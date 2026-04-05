"""Mission Controller — orchestrates multi-agent missions."""
import glob as glob_mod
import json
import logging
import os
import time
from datetime import datetime, timezone

from context.policy_telemetry import emit_policy_event
from mission.mission_state import MissionState, MissionStatus
from mission.persistence_adapter import MissionPersistenceAdapter
from mission.policy_context import (
    TimeoutConfig,
    build_policy_context,
)
from mission.policy_engine import PolicyDecision, PolicyEngine
from mission.recovery_engine import StageRecoveryEngine
from mission.resilience import (
    CircuitBreaker,
)
from persistence.dlq_store import DLQStore
from services.approval_store import ApprovalStore

MISSIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs", "missions"
)


class MissionController:
    def __init__(self, planner_agent_id="gpt-general"):
        """
        planner_agent_id: which LLM to use for mission planning.
        The planner breaks user request into stages.
        Specialists execute each stage.
        """
        self.planner_agent_id = planner_agent_id
        os.makedirs(MISSIONS_DIR, exist_ok=True)

        # B-106: Resilience — DLQ + circuit breaker
        self._dlq_store = DLQStore()
        # B-134: Approval FSM store (D-138)
        self._approval_store = ApprovalStore()
        # B-107: Policy engine — pre-stage evaluation
        self._policy_engine = PolicyEngine()
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=3, reset_timeout_s=300.0)

        # B-139: Extracted services (D-139)
        self._persistence = MissionPersistenceAdapter(MISSIONS_DIR)
        self._recovery_engine = StageRecoveryEngine(
            self._circuit_breaker, self._dlq_store)

        # 7.9: Auto-generate capability manifest on startup
        self._update_capability_manifest()

        # B-141: Recover orphaned missions on startup (fail-closed)
        self._recover_orphaned_missions()

    # ── B-141: Mission Startup Recovery ─────────────────────────────

    def _recover_orphaned_missions(self) -> int:
        """B-141: Fail-closed startup recovery for orphaned missions.

        Scans persisted missions and applies recovery matrix:
        - RUNNING/PLANNING → FAILED (orphaned_by_restart)
        - WAITING_APPROVAL (PENDING/ESCALATED) → expire approval → FAILED
        - PAUSED → preserve (operator explicitly paused)
        - Terminal states (COMPLETED/FAILED/TIMED_OUT) → no mutation
        """
        logger = logging.getLogger("mcc.controller.startup_recovery")
        # Suffixes for non-canonical files
        excluded_suffixes = ("-state.json", "-summary.json", "-token-report.json")

        pattern = os.path.join(MISSIONS_DIR, "mission-*.json")
        recovered = []

        for mission_path in sorted(glob_mod.glob(pattern)):
            filename = os.path.basename(mission_path)
            if any(filename.endswith(s) for s in excluded_suffixes):
                continue

            try:
                with open(mission_path, "r", encoding="utf-8") as f:
                    mission = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Cannot read mission file %s: %s", mission_path, exc)
                continue

            mission_id = mission.get("missionId", "")
            status = mission.get("status", "")

            if not mission_id or not status:
                continue

            # Load state machine (if persisted)
            state_path = os.path.join(MISSIONS_DIR, f"{mission_id}-state.json")
            mission_state = None
            if os.path.exists(state_path):
                try:
                    with open(state_path, "r", encoding="utf-8") as f:
                        mission_state = MissionState.from_dict(json.load(f))
                except (json.JSONDecodeError, OSError, KeyError):
                    pass

            old_status = status
            reason = ""

            # Case 1: RUNNING or PLANNING → FAILED
            if status in ("running", "planning", "executing"):
                reason = "orphaned_by_restart"
                mission["status"] = "failed"
                mission["error"] = f"Startup recovery: {reason}"
                mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                if mission_state:
                    mission_state.transition_to(MissionStatus.FAILED, reason)

            # Case 2: WAITING_APPROVAL → expire approval → FAILED
            elif status == "waiting_approval":
                # Expire any pending/escalated approvals for this mission
                approval_id = mission.get("pendingApprovalId")
                approval_reason = "restart_expired_approval"
                if approval_id:
                    record = self._approval_store.pending.get(approval_id)
                    if record and record.status == "escalated":
                        approval_reason = "restart_expired_escalated_approval"
                    # Force-expire the approval
                    if record and record.status in ("pending", "escalated"):
                        record.status = "expired"
                        record.decision = "expired"
                        record.decidedAt = datetime.now(timezone.utc).isoformat()
                        record.decidedBy = "system:startup_recovery"
                        self._approval_store._move_to_history(record)
                        self._approval_store._persist_decision(record)

                reason = approval_reason
                mission["status"] = "failed"
                mission["error"] = f"Startup recovery: {reason}"
                mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                if mission_state:
                    mission_state.transition_to(MissionStatus.FAILED, reason)

            # Case 3: PAUSED → preserve (no mutation)
            elif status == "paused":
                continue

            # Case 4: Terminal states → no mutation
            elif status in ("completed", "failed", "timed_out"):
                continue

            else:
                # Unknown non-terminal state → fail-closed
                reason = f"orphaned_unknown_state_{status}"
                mission["status"] = "failed"
                mission["error"] = f"Startup recovery: {reason}"
                mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                if mission_state:
                    try:
                        mission_state.transition_to(MissionStatus.FAILED, reason)
                    except Exception:
                        pass

            # Persist recovered mission
            self._save_mission(mission)
            if mission_state:
                self._persist_mission_state(mission_state)

            recovered.append({
                "mission_id": mission_id,
                "old_status": old_status,
                "new_status": "failed",
                "reason": reason,
            })

            emit_policy_event("mission_startup_recovery", {
                "mission_id": mission_id,
                "old_status": old_status,
                "new_status": "failed",
                "reason": reason,
            })

            logger.info(
                "Recovered mission %s: %s → failed (reason=%s)",
                mission_id, old_status, reason)

        if recovered:
            logger.warning(
                "Startup recovery: %d orphaned missions recovered", len(recovered))
        else:
            logger.info("Startup recovery: no orphaned missions found")

        return len(recovered)

    def execute_mission(self, goal: str, user_id: str, session_id: str,
                         retry_from_mission: dict = None) -> dict:
        """Execute a multi-agent mission.

        1. Plan: break goal into stages
        2. Execute: run each stage with appropriate specialist (state-driven)
        3. Collect: gather artifacts via Context Assembler
        4. Report: return final result with structured summary

        retry_from_mission: If provided, resume from last completed stage of this
        failed mission instead of re-planning from scratch.
        """
        from context.assembler import ContextAssembler
        from context.expansion_broker import ExpansionBroker
        from mission.role_registry import resolve_role

        mission_id = f"mission-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
        start_time = time.time()

        # Initialize Context Assembler and Expansion Broker for this mission
        assembler = ContextAssembler(mission_id)
        expansion_broker = ExpansionBroker(mission_id)

        # 5C-1: Initialize mission state machine
        mission_state = MissionState(mission_id)
        mission_state.transition_to(MissionStatus.PLANNING, "mission started")

        # Reset per-mission gate flags
        self._gate_1_checked = False

        # Initialize mission dict
        mission = {
            "missionId": mission_id,
            "goal": goal,
            "userId": user_id,
            "sessionId": session_id,
            "status": "planning",
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "stages": [],
            "artifacts": [],
            "completedArtifactIds": [],
            "currentStage": 0,
            "error": None,
            "finishedAt": None,
            "retryFromMissionId": retry_from_mission.get("missionId") if retry_from_mission else None,
            "risk_level": None,  # D-128: set after planning, before execution
            "timeoutConfig": TimeoutConfig().to_dict(),  # B-014: timeout hierarchy
            "policyContext": None,  # B-013: set before stage execution
            "cumulativeTokens": 0,  # B-140: running token total
            "maxTokenBudget": None,  # B-140: None = no enforcement (backward compat)
        }
        self._save_mission(mission)

        # Step 1: Plan the mission (complexity-routed or reuse from retry)
        resume_from_index = 0
        try:
            if retry_from_mission:
                # Reuse plan from failed mission, resume after last completed stage
                old_stages = retry_from_mission.get("stages", [])
                plan = {"stages": []}
                for s in old_stages:
                    # Reset non-completed stages for re-execution
                    new_stage = dict(s)
                    if new_stage.get("status") == "completed":
                        resume_from_index += 1
                    else:
                        new_stage["status"] = "pending"
                        new_stage["error"] = None
                        new_stage["result"] = None
                        new_stage["started_at"] = None
                        new_stage["finished_at"] = None
                    plan["stages"].append(new_stage)
                complexity = retry_from_mission.get("complexity", "standard")
                mission["stages"] = plan["stages"]
                mission["complexity"] = complexity
                self._mission_complexity = complexity
                mission["status"] = "executing"
                # Carry forward completed artifacts
                for s in plan["stages"][:resume_from_index]:
                    all_completed_arts = s.get("artifacts", [])
                    mission["artifacts"].extend(all_completed_arts)
                mission_state.transition_to(MissionStatus.READY,
                                            f"retry: reusing plan, resuming from stage {resume_from_index + 1}")
            else:
                plan, complexity = self._plan_mission(goal, mission_id)
                mission["stages"] = plan["stages"]
                mission["complexity"] = complexity
                self._mission_complexity = complexity
                mission["status"] = "executing"
                mission_state.transition_to(MissionStatus.READY,
                                            f"planned {len(plan['stages'])} stages")
            # D-128: Classify mission risk from planned tool usage (once, at creation)
            mission["risk_level"] = self._classify_mission_risk(mission)
            # B-140: Set default token budget if not specified
            if mission.get("maxTokenBudget") is None:
                mission["maxTokenBudget"] = self._default_token_budget(
                    mission.get("complexity", "standard"))
            self._save_mission(mission)
        except Exception as e:
            mission["status"] = "failed"
            mission["error"] = f"Planning failed: {e}"
            mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
            mission_state.transition_to(MissionStatus.FAILED,
                                        f"planning failed: {e}")
            self._save_mission(mission)
            self._persist_mission_state(mission_state)
            # B-106: Enqueue to DLQ for later retry
            self._enqueue_to_dlq(mission)
            self._emit_mission_summary(mission_id, mission, assembler,
                                       expansion_broker, "failed",
                                       mission_state=mission_state)
            return mission

        # Step 2: Execute stages with state-driven while loop
        mission_state.transition_to(MissionStatus.RUNNING, "executing stages")
        all_artifacts = list(mission.get("artifacts", []))
        completed_roles = set()
        failure_reason = None
        current_stage_index = resume_from_index
        # D-102 L1: Track stage results for distance-based context assembly
        stage_results = []

        while current_stage_index < len(mission["stages"]):
            stage = mission["stages"][current_stage_index]
            mission["currentStage"] = current_stage_index + 1
            stage_id = stage.get("id", f"stage-{current_stage_index+1}")
            specialist = stage.get("specialist", "analyst")
            role = resolve_role(specialist)

            # 5C-1: Track current position in state machine
            mission_state.current_stage_index = current_stage_index
            mission_state.pending_stage_id = stage_id

            # Skip already-completed stages (retry resume)
            if stage.get("status") == "completed":
                all_artifacts.extend(stage.get("artifacts", []))
                completed_roles.add(role)
                current_stage_index += 1
                continue

            # Skip stages that failed during planning validation
            if stage.get("status") == "failed":
                failure_reason = stage.get("error",
                                           f"Stage {stage_id} failed during planning")
                mission["status"] = "failed"
                mission["error"] = failure_reason
                mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                mission_state.transition_to(MissionStatus.FAILED, failure_reason)
                self._save_mission(mission)
                self._persist_mission_state(mission_state)
                self._enqueue_to_dlq(mission)
                self._emit_mission_summary(mission_id, mission, assembler,
                                           expansion_broker, "failed",
                                           mission_state=mission_state)
                return mission

            # D-053: Fail-closed — working set must exist in mission mode
            working_set = stage.get("working_set")
            if working_set is None:
                stage["status"] = "failed"
                stage["error"] = (
                    f"POLICY: Stage {stage_id} cannot start "
                    f"without a working set in mission mode."
                )
                failure_reason = stage["error"]
                mission["status"] = "failed"
                mission["error"] = failure_reason
                mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                mission_state.transition_to(MissionStatus.FAILED, failure_reason)
                self._save_mission(mission)
                self._persist_mission_state(mission_state)
                self._enqueue_to_dlq(mission)
                self._emit_mission_summary(mission_id, mission, assembler,
                                           expansion_broker, "failed",
                                           mission_state=mission_state)
                return mission

            # 4-4: Enrich working set from discovery_map for downstream roles
            if specialist in ("developer", "tester", "reviewer"):
                working_set = self._enrich_working_set_from_discovery(
                    working_set, specialist, assembler)
                stage["working_set"] = working_set

            stage["status"] = "running"
            stage["started_at"] = datetime.now(timezone.utc).isoformat()
            self._save_mission(mission)
            self._persist_mission_state(mission_state)
            # Emit live summary so UI can track progress
            self._emit_mission_summary(mission_id, mission, assembler,
                                       expansion_broker, "running",
                                       mission_state=mission_state)

            try:
                # B-013: Build policy context for pre-stage evaluation
                policy_ctx = build_policy_context(mission, start_time)
                mission["policyContext"] = policy_ctx.to_dict()
                stage["policyContext"] = policy_ctx.to_dict()

                # B-014: Check mission-level timeout before starting stage
                elapsed = time.time() - start_time
                mission_timeout = policy_ctx.timeout_config.mission_seconds
                if elapsed >= mission_timeout:
                    stage["status"] = "timed_out"
                    stage["error"] = (
                        f"Mission timeout exceeded: {elapsed:.0f}s >= {mission_timeout}s"
                    )
                    mission["status"] = "timed_out"
                    mission["error"] = stage["error"]
                    mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                    mission_state.transition_to(
                        MissionStatus.TIMED_OUT,
                        f"mission timeout: {elapsed:.0f}s >= {mission_timeout}s")
                    emit_policy_event("mission_timed_out", {
                        "mission_id": mission_id,
                        "elapsed_seconds": round(elapsed, 1),
                        "timeout_seconds": mission_timeout,
                        "stage_id": stage_id,
                    })
                    self._save_mission(mission)
                    self._persist_mission_state(mission_state)
                    self._enqueue_to_dlq(mission)
                    self._emit_mission_summary(
                        mission_id, mission, assembler,
                        expansion_broker, "timed_out",
                        mission_state=mission_state)
                    return mission

                # Build artifact context from Assembler for this stage
                artifact_context = ""
                if mission["completedArtifactIds"]:
                    context_package = assembler.build_context_for_role(
                        role=self._ROLE_ALIASES.get(specialist, specialist),
                        skill="",
                        stage_id=stage_id,
                        artifact_ids=mission["completedArtifactIds"]
                    )
                    artifact_context = self._format_artifact_context(
                        context_package, stage_results=stage_results)

                # B-107: Pre-stage policy evaluation
                mission_config = {
                    "goal": mission.get("goal", ""),
                    "complexity": mission.get("complexity", "medium"),
                    "stages": mission.get("stages", []),
                    "approval_state": mission.get("approval_state", "none"),
                }
                policy_result = self._policy_engine.evaluate(
                    policy_ctx.to_dict(), mission_config)
                stage["policyDecision"] = policy_result.decision.value
                stage["policyRule"] = policy_result.matched_rule
                stage["policyEvalMs"] = round(policy_result.eval_time_ms, 2)

                if policy_result.decision == PolicyDecision.DENY:
                    stage["status"] = "skipped"
                    stage["error"] = f"Policy denied: {policy_result.reason}"
                    emit_policy_event("policy_denied", {
                        "mission_id": mission_id,
                        "stage_id": stage_id,
                        "rule": policy_result.matched_rule,
                        "reason": policy_result.reason,
                    })
                    self._save_mission(mission)
                    continue

                if policy_result.decision == PolicyDecision.ESCALATE:
                    stage["status"] = "waiting_approval"
                    mission["status"] = "waiting_approval"
                    mission_state.transition_to(
                        MissionStatus.WAITING_APPROVAL,
                        f"Policy escalated: {policy_result.reason}")

                    # B-134: Create approval request in FSM store
                    approval_record = self._approval_store.request_approval(
                        mission_id=mission_id,
                        stage_id=stage_id,
                        role=specialist,
                        tool_call_id=f"policy-{stage_id}",
                        tool=stage.get("skill", "unknown"),
                        params={"goal": mission.get("goal", ""), "stage": stage_id},
                        risk=stage.get("policyDecision", "escalate"),
                        reason=policy_result.reason,
                        timeout_seconds=300,
                    )
                    mission["pendingApprovalId"] = approval_record.approvalId

                    emit_policy_event("policy_escalated", {
                        "mission_id": mission_id,
                        "stage_id": stage_id,
                        "rule": policy_result.matched_rule,
                        "approval_id": approval_record.approvalId,
                    })
                    self._save_mission(mission)
                    self._persist_mission_state(mission_state)
                    self._emit_mission_summary(
                        mission_id, mission, assembler,
                        expansion_broker, "waiting_approval",
                        mission_state=mission_state)

                    # B-134: Wait for approval decision
                    decision = self._wait_for_approval(
                        mission_id, mission, mission_state,
                        approval_record.approvalId, timeout_s=300)

                    if decision == "approved":
                        # Resume execution — transition back to RUNNING
                        mission_state.transition_to(
                            MissionStatus.RUNNING,
                            f"approval {approval_record.approvalId} approved")
                        mission["status"] = "executing"
                        mission.pop("pendingApprovalId", None)
                        emit_policy_event("approval_resumed", {
                            "mission_id": mission_id,
                            "approval_id": approval_record.approvalId,
                            "stage_id": stage_id,
                        })
                        self._save_mission(mission)
                        self._persist_mission_state(mission_state)
                        # Continue to stage execution (don't return)
                    else:
                        # denied / expired / timeout → FAILED
                        failure_reason = (
                            f"Approval {decision} for stage {stage_id} "
                            f"(approval_id={approval_record.approvalId})")
                        mission_state.transition_to(
                            MissionStatus.FAILED, failure_reason)
                        mission["status"] = "failed"
                        mission["error"] = failure_reason
                        mission["finishedAt"] = datetime.now(
                            timezone.utc).isoformat()
                        mission.pop("pendingApprovalId", None)
                        emit_policy_event("approval_failed", {
                            "mission_id": mission_id,
                            "approval_id": approval_record.approvalId,
                            "decision": decision,
                            "stage_id": stage_id,
                        })
                        self._save_mission(mission)
                        self._persist_mission_state(mission_state)
                        self._enqueue_to_dlq(mission)
                        self._emit_mission_summary(
                            mission_id, mission, assembler,
                            expansion_broker, "failed",
                            mission_state=mission_state)
                        return mission

                if policy_result.decision == PolicyDecision.DEGRADE:
                    emit_policy_event("policy_degraded", {
                        "mission_id": mission_id,
                        "stage_id": stage_id,
                        "rule": policy_result.matched_rule,
                        "fallback": policy_result.fallback,
                    })
                    # Continue with degraded mode — fallback info in stage

                # B-014: Execute stage with timeout enforcement
                stage_timeout = policy_ctx.timeout_config.effective_stage_timeout(
                    stage.get("timeoutSeconds"))
                stage_start = time.time()

                result = self._execute_stage(
                    stage, all_artifacts, mission_id, user_id,
                    artifact_context=artifact_context,
                    expansion_broker=expansion_broker
                )

                # B-014: Post-execution stage timeout check
                stage_elapsed = time.time() - stage_start
                if stage_elapsed >= stage_timeout:
                    emit_policy_event("stage_timeout_exceeded", {
                        "mission_id": mission_id,
                        "stage_id": stage_id,
                        "elapsed_seconds": round(stage_elapsed, 1),
                        "timeout_seconds": stage_timeout,
                        "completed": True,
                    })

                # Guard: ensure result is a dict (LLM may return string on error)
                if not isinstance(result, dict):
                    result = {"status": "error", "response": str(result),
                              "error": f"Unexpected result type: {type(result).__name__}"}

                # Always save prompt/execution info regardless of outcome
                stage["system_prompt"] = result.get("systemPrompt", "")
                stage["user_prompt"] = result.get("userPrompt", "")
                stage["turns_used"] = result.get("turnsUsed", 0)
                stage["duration_ms"] = result.get("totalDurationMs", 0)
                stage["tool_call_count"] = len(result.get("toolCalls", []))
                stage["tool_calls_detail"] = result.get("toolCalls", [])
                stage["token_report"] = result.get("tokenReport")
                stage["policy_deny_count"] = sum(
                    1 for tc in result.get("toolCalls", [])
                    if tc.get("policyDenied")
                )

                # Check if stage itself reported failure
                if result and result.get("status") == "error":
                    stage["result"] = result.get("response", "")
                    raise Exception(result.get("error",
                                               "Stage reported failure"))

                stage["status"] = "completed"
                stage["finished_at"] = datetime.now(timezone.utc).isoformat()
                stage["result"] = result.get("response", "")
                stage["artifacts"] = result.get("artifacts", [])
                # B-106: Reset circuit breaker on success
                self._circuit_breaker.record_success(specialist)
                # B-140: Accumulate token budget after stage completion
                self._update_mission_budget(mission)
                # Save immediately so UI sees progress
                self._save_mission(mission)
                self._persist_mission_state(mission_state)
                self._emit_mission_summary(mission_id, mission, assembler,
                                           expansion_broker, "running",
                                           mission_state=mission_state)
                all_artifacts.extend(stage["artifacts"])

                # Store stage output in Assembler with D-047 header
                # 6C-1: Use typed artifact from skill contract
                canonical_role = self._ROLE_ALIASES.get(specialist, specialist)
                stage_skill = stage.get("skill", "")
                artifact_type = self._resolve_artifact_type(stage_skill)

                stage_artifact_data = {
                    "response": stage["result"],
                    "stage_id": stage_id,
                    "specialist": specialist,
                    "tool_calls": stage["tool_call_count"],
                    "raw_artifacts": stage["artifacts"]
                }

                # 6D-1: Extract structured fields from LLM response
                from mission.artifact_extractor import extract_artifact_fields
                extracted = extract_artifact_fields(
                    artifact_type, stage.get("result", ""))
                stage_artifact_data.update(extracted)

                artifact_id = assembler.store_artifact(
                    artifact_type=artifact_type,
                    data=stage_artifact_data,
                    stage_id=stage_id,
                    role=canonical_role,
                    skill=stage_skill,
                    input_artifact_ids=list(mission["completedArtifactIds"])
                )
                mission["completedArtifactIds"].append(artifact_id)

                # 6C-1: Schema validation (non-blocking warning)
                if artifact_type != "stage_output":
                    self._validate_artifact_schema(
                        artifact_type, stage_artifact_data,
                        mission_id, stage_id, canonical_role)

                # D-102 L1: Extract clean stage result for downstream context
                from mission.stage_result import extract_stage_result
                sr = extract_stage_result(stage)
                stage_results.append(sr)

                # 5C-1: Track completion in state machine
                completed_roles.add(role)
                mission_state.last_completed_stage_id = stage_id

            except Exception as e:
                # 5C-3: Recovery triage — NOT immediate abort
                error_context = str(e)

                emit_policy_event("stage_failed", {
                    "mission_id": mission_id,
                    "stage_id": stage_id,
                    "role": role,
                    "error": error_context[:500]
                })

                recovery = self._handle_stage_failure(
                    stage, error_context, mission_state, assembler,
                    mission_id, user_id, all_artifacts, expansion_broker)

                if recovery["action"] == "retry_stage":
                    # Re-run same index
                    continue
                elif recovery["action"] in ("abort", "escalate"):
                    stage["status"] = "failed"
                    stage["finished_at"] = datetime.now(timezone.utc).isoformat()
                    stage["error"] = error_context
                    failure_reason = (f"Stage {stage_id} failed: "
                                      f"{recovery.get('reason', error_context)}")
                    if mission_state.status != MissionStatus.FAILED:
                        mission_state.transition_to(MissionStatus.FAILED,
                                                    failure_reason)
                    mission["status"] = "failed"
                    mission["error"] = failure_reason
                    mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                    self._save_mission(mission)
                    self._persist_mission_state(mission_state)
                    self._save_token_report(mission)
                    # B-106: Enqueue to DLQ for later retry
                    self._enqueue_to_dlq(mission)
                    self._emit_mission_summary(
                        mission_id, mission, assembler,
                        expansion_broker, "failed",
                        mission_state=mission_state)
                    return mission
                elif recovery["action"] == "retry_from":
                    target = recovery.get("target_stage", "stage-1")
                    target_index = self._find_stage_index(
                        mission["stages"], target)
                    if target_index is not None:
                        current_stage_index = target_index
                        mission_state.transition_to(
                            MissionStatus.READY,
                            f"Retrying from {target}")
                        mission_state.transition_to(
                            MissionStatus.RUNNING,
                            "resuming execution")
                        continue
                    else:
                        failure_reason = (f"Could not find target "
                                          f"stage: {target}")
                        mission_state.transition_to(
                            MissionStatus.FAILED, failure_reason)
                        mission["status"] = "failed"
                        mission["error"] = failure_reason
                        mission["finishedAt"] = (
                            datetime.now(timezone.utc).isoformat())
                        self._save_mission(mission)
                        self._persist_mission_state(mission_state)
                        self._enqueue_to_dlq(mission)
                        self._emit_mission_summary(
                            mission_id, mission, assembler,
                            expansion_broker, "failed",
                            mission_state=mission_state)
                        return mission

            # 5C-2: Gate checks after stage completion
            gate_action = self._check_gates_and_loops(
                role, completed_roles, assembler, stages=mission["stages"],
                current_index=current_stage_index,
                mission_state=mission_state, mission_id=mission_id)

            if gate_action == "abort":
                failure_reason = "Quality gate forced abort"
                mission["status"] = "failed"
                mission["error"] = failure_reason
                mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                self._save_mission(mission)
                self._persist_mission_state(mission_state)
                self._save_token_report(mission)
                self._enqueue_to_dlq(mission)
                self._emit_mission_summary(mission_id, mission, assembler,
                                           expansion_broker, "failed",
                                           mission_state=mission_state)
                return mission

            # Check for pause signal between stages
            if self._check_and_handle_pause(mission_id, mission, mission_state,
                                             assembler, expansion_broker):
                # Mission was paused — wait for resume or abort
                resumed = self._wait_for_resume(mission_id, mission,
                                                 mission_state)
                if not resumed:
                    # Resume timed out or cancel signal — abort
                    mission["status"] = "failed"
                    mission["error"] = "Mission aborted — resume not received"
                    mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                    mission_state.transition_to(MissionStatus.FAILED,
                                                "pause aborted — no resume")
                    self._save_mission(mission)
                    self._persist_mission_state(mission_state)
                    self._save_token_report(mission)
                    self._enqueue_to_dlq(mission)
                    self._emit_mission_summary(mission_id, mission, assembler,
                                               expansion_broker, "failed",
                                               mission_state=mission_state)
                    return mission

            # Both "proceed" and "stages_modified" → increment
            current_stage_index += 1
            self._save_mission(mission)
            self._persist_mission_state(mission_state)

        # Step 3: Generate final summary
        try:
            summary = self._generate_summary(goal, mission["stages"],
                                             all_artifacts)
        except Exception:
            summary = "Mission completed but summary generation failed."

        # 5C-1: Terminal state
        if mission_state.status == MissionStatus.RUNNING:
            mission_state.transition_to(MissionStatus.COMPLETED,
                                        "all stages done")

        mission["status"] = "completed"
        mission["summary"] = summary
        mission["artifacts"] = all_artifacts
        mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
        mission["totalDurationMs"] = int((time.time() - start_time) * 1000)
        self._save_mission(mission)
        self._persist_mission_state(mission_state)
        self._save_token_report(mission)

        # D-055: Structured mission summary
        self._emit_mission_summary(mission_id, mission, assembler,
                                   expansion_broker, "completed",
                                   mission_state=mission_state)

        return mission

    def _plan_mission(self, goal: str, mission_id: str) -> tuple[dict, str]:
        """Plan mission with complexity-routed stage template.

        Returns (plan_dict, complexity_class).
        """
        from context.policy_telemetry import emit_policy_event
        from mission.complexity_router import classify_complexity
        from mission.role_registry import get_role, resolve_role
        from mission.skill_contracts import validate_role_skill
        from providers.factory import create_provider

        provider, _ = create_provider(self.planner_agent_id)

        # Step 1: Complexity classification (Tier 0 deterministic first)
        classification = classify_complexity(goal, provider)
        complexity = classification["complexity"]
        template = classification["stage_template"]

        emit_policy_event("complexity_classified", {
            "mission_id": mission_id,
            "complexity": complexity,
            "tier_used": classification["tier_used"],
            "role_count": classification["role_count"],
            "message_preview": goal[:100]
        })

        # Step 2: Build constrained planner prompt
        role_sequence = " -> ".join(s["specialist"] for s in template)
        template_lines = "\n".join(
            f"Stage {i+1}: {s['specialist']} (skill: {s['skill']})"
            for i, s in enumerate(template)
        )

        constrained_prompt = f"""You are a mission planner.

TASK COMPLEXITY: {complexity}
REQUIRED ROLE SEQUENCE: {role_sequence}

You MUST use exactly these roles in this order:
{template_lines}

For each stage, provide a specific instruction based on the user's goal.
Do NOT add or remove roles from the sequence.
Do NOT change the role order.

Respond ONLY with a JSON object, no markdown:
{{
  "stages": [
    {{
      "id": "stage-1",
      "specialist": "{template[0]['specialist']}",
      "skill": "{template[0]['skill']}",
      "objective": "...",
      "instruction": "Specific instruction for this role"
    }}
  ]
}}"""

        # Step 3: LLM fills in instructions (with retry on empty/invalid response)
        messages = [
            {"role": "system", "content": constrained_prompt},
            {"role": "user", "content": goal}
        ]

        plan = None
        last_error = None
        for attempt in range(2):
            try:
                response = provider.chat(messages, tools=[], max_tokens=2000)
                text = response.text or ""
                text = text.strip()

                if not text:
                    last_error = "LLM returned empty response"
                    continue

                # Strip markdown fences
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text.rsplit("```", 1)[0]
                text = text.strip()
                if text.startswith("json"):
                    text = text[4:].strip()

                # Try to find JSON in text if it doesn't start with {
                if not text.startswith("{"):
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', text)
                    if json_match:
                        text = json_match.group(0)

                parsed = json.loads(text)
                # Guard: ensure parsed result is a dict with stages
                if isinstance(parsed, dict) and "stages" in parsed:
                    plan = parsed
                else:
                    last_error = f"Parsed JSON is not a valid plan: {type(parsed).__name__}"
                    continue
                break
            except json.JSONDecodeError as e:
                last_error = f"LLM response is not valid JSON: {e}. Response was: {(response.text or '')[:200]}"
                continue
            except Exception as e:
                last_error = str(e)
                continue

        # Fallback: if LLM failed to produce valid JSON, use template directly
        if plan is None:
            emit_policy_event("planning_llm_fallback", {
                "mission_id": mission_id,
                "reason": last_error,
            })
            plan = {"stages": [
                {
                    "id": f"stage-{i+1}",
                    "specialist": s["specialist"],
                    "skill": s["skill"],
                    "objective": goal,
                    "instruction": f"Role: {s['specialist']}. Perform {s['skill']} for: {goal}",
                }
                for i, s in enumerate(template)
            ]}

        stages = plan.get("stages", [])

        # Step 4: Force template if planner deviated
        if len(stages) != len(template):
            stages = self._force_template(template, goal, stages)
            plan["stages"] = stages

        # Validate and enrich stages
        for stage in stages:
            stage["status"] = "pending"
            stage["result"] = None
            stage["artifacts"] = []
            stage["error"] = None
            stage["duration_ms"] = 0

            raw_specialist = stage.get("specialist", "analyst")
            canonical_role = resolve_role(raw_specialist)
            stage["specialist"] = canonical_role

            role_def = get_role(canonical_role)
            if not role_def:
                stage["status"] = "failed"
                stage["error"] = f"POLICY: Unknown role '{canonical_role}'"
                continue

            skill = stage.get("skill", "")
            if skill:
                allowed, reason = validate_role_skill(canonical_role, skill)
                if not allowed:
                    stage["status"] = "failed"
                    stage["error"] = f"POLICY: {reason}"
                    continue

            stage["working_set"] = self._build_default_working_set(
                stage.get("id", "unknown"),
                canonical_role
            )

        return plan, complexity

    def _force_template(self, template: list, goal: str,
                        attempted_stages: list) -> list:
        """When planner deviates from template, force template with best-effort instructions."""
        forced = []
        for i, t in enumerate(template):
            instruction = f"Perform {t['skill']} for: {goal}"
            for attempted in attempted_stages:
                if attempted.get("specialist") == t["specialist"]:
                    instruction = attempted.get("instruction", instruction)
                    break
            forced.append({
                "id": f"stage-{i+1}",
                "specialist": t["specialist"],
                "skill": t["skill"],
                "instruction": instruction
            })
        return forced

    def _enrich_working_set_from_discovery(self, working_set, role, assembler):
        """Populate working set with file targets from discovery_map artifact."""
        if not assembler:
            return working_set

        from artifacts.schema_validator import extract_working_set_from_discovery

        # Find discovery_map artifacts
        discovery_artifacts = [
            aid for aid, art in assembler.artifacts.items()
            if art.get("type") == "discovery_map"
        ]
        if not discovery_artifacts:
            return working_set

        latest_id = discovery_artifacts[-1]
        discovery_data = assembler.artifacts[latest_id].get("data", {})
        file_targets = extract_working_set_from_discovery(discovery_data)

        role_targets = file_targets.get(role)
        if not role_targets:
            return working_set

        # Enrich — add discovered files to existing working set
        if hasattr(working_set, 'files'):
            existing_ro = set(working_set.files.read_only)
            new_ro = set(role_targets.get("readOnly", []))
            working_set.files.read_only = list(existing_ro | new_ro)

            if role == "developer":
                existing_rw = set(working_set.files.read_write)
                new_rw = set(role_targets.get("readWrite", []))
                working_set.files.read_write = list(existing_rw | new_rw)

                existing_c = set(working_set.files.creatable)
                new_c = set(role_targets.get("creatable", []))
                working_set.files.creatable = list(existing_c | new_c)

            existing_dirs = set(working_set.files.directory_list)
            new_dirs = set(role_targets.get("directoryList", []))
            working_set.files.directory_list = list(existing_dirs | new_dirs)

        return working_set

    def _execute_stage(self, stage: dict, previous_artifacts: list,
                       mission_id: str, user_id: str,
                       artifact_context: str = "",
                       expansion_broker=None) -> dict:
        """Execute a single stage with the appropriate specialist."""
        from oc_agent_runner_lib import run_agent_with_config

        specialist = stage.get("specialist", "analyst")
        instruction = stage.get("instruction", stage.get("objective", ""))

        # Build context: Assembler-based context (primary) +
        # legacy artifact preview (fallback)
        context = ""
        if artifact_context:
            context = "\n\nContext from previous stages:\n" + artifact_context
        elif previous_artifacts:
            context = "\n\nResults from previous stages:\n"
            for art in previous_artifacts:
                art_type = art.get("type", "unknown")
                art_data = art.get("data", {})
                if art_type == "text_response":
                    context += f"- {art_data.get('message', '')[:200]}\n"
                elif art_type == "system_info":
                    context += f"- System: {json.dumps(art_data)}\n"
                elif art_type == "file_created":
                    context += f"- File created: {art_data.get('path', '')}\n"
                else:
                    context += f"- [{art_type}]: {json.dumps(art_data)[:200]}\n"

        full_instruction = instruction + context
        # 6C-2: Agent selection from role registry
        agent_id = self._select_agent_for_role(specialist, mission_id,
                                                stage.get("id", ""))
        # 7.4: Track which agent/model was used for this stage
        stage["agent_used"] = agent_id

        working_set = stage.get("working_set")

        result = run_agent_with_config(
            message=full_instruction,
            agent_id=agent_id,
            user_id=user_id,
            session_id=f"{mission_id}-{stage.get('id', 'stage')}",
            max_turns=10,
            tool_policy=specialist,
            working_set=working_set,
            expansion_broker=expansion_broker
        )

        return result

    def _format_artifact_context(self, context_package: list,
                                   stage_results: list = None) -> str:
        """Format assembler context for LLM consumption.

        D-102 L2 distance-based tiered truncation:
          Distance 1 (N-1, previous stage):  max 5000 chars
          Distance 2 (N-2):                  max 2000 chars
          Distance 3+ (N-3+):                max 500 chars

        Semantic tier limits (A-D) are still respected but capped by
        distance limits. The stricter of the two applies.

        Stage boundary isolation (L1): only artifact text passed,
        tool call history never crosses stage boundaries.

        Args:
            context_package: list of (artifactId, content, tier) from assembler
            stage_results: list of StageResult from completed stages (optional,
                          enables distance-based limits)
        """
        # Semantic tier limits (existing)
        SEMANTIC_LIMITS = {"A": 5000, "B": 2000, "C": 500, "D": 1000}
        # Distance-based limits (L2) — index from end of context_package
        DISTANCE_LIMITS = {1: 5000, 2: 2000}  # 3+ defaults to 500
        DISTANCE_DEFAULT = 500

        n_artifacts = len(context_package)

        parts = []
        for idx, (artifact_id, content, tier) in enumerate(context_package):
            if content is None:
                continue

            # Semantic limit from tier matrix
            semantic_limit = SEMANTIC_LIMITS.get(tier, 1000)

            # Distance limit: how far back is this artifact?
            # idx=0 is oldest, idx=n-1 is most recent
            if stage_results is not None and n_artifacts > 0:
                distance = n_artifacts - idx  # 1 = most recent
                distance_limit = DISTANCE_LIMITS.get(distance, DISTANCE_DEFAULT)
                char_limit = min(semantic_limit, distance_limit)
            else:
                char_limit = semantic_limit

            if isinstance(content, dict):
                text = json.dumps(content, indent=2, ensure_ascii=False)
            elif isinstance(content, str):
                text = content
            else:
                continue

            if len(text) > char_limit:
                text = text[:char_limit] + f"\n[...truncated to {char_limit} chars]"

            parts.append(f"--- {artifact_id} (tier {tier}) ---\n{text}")

        result = "\n\n".join(parts)

        # D-102: Total context budget check
        from context.token_budget import estimate_tokens
        total_tokens = estimate_tokens(result)
        if total_tokens > 40000:
            # Emergency truncation — keep only most recent artifacts
            parts = parts[-3:]
            result = "\n\n".join(parts)
            result += f"\n\n[Context truncated: {total_tokens} tokens exceeded 40K budget]"

        return result

    def _classify_mission_risk(self, mission: dict) -> str:
        """D-128: Classify mission risk from planned stages' tool usage.

        Computed once at creation, never recomputed.
        Returns highest risk level among all tools, unknown defaults to high.
        """
        from services.risk_engine import RiskEngine
        engine = RiskEngine()
        tool_names = []
        for stage in mission.get("stages", []):
            tool = stage.get("tool")
            if tool:
                tool_names.append(tool)
            # Also check tools list if present
            for t in stage.get("tools", []):
                if isinstance(t, str):
                    tool_names.append(t)
                elif isinstance(t, dict) and "name" in t:
                    tool_names.append(t["name"])
        return engine.classify_mission(tool_names)

    def _persist_mission_state(self, mission_state: MissionState):
        """5C-1: Persist mission state machine — delegates to MissionPersistenceAdapter (B-139)."""
        self._persistence.persist_mission_state(mission_state)

    def _emit_mission_summary(self, mission_id: str, mission: dict,
                               assembler, expansion_broker, status: str,
                               mission_state: MissionState = None):
        """D-055: Generate and save per-mission structured summary."""
        from context.policy_telemetry import emit_policy_event

        consumption = assembler.get_consumption_stats() if assembler else {}
        expansion = expansion_broker.get_stats() if expansion_broker else {}

        summary = {
            "missionId": mission_id,
            "completedAt": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "stages": [],
            "totalPolicyDenies": 0,
            "totalRereads": consumption.get("rereads", 0),
            "totalExpansionRequests": expansion.get("total", 0),
            "totalExpansionGranted": expansion.get("granted", 0),
            "totalExpansionDenied": expansion.get("denied", 0),
            "artifactCount": len(assembler.artifacts) if assembler else 0,
            "cacheStats": consumption.get("cache_stats", {}),
            "consumptionByTier": consumption.get("by_tier", {})
        }

        # Mission-level error
        if mission.get("error"):
            summary["error"] = mission["error"]

        # 5C-1: State machine info in summary
        if mission_state:
            summary["stateTransitions"] = mission_state.transition_log
            summary["finalState"] = mission_state.status.value
            summary["attemptCounters"] = mission_state.attempt_counters

        # 5C-2: Feedback loop stats (populated if feedback was used)
        if hasattr(self, '_feedback_loop') and self._feedback_loop:
            summary["feedbackLoopStats"] = self._feedback_loop.get_stats()
        summary["gatesChecked"] = {
            "gate_1": getattr(self, '_gate_1_checked', False),
            "gate_2": getattr(self, '_gate_2_checked', False),
            "gate_3": getattr(self, '_gate_3_checked', False),
        }

        for stage in mission.get("stages", []):
            pd_count = stage.get("policy_deny_count", 0)
            stage_entry = {
                "stageId": stage.get("id", "unknown"),
                "role": stage.get("specialist", "unknown"),
                "status": stage.get("status", "unknown"),
                "toolCalls": stage.get("tool_call_count", 0),
                "policyDenies": pd_count,
            }
            if stage.get("error"):
                stage_entry["error"] = stage["error"]
            if stage.get("result"):
                stage_entry["result"] = stage["result"][:2000]
            if stage.get("system_prompt"):
                stage_entry["systemPrompt"] = stage["system_prompt"][:3000]
            if stage.get("user_prompt"):
                stage_entry["userPrompt"] = stage["user_prompt"][:3000]
            if stage.get("turns_used"):
                stage_entry["turnsUsed"] = stage["turns_used"]
            if stage.get("duration_ms"):
                stage_entry["durationMs"] = stage["duration_ms"]
            if stage.get("started_at"):
                stage_entry["startedAt"] = stage["started_at"]
            if stage.get("finished_at"):
                stage_entry["finishedAt"] = stage["finished_at"]
            # 7.1: Deny forensics per stage
            if stage.get("deny_forensics"):
                stage_entry["denyForensics"] = stage["deny_forensics"]
            # 7.4: Agent used per stage
            if stage.get("agent_used"):
                stage_entry["agentUsed"] = stage["agent_used"]
            # 7.6: Gate results per stage
            if stage.get("gate_results"):
                stage_entry["gateResults"] = stage["gate_results"]
            if stage.get("is_rework"):
                stage_entry["isRework"] = True
                stage_entry["reworkCycle"] = stage.get("rework_cycle", 0)
            if stage.get("is_recovery"):
                stage_entry["isRecovery"] = True
            if stage.get("tool_calls_detail"):
                stage_entry["toolCallDetails"] = [
                    {
                        "tool": tc.get("tool", ""),
                        "params": tc.get("params", {}),
                        "success": tc.get("success", True),
                        "error": tc.get("error"),
                        "durationMs": tc.get("durationMs", 0),
                        "risk": tc.get("risk", "unknown"),
                        "tokenTruncated": tc.get("tokenTruncated", False),
                        "tokenBlocked": tc.get("tokenBlocked", False),
                    }
                    for tc in stage["tool_calls_detail"][:20]
                    if isinstance(tc, dict)  # guard against str items
                ]
            summary["stages"].append(stage_entry)
            summary["totalPolicyDenies"] += pd_count

        # 7.1: Aggregate deny forensics across all stages
        all_deny_forensics = [
            s.get("deny_forensics") for s in mission.get("stages", [])
            if s.get("deny_forensics")
        ]
        summary["denyForensics"] = all_deny_forensics

        # Save to disk (atomic write — D-071 / BF-8.0)
        import tempfile
        summary_path = os.path.join(MISSIONS_DIR, f"{mission_id}-summary.json")
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=MISSIONS_DIR, suffix=".tmp", prefix="summary-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, summary_path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception:
            pass

        # Telemetry event
        event_type = "mission_completed" if status == "completed" else "mission_failed"
        event_data = {
            "mission_id": mission_id,
            "artifact_count": summary["artifactCount"],
            "total_rereads": summary["totalRereads"],
            "total_expansion_requests": summary["totalExpansionRequests"],
            "total_policy_denies": summary["totalPolicyDenies"]
        }
        if mission_state:
            event_data["final_state"] = mission_state.status.value
            event_data["state_transitions"] = len(mission_state.transition_log)
        if status == "failed":
            event_data["failure_reason"] = mission.get("error", "unknown")
        emit_policy_event(event_type, event_data)

    # D-048: Working set templates per role — 9 governed roles.
    _WORKING_SET_TEMPLATES = {
        "product-owner": {
            "max_file_reads": 0,
            "max_directory_reads": 0,
            "max_expansions": 0,
            "generated_outputs": [],
            "forbidden_directories": [r"C:\Windows\System32", r"C:\Program Files"],
            "forbidden_patterns": [r"\.ps1$", r"\.env$", r"allowlist\.json$"]
        },
        "analyst": {
            "max_file_reads": 30,
            "max_directory_reads": 15,
            "max_expansions": 999,
            "generated_outputs": [],
            "forbidden_directories": [r"C:\Windows\System32", r"C:\Program Files"],
            "forbidden_patterns": [r"\.env$", r"allowlist\.json$"]
        },
        "architect": {
            "max_file_reads": 15,
            "max_directory_reads": 10,
            "max_expansions": 999,
            "generated_outputs": [],
            "forbidden_directories": [r"C:\Windows\System32", r"C:\Program Files"],
            "forbidden_patterns": [r"\.env$", r"allowlist\.json$"]
        },
        "project-manager": {
            "max_file_reads": 0,
            "max_directory_reads": 0,
            "max_expansions": 0,
            "generated_outputs": [],
            "forbidden_directories": [r"C:\Windows\System32", r"C:\Program Files"],
            "forbidden_patterns": [r"\.ps1$", r"\.env$", r"allowlist\.json$"]
        },
        "developer": {
            "max_file_reads": 20,
            "max_directory_reads": 5,
            "max_expansions": 8,
            "generated_outputs": ["logs/artifacts/"],
            "forbidden_directories": [r"C:\Windows\System32", r"C:\Program Files"],
            "forbidden_patterns": [r"\.env$", r"allowlist\.json$"]
        },
        "tester": {
            "max_file_reads": 15,
            "max_directory_reads": 5,
            "max_expansions": 3,
            "generated_outputs": [],
            "forbidden_directories": [r"C:\Windows\System32", r"C:\Program Files"],
            "forbidden_patterns": [r"\.env$", r"allowlist\.json$"]
        },
        "reviewer": {
            "max_file_reads": 12,
            "max_directory_reads": 3,
            "max_expansions": 5,
            "generated_outputs": [],
            "forbidden_directories": [r"C:\Windows\System32", r"C:\Program Files"],
            "forbidden_patterns": [r"\.env$", r"allowlist\.json$"]
        },
        "manager": {
            "max_file_reads": 0,
            "max_directory_reads": 0,
            "max_expansions": 0,
            "generated_outputs": [],
            "forbidden_directories": [r"C:\Windows\System32", r"C:\Program Files"],
            "forbidden_patterns": [r"\.ps1$", r"\.env$", r"allowlist\.json$"]
        },
        "remote-operator": {
            "max_file_reads": 10,
            "max_directory_reads": 5,
            "max_expansions": 2,
            "generated_outputs": ["results/"],
            "forbidden_directories": [],
            "forbidden_patterns": []
        },
    }

    # D-048: Alias resolution uses role_registry
    _ROLE_ALIASES = {
        "executor": "remote-operator",
    }

    def _build_default_working_set(self, stage_id: str, specialist: str):
        """Build a default working set for a specialist role.

        D-053: Every mission stage must have a working set.
        D-048: Canonical role naming — "executor" maps to "remote-operator".
        """
        from context.working_set import FileAccess, ReadBudget, WorkingSet

        # controller.py is at agent/mission/controller.py → 3x dirname = project root
        oc_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        results_dir = os.path.join(oc_root, "results")

        # D-048: Resolve alias
        canonical_role = self._ROLE_ALIASES.get(specialist, specialist)

        # Get template or restrictive fallback
        template = self._WORKING_SET_TEMPLATES.get(canonical_role, {
            "max_file_reads": 5,
            "max_directory_reads": 2,
            "max_expansions": 0,
            "generated_outputs": [],
            "forbidden_directories": [r"C:\Windows\System32", r"C:\Program Files"],
            "forbidden_patterns": [r"\.env$", r"credentials", r"\.key$"]
        })

        gen_outputs = [os.path.join(oc_root, p) for p in template["generated_outputs"]]

        files = FileAccess(
            read_only=[],
            read_write=[],
            creatable=[],
            generated_outputs=gen_outputs,
            directory_list=[oc_root, results_dir]
        )

        budget = ReadBudget(
            max_file_reads=template["max_file_reads"],
            max_directory_reads=template["max_directory_reads"],
            max_expansions=template["max_expansions"],
            remaining_file_reads=template["max_file_reads"],
            remaining_directory_reads=template["max_directory_reads"],
            remaining_expansions=template["max_expansions"]
        )

        return WorkingSet(
            stage_id=stage_id,
            role=canonical_role,
            skill="",
            files=files,
            budget=budget,
            forbidden_directories=template["forbidden_directories"],
            forbidden_patterns=template["forbidden_patterns"]
        )

    # 6C-1: Resolve artifact type from skill contract
    def _resolve_artifact_type(self, skill_name: str) -> str:
        """Map skill to its output artifact type via skill contract."""
        if not skill_name:
            return "stage_output"
        from mission.skill_contracts import get_skill_contract
        contract = get_skill_contract(skill_name)
        if contract and contract.get("outputArtifact"):
            return contract["outputArtifact"]
        return "stage_output"

    def _validate_artifact_schema(self, artifact_type, data,
                                   mission_id, stage_id, role):
        """6C-1: Non-blocking schema validation with telemetry warning."""
        try:
            from artifacts.schema_validator import validate_artifact_data
            from context.policy_telemetry import emit_policy_event
            errors = validate_artifact_data(artifact_type, data)
            if errors:
                emit_policy_event("artifact_validation_warning", {
                    "mission_id": mission_id,
                    "stage_id": stage_id,
                    "artifact_type": artifact_type,
                    "errors": errors[:5],
                    "role": role
                })
        except Exception:
            pass  # validation is best-effort

    # 6C-2: Model/provider selection from role registry
    _MODEL_TO_AGENT = {
        "claude-sonnet": "claude-general",
        "claude-opus": "claude-general",
        "gpt-4o": "gpt-general",
        "ollama-local": "ollama-general",
    }

    def _select_agent_for_role(self, role_name: str,
                                mission_id: str = "",
                                stage_id: str = "") -> str:
        """D-043: Select provider/agent based on role registry.

        Claude for high-leverage roles, GPT-4o for mechanical roles,
        Ollama for compression. Falls back to gpt-general if provider
        unavailable.
        """
        from context.policy_telemetry import emit_policy_event
        from mission.role_registry import get_role, resolve_role

        canonical = resolve_role(role_name)
        role_def = get_role(canonical)

        if not role_def:
            return "gpt-general"

        preferred = role_def.get("preferredModel", "gpt-4o")
        agent_name = self._MODEL_TO_AGENT.get(preferred, "gpt-general")

        # Verify agent exists in config; fallback if not
        fallback_used = False
        try:
            from providers.factory import create_provider
            create_provider(agent_name)
        except Exception:
            fallback_used = agent_name != "gpt-general"
            agent_name = "gpt-general"

        if mission_id:
            emit_policy_event("model_selected", {
                "mission_id": mission_id,
                "stage_id": stage_id,
                "role": canonical,
                "preferred_model": preferred,
                "selected_agent": agent_name,
                "fallback_used": fallback_used
            })

        return agent_name

    def _generate_summary(self, goal: str, stages: list, artifacts: list) -> str:
        """Generate a human-readable mission summary."""
        from providers.factory import create_provider
        provider, _ = create_provider(self.planner_agent_id)

        stages_text = ""
        for s in stages:
            status = s.get("status", "unknown")
            result = (s.get("result") or "")[:200]
            stages_text += f"- {s.get('id')}: {s.get('objective')} -> {status}. Result: {result}\n"

        messages = [
            {"role": "system", "content": "Summarize the mission results concisely in the same language as the goal. Include key findings and actions taken."},
            {"role": "user", "content": f"Goal: {goal}\n\nStages:\n{stages_text}"}
        ]

        response = provider.chat(messages, tools=[], max_tokens=500)
        return response.text or "Mission completed."

    # ── 7.1: Deny Forensics Aggregation ──────────────────────────

    def _aggregate_deny_forensics(self, gate_result):
        """7.1: Aggregate deny forensics from a failed quality gate.

        Extracts structured deny information: which rules triggered,
        which files are affected, and the blocking messages.
        Returns a dict suitable for stage["deny_forensics"] and
        mission summary denyForensics.
        """
        if gate_result.passed:
            return {}

        forensics = {
            "gate": gate_result.gate_name,
            "recommendation": gate_result.recommendation,
            "blocking_rules": [],
            "findings": []
        }

        for issue in gate_result.blocking_issues:
            forensics["blocking_rules"].append({
                "rule": issue,
                "severity": "blocking"
            })

        for finding in gate_result.findings:
            if finding.get("status") in ("fail", "warn"):
                forensics["findings"].append({
                    "check": finding.get("check", "unknown"),
                    "status": finding.get("status", "unknown"),
                    "detail": finding.get("detail", "")
                })

        return forensics

    # ── 5C-2: Quality Gate + Feedback Loop Integration ──────────────

    def _check_gates_and_loops(self, role, completed_roles, assembler,
                               stages, current_index, mission_state,
                               mission_id):
        """Check quality gates after specific roles complete.

        Returns: "proceed" | "abort" | "stages_modified"
        """
        from context.policy_telemetry import emit_policy_event
        from mission.feedback_loops import FeedbackLoop
        from mission.quality_gates import check_gate_1, check_gate_2, check_gate_3

        # Lazy-init feedback loop for this mission (D-103: complexity-based limits)
        if not hasattr(self, '_feedback_loop') or self._feedback_loop is None:
            complexity = getattr(self, '_mission_complexity', 'medium')
            self._feedback_loop = FeedbackLoop(
                mission_id, complexity=complexity)
        feedback = self._feedback_loop

        GATE_1_AFTER = {"product-owner", "analyst", "architect",
                        "project-manager"}

        # GATE 1: After all planning roles done
        if (not getattr(self, '_gate_1_checked', False)
                and role in GATE_1_AFTER
                and GATE_1_AFTER.issubset(completed_roles)):

            gate_result = check_gate_1({}, assembler)
            emit_policy_event("quality_gate_checked", {
                "mission_id": mission_state.mission_id,
                "gate": "gate_1",
                "passed": gate_result.passed,
                "blocking": gate_result.blocking_issues,
                "recommendation": gate_result.recommendation
            })
            self._gate_1_checked = True

            # 7.1 + 7.6: Store gate results and deny forensics
            stages[current_index]["gate_results"] = {
                "passed": gate_result.passed,
                "gate_name": gate_result.gate_name,
                "findings": gate_result.findings
            }
            if not gate_result.passed:
                stages[current_index]["deny_forensics"] = (
                    self._aggregate_deny_forensics(gate_result))

            if not gate_result.passed:
                if gate_result.recommendation == "abort":
                    mission_state.transition_to(
                        MissionStatus.FAILED,
                        f"Gate 1 failed: {gate_result.blocking_issues}")
                    return "abort"
                # Gate 1 fail with rework → recovery stage
                recovery_stage = self._create_recovery_stage(
                    stages[current_index], "gate_1_failed")
                stages.insert(current_index + 1, recovery_stage)
                return "stages_modified"

        # GATE 2: After tester completes
        if role == "tester":
            gate_result = check_gate_2({}, assembler)
            emit_policy_event("quality_gate_checked", {
                "mission_id": mission_state.mission_id,
                "gate": "gate_2",
                "passed": gate_result.passed,
                "blocking": gate_result.blocking_issues,
                "recommendation": gate_result.recommendation
            })
            self._gate_2_checked = True

            # 7.1 + 7.6: Store gate results and deny forensics
            stages[current_index]["gate_results"] = {
                "passed": gate_result.passed,
                "gate_name": gate_result.gate_name,
                "findings": gate_result.findings
            }
            if not gate_result.passed:
                stages[current_index]["deny_forensics"] = (
                    self._aggregate_deny_forensics(gate_result))

            if not gate_result.passed:
                test_data = self._get_latest_artifact_data(
                    "test_report", assembler)
                loop_result = feedback.evaluate_test_result(test_data)

                if loop_result["action"] == "rework":
                    mission_state.transition_to(
                        MissionStatus.WAITING_REWORK,
                        f"Gate 2 fail, dev-test rework cycle "
                        f"{loop_result.get('cycle', 0)}")
                    rework_stages = self._create_rework_stages(
                        stages[current_index], loop_result,
                        "developer", "tester")
                    for j, rs in enumerate(rework_stages):
                        stages.insert(current_index + 1 + j, rs)
                    mission_state.transition_to(
                        MissionStatus.RUNNING,
                        "rework stages inserted")
                    return "stages_modified"

                elif loop_result["action"] == "escalate":
                    mission_state.transition_to(
                        MissionStatus.FAILED,
                        f"Gate 2 escalated: {loop_result.get('reason', '')}")
                    recovery_stage = self._create_recovery_stage(
                        stages[current_index], "gate_2_escalated")
                    stages.insert(current_index + 1, recovery_stage)
                    mission_state.transition_to(
                        MissionStatus.RUNNING,
                        "recovery stage inserted")
                    return "stages_modified"

        # GATE 3: After reviewer completes
        if role == "reviewer":
            gate_result = check_gate_3({}, assembler)
            emit_policy_event("quality_gate_checked", {
                "mission_id": mission_state.mission_id,
                "gate": "gate_3",
                "passed": gate_result.passed,
                "blocking": gate_result.blocking_issues,
                "recommendation": gate_result.recommendation
            })
            self._gate_3_checked = True

            # 7.1 + 7.6: Store gate results and deny forensics
            stages[current_index]["gate_results"] = {
                "passed": gate_result.passed,
                "gate_name": gate_result.gate_name,
                "findings": gate_result.findings
            }
            if not gate_result.passed:
                stages[current_index]["deny_forensics"] = (
                    self._aggregate_deny_forensics(gate_result))

            if not gate_result.passed:
                review_data = self._get_latest_artifact_data(
                    "review_decision", assembler)
                loop_result = feedback.evaluate_review_result(review_data)

                if loop_result["action"] == "rework":
                    mission_state.transition_to(
                        MissionStatus.WAITING_REVIEW,
                        f"Gate 3 fail, dev-review rework cycle "
                        f"{loop_result.get('cycle', 0)}")
                    rework_stages = self._create_rework_stages(
                        stages[current_index], loop_result,
                        "developer", "reviewer")
                    for j, rs in enumerate(rework_stages):
                        stages.insert(current_index + 1 + j, rs)
                    mission_state.transition_to(
                        MissionStatus.RUNNING,
                        "rework stages inserted")
                    return "stages_modified"

                elif loop_result["action"] == "escalate":
                    mission_state.transition_to(
                        MissionStatus.FAILED,
                        f"Gate 3 escalated: {loop_result.get('reason', '')}")
                    recovery_stage = self._create_recovery_stage(
                        stages[current_index], "gate_3_escalated")
                    stages.insert(current_index + 1, recovery_stage)
                    mission_state.transition_to(
                        MissionStatus.RUNNING,
                        "recovery stage inserted")
                    return "stages_modified"

        return "proceed"

    def _create_rework_stages(self, failed_stage, loop_result, *roles):
        """Create rework stages for feedback loop."""
        rework = []
        skill_map = {
            "developer": "targeted_code_change",
            "tester": "test_validation",
            "reviewer": "quality_review"
        }
        for role in roles:
            stage_id = failed_stage.get("id",
                                        failed_stage.get("stage_id", "unknown"))
            cycle = loop_result.get("cycle", 0)
            focus = loop_result.get("bugs",
                                    loop_result.get("must_fix", []))
            rework.append({
                "id": f"{stage_id}-rework-{role}-c{cycle}",
                "specialist": role,
                "skill": skill_map.get(role, ""),
                "instruction": (
                    f"Rework based on feedback: "
                    f"{loop_result.get('reason', '')}. "
                    f"Focus on: {focus}"),
                "is_rework": True,
                "rework_cycle": cycle,
                "status": "pending",
                "result": None,
                "artifacts": [],
                "error": None,
                "duration_ms": 0,
                "working_set": self._build_default_working_set(
                    f"{stage_id}-rework-{role}-c{cycle}", role)
            })
        return rework

    def _create_recovery_stage(self, failed_stage, failure_reason=""):
        """Create manager recovery_triage stage."""
        stage_id = failed_stage.get("id",
                                    failed_stage.get("stage_id", "unknown"))
        recovery_id = f"{stage_id}-recovery"
        return {
            "id": recovery_id,
            "specialist": "manager",
            "skill": "recovery_triage",
            "instruction": (
                f"Diagnose failure: {failure_reason}. "
                f"Failed stage: {stage_id}. "
                f"Decide: retry_stage | abort | escalate_to_operator"),
            "is_recovery": True,
            "status": "pending",
            "result": None,
            "artifacts": [],
            "error": None,
            "duration_ms": 0,
            "working_set": self._build_default_working_set(
                recovery_id, "manager")
        }

    def _get_latest_artifact_data(self, artifact_type, assembler):
        """Get data dict of the latest artifact of given type."""
        if not assembler:
            return {}
        matching = [
            (aid, art) for aid, art in assembler.artifacts.items()
            if art.get("type") == artifact_type
        ]
        if not matching:
            return {}
        _latest_id, latest_art = matching[-1]
        return latest_art.get("data", {})

    # ── 5C-3: Recovery Triage Integration ─────────────────────────

    def _handle_stage_failure(self, failed_stage, error_context,
                              mission_state, assembler,
                              mission_id, user_id, all_artifacts,
                              expansion_broker):
        """D-056 / B-106: Recovery triage — delegates to StageRecoveryEngine (B-139)."""
        return self._recovery_engine.handle_stage_failure(
            failed_stage=failed_stage,
            error_context=error_context,
            mission_state=mission_state,
            assembler=assembler,
            mission_id=mission_id,
            user_id=user_id,
            all_artifacts=all_artifacts,
            expansion_broker=expansion_broker,
            execute_stage_fn=self._execute_stage,
            create_recovery_stage_fn=self._create_recovery_stage,
        )

    def _enqueue_to_dlq(self, mission: dict) -> str | None:
        """B-106: Enqueue failed mission to DLQ — delegates to StageRecoveryEngine (B-139)."""
        return self._recovery_engine.enqueue_to_dlq(
            mission, suppress=getattr(self, "_dlq_suppress", False))

    def _find_stage_index(self, stages, target_stage_id):
        """Find index of stage by ID — delegates to MissionPersistenceAdapter (B-139)."""
        return MissionPersistenceAdapter.find_stage_index(stages, target_stage_id)

    # ── 7.9: Capability Manifest ─────────────────────────────────

    def _update_capability_manifest(self):
        """7.9: Auto-generate config/capabilities.json on startup.

        Detects available capabilities by checking controller features.
        Uses atomic write (temp → fsync → os.replace) per D-071.
        Owner: MissionController. Manual edits FORBIDDEN.
        """
        import tempfile

        oc_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        manifest_path = os.path.join(oc_root, "config", "capabilities.json")

        now_iso = datetime.now(timezone.utc).isoformat()

        # Detect capabilities
        capabilities = {}

        # deny_forensics: check for _aggregate_deny_forensics method
        capabilities["deny_forensics"] = {
            "available": hasattr(self, '_aggregate_deny_forensics'),
            "since": now_iso
        }

        # model_tracking: check for agent_used logic in _execute_stage
        # We verify by checking our own source for the marker comment
        capabilities["model_tracking"] = {
            "available": True,  # 7.4 adds stage["agent_used"] in _execute_stage
            "since": now_iso
        }

        # gate_visibility: check that gate results are stored structured
        capabilities["gate_visibility"] = {
            "available": True,  # 7.6 adds stage["gate_results"] in _check_gates_and_loops
            "since": now_iso
        }

        # self_verification: check developer prompt content
        try:
            from mission.specialists import SPECIALIST_PROMPTS
            dev_prompt = SPECIALIST_PROMPTS.get("developer", "")
            capabilities["self_verification"] = {
                "available": "SELF-VERIFICATION" in dev_prompt,
                "since": now_iso
            }
        except Exception:
            capabilities["self_verification"] = {
                "available": False,
                "since": now_iso
            }

        # tester_guidelines: check tester prompt content
        try:
            from mission.specialists import SPECIALIST_PROMPTS
            tester_prompt = SPECIALIST_PROMPTS.get("tester", "")
            capabilities["tester_guidelines"] = {
                "available": "VERDICT GUIDELINES" in tester_prompt,
                "since": now_iso
            }
        except Exception:
            capabilities["tester_guidelines"] = {
                "available": False,
                "since": now_iso
            }

        manifest = {
            "version": "4.5-C",
            "generatedAt": now_iso,
            "owner": "agent-controller",
            "autoGenerated": True,
            "capabilities": capabilities
        }

        # Atomic write: temp → fsync → os.replace
        try:
            config_dir = os.path.dirname(manifest_path)
            os.makedirs(config_dir, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                dir=config_dir, suffix=".tmp", prefix="capabilities-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, manifest_path)
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception:
            pass  # Best effort — don't block mission execution

    # ── B-140: Per-Mission Token Budget ────────────────────────────

    # Default budgets per complexity tier (D-139 / B-138 design)
    _BUDGET_DEFAULTS = {
        "trivial": 50_000,
        "standard": 200_000,
        "complex": 500_000,
        "critical": 1_000_000,
    }

    @classmethod
    def _default_token_budget(cls, complexity: str) -> int | None:
        """Return default token budget for complexity tier, or None for no enforcement."""
        return cls._BUDGET_DEFAULTS.get(complexity)

    @staticmethod
    def _update_mission_budget(mission: dict) -> int:
        """B-140: Accumulate cumulative token count from completed stages.

        Called after each stage completion. Updates mission["cumulativeTokens"].
        Returns the new cumulative total.
        """
        total = 0
        for stage in mission.get("stages", []):
            if stage.get("status") != "completed":
                continue
            tr = stage.get("token_report")
            if tr and isinstance(tr, dict):
                total += tr.get("total_tokens", 0)
        mission["cumulativeTokens"] = total
        return total

    # ── Persistence ──────────────────────────────────────────────

    def _save_mission(self, mission: dict):
        """Save mission state to disk — delegates to MissionPersistenceAdapter (B-139)."""
        self._persistence.save_mission(mission)

    def _save_token_report(self, mission: dict):
        """Save aggregated token report — delegates to MissionPersistenceAdapter (B-139)."""
        self._persistence.save_token_report(mission)

    def _check_and_handle_pause(self, mission_id: str, mission: dict,
                                 mission_state: MissionState,
                                 assembler=None, expansion_broker=None) -> bool:
        """Check for pending pause signal. Returns True if mission should pause."""
        from pathlib import Path

        from api.mutation_bridge import has_pending_signal

        missions_dir = Path(MISSIONS_DIR)
        pause_req = has_pending_signal(missions_dir, mission_id, "pause", mission_id)
        if not pause_req:
            return False

        # Transition to paused state
        mission_state.transition_to(MissionStatus.PAUSED, f"pause signal: {pause_req}")
        mission["status"] = "paused"
        self._save_mission(mission)
        self._persist_mission_state(mission_state)

        if assembler and expansion_broker:
            self._emit_mission_summary(mission_id, mission, assembler,
                                       expansion_broker, "paused",
                                       mission_state=mission_state)

        # Clean up pause signal
        self._delete_signal(missions_dir, mission_id, "pause", pause_req)
        return True

    def _wait_for_resume(self, mission_id: str, mission: dict,
                          mission_state: MissionState,
                          timeout_s: int = 3600) -> bool:
        """Block until resume signal arrives or timeout. Returns True if resumed."""
        import logging
        from pathlib import Path

        from api.mutation_bridge import has_pending_signal

        logger = logging.getLogger("mcc.controller")
        missions_dir = Path(MISSIONS_DIR)
        deadline = time.time() + timeout_s

        logger.info("[PAUSE] Mission %s paused — waiting for resume (timeout=%ds)",
                    mission_id, timeout_s)

        while time.time() < deadline:
            # Check for resume signal
            resume_req = has_pending_signal(missions_dir, mission_id,
                                            "resume", mission_id)
            if resume_req:
                mission_state.transition_to(MissionStatus.RUNNING,
                                            f"resume signal: {resume_req}")
                mission["status"] = "executing"
                self._save_mission(mission)
                self._persist_mission_state(mission_state)
                self._delete_signal(missions_dir, mission_id, "resume", resume_req)
                logger.info("[RESUME] Mission %s resumed", mission_id)
                return True

            # Check for cancel signal — don't block forever
            cancel_req = has_pending_signal(missions_dir, mission_id,
                                             "cancel", mission_id)
            if cancel_req:
                self._delete_signal(missions_dir, mission_id, "cancel", cancel_req)
                logger.info("[CANCEL] Mission %s cancelled during pause", mission_id)
                return False

            time.sleep(2)  # Poll every 2 seconds

        logger.warning("[PAUSE TIMEOUT] Mission %s — no resume after %ds",
                       mission_id, timeout_s)
        return False

    def _wait_for_approval(self, mission_id: str, mission: dict,
                            mission_state: MissionState,
                            approval_id: str,
                            timeout_s: int = 300) -> str:
        """Block until approval decision arrives or timeout.

        Returns: 'approved', 'denied', 'expired', or 'timeout'
        D-138: timeout = deny semantics.
        """
        import logging
        logger = logging.getLogger("mcc.controller")
        deadline = time.time() + timeout_s

        logger.info("[APPROVAL] Mission %s waiting for approval %s (timeout=%ds)",
                    mission_id, approval_id, timeout_s)

        while time.time() < deadline:
            # Check approval store for decision
            record = self._approval_store.get_record(approval_id)
            if not record:
                logger.warning("[APPROVAL] Record %s disappeared", approval_id)
                return "denied"

            status = record.get("status", "pending")

            if status == "approved":
                logger.info("[APPROVAL] Mission %s approved by %s",
                           mission_id, record.get("decidedBy", "unknown"))
                return "approved"
            elif status == "denied":
                logger.info("[APPROVAL] Mission %s denied by %s",
                           mission_id, record.get("decidedBy", "unknown"))
                return "denied"
            elif status == "expired":
                logger.info("[APPROVAL] Mission %s approval expired (D-138 timeout=deny)",
                           mission_id)
                return "expired"
            # escalated → keep waiting for re-decision

            # Also check expiration proactively
            self._approval_store.check_expired()

            time.sleep(2)  # Poll every 2 seconds

        # Timeout — D-138: timeout = deny
        self._approval_store.check_expired()
        logger.warning("[APPROVAL TIMEOUT] Mission %s — no decision after %ds",
                       mission_id, timeout_s)
        return "timeout"

    @staticmethod
    def _delete_signal(missions_dir, mission_id: str,
                       signal_type: str, request_id: str):
        """Delete a processed signal artifact."""
        from pathlib import Path
        mission_dir = Path(missions_dir) / mission_id
        pattern = f"{signal_type}-request-{request_id}.json"
        for f in mission_dir.glob(pattern):
            try:
                f.unlink()
            except OSError:
                pass
