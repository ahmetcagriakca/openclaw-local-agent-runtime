"""Mission Controller — orchestrates multi-agent missions."""
import json
import os
import time
from datetime import datetime, timezone

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

    def execute_mission(self, goal: str, user_id: str, session_id: str) -> dict:
        """Execute a multi-agent mission.

        1. Plan: break goal into stages
        2. Execute: run each stage with appropriate specialist
        3. Collect: gather artifacts via Context Assembler
        4. Report: return final result with structured summary
        """
        from context.assembler import ContextAssembler
        from context.expansion_broker import ExpansionBroker

        mission_id = f"mission-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
        start_time = time.time()

        # Initialize Context Assembler and Expansion Broker for this mission
        assembler = ContextAssembler(mission_id)
        expansion_broker = ExpansionBroker(mission_id)

        # Initialize mission state
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
            "finishedAt": None
        }
        self._save_mission(mission)

        # Step 1: Plan the mission (complexity-routed)
        try:
            plan, complexity = self._plan_mission(goal, mission_id)
            mission["stages"] = plan["stages"]
            mission["complexity"] = complexity
            mission["status"] = "executing"
            self._save_mission(mission)
        except Exception as e:
            mission["status"] = "failed"
            mission["error"] = f"Planning failed: {e}"
            mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
            self._save_mission(mission)
            self._emit_mission_summary(mission_id, mission, assembler,
                                       expansion_broker, "failed")
            return mission

        # Step 2: Execute each stage sequentially
        all_artifacts = []
        for i, stage in enumerate(mission["stages"]):
            mission["currentStage"] = i + 1
            stage_id = stage.get("id", f"stage-{i+1}")
            specialist = stage.get("specialist", "analyst")

            # Skip stages that failed during planning validation
            if stage.get("status") == "failed":
                mission["status"] = "failed"
                mission["error"] = stage.get("error", f"Stage {stage_id} failed during planning")
                mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                self._save_mission(mission)
                self._emit_mission_summary(mission_id, mission, assembler,
                                           expansion_broker, "failed")
                return mission

            # D-053: Fail-closed — working set must exist in mission mode
            working_set = stage.get("working_set")
            if working_set is None:
                stage["status"] = "failed"
                stage["error"] = (
                    f"POLICY: Stage {stage_id} cannot start "
                    f"without a working set in mission mode."
                )
                mission["status"] = "failed"
                mission["error"] = stage["error"]
                mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                self._save_mission(mission)
                self._emit_mission_summary(mission_id, mission, assembler,
                                           expansion_broker, "failed")
                return mission

            # 4-4: Enrich working set from discovery_map for downstream roles
            if specialist in ("developer", "tester", "reviewer"):
                working_set = self._enrich_working_set_from_discovery(
                    working_set, specialist, assembler)
                stage["working_set"] = working_set

            stage["status"] = "running"
            self._save_mission(mission)

            try:
                # Build artifact context from Assembler for this stage
                artifact_context = ""
                if mission["completedArtifactIds"]:
                    context_package = assembler.build_context_for_role(
                        role=self._ROLE_ALIASES.get(specialist, specialist),
                        skill="",
                        stage_id=stage_id,
                        artifact_ids=mission["completedArtifactIds"]
                    )
                    artifact_context = self._format_artifact_context(context_package)

                result = self._execute_stage(
                    stage, all_artifacts, mission_id, user_id,
                    artifact_context=artifact_context,
                    expansion_broker=expansion_broker
                )
                stage["status"] = "completed"
                stage["result"] = result.get("response", "")
                stage["artifacts"] = result.get("artifacts", [])
                stage["duration_ms"] = result.get("totalDurationMs", 0)
                stage["tool_call_count"] = len(result.get("toolCalls", []))
                stage["policy_deny_count"] = sum(
                    1 for tc in result.get("toolCalls", [])
                    if tc.get("policyDenied")
                )
                all_artifacts.extend(stage["artifacts"])

                # Store stage output in Assembler with D-047 header
                canonical_role = self._ROLE_ALIASES.get(specialist, specialist)
                artifact_id = assembler.store_artifact(
                    artifact_type="stage_output",
                    data={
                        "response": stage["result"],
                        "stage_id": stage_id,
                        "specialist": specialist,
                        "tool_calls": stage["tool_call_count"],
                        "raw_artifacts": stage["artifacts"]
                    },
                    stage_id=stage_id,
                    role=canonical_role,
                    skill="",
                    input_artifact_ids=list(mission["completedArtifactIds"])
                )
                mission["completedArtifactIds"].append(artifact_id)

            except Exception as e:
                stage["status"] = "failed"
                stage["error"] = str(e)
                mission["status"] = "failed"
                mission["error"] = f"Stage {i+1} failed: {e}"
                mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                self._save_mission(mission)
                self._emit_mission_summary(mission_id, mission, assembler,
                                           expansion_broker, "failed")
                return mission

            self._save_mission(mission)

        # Step 3: Generate final summary
        try:
            summary = self._generate_summary(goal, mission["stages"], all_artifacts)
        except Exception:
            summary = "Mission completed but summary generation failed."

        mission["status"] = "completed"
        mission["summary"] = summary
        mission["artifacts"] = all_artifacts
        mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
        mission["totalDurationMs"] = int((time.time() - start_time) * 1000)
        self._save_mission(mission)

        # D-055: Structured mission summary
        self._emit_mission_summary(mission_id, mission, assembler,
                                   expansion_broker, "completed")

        return mission

    def _plan_mission(self, goal: str, mission_id: str) -> tuple[dict, str]:
        """Plan mission with complexity-routed stage template.

        Returns (plan_dict, complexity_class).
        """
        from providers.factory import create_provider
        from mission.complexity_router import classify_complexity
        from mission.role_registry import resolve_role, get_role
        from mission.skill_contracts import validate_role_skill
        from context.policy_telemetry import emit_policy_event

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

        # Step 3: LLM fills in instructions
        messages = [
            {"role": "system", "content": constrained_prompt},
            {"role": "user", "content": goal}
        ]

        response = provider.chat(messages, tools=[], max_tokens=2000)

        # Parse JSON response
        text = response.text or ""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        plan = json.loads(text)
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
        agent_id = self._get_specialist_agent(specialist)
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

    def _format_artifact_context(self, context_package: list) -> str:
        """Format assembler context for LLM consumption."""
        parts = []
        for artifact_id, content, tier in context_package:
            if content is None:
                continue
            if isinstance(content, dict):
                parts.append(f"--- Artifact: {artifact_id} (tier {tier}) ---")
                parts.append(json.dumps(content, indent=2, ensure_ascii=False)[:3000])
            elif isinstance(content, str):
                parts.append(f"--- Artifact: {artifact_id} (summary, tier {tier}) ---")
                parts.append(content)
        return "\n\n".join(parts)

    def _emit_mission_summary(self, mission_id: str, mission: dict,
                               assembler, expansion_broker, status: str):
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

        for stage in mission.get("stages", []):
            pd_count = stage.get("policy_deny_count", 0)
            summary["stages"].append({
                "stageId": stage.get("id", "unknown"),
                "role": stage.get("specialist", "unknown"),
                "status": stage.get("status", "unknown"),
                "toolCalls": stage.get("tool_call_count", 0),
                "policyDenies": pd_count
            })
            summary["totalPolicyDenies"] += pd_count

        # Save to disk
        summary_path = os.path.join(MISSIONS_DIR, f"{mission_id}-summary.json")
        try:
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
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
        from context.working_set import WorkingSet, FileAccess, ReadBudget

        oc_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

    def _get_specialist_agent(self, specialist: str) -> str:
        """Map specialist role to agent ID from config."""
        # Phase 3-F: both specialists use the same provider,
        # differentiated by system prompt and tool policy.
        # Future: each specialist can use a different provider/model.
        mapping = {
            "analyst": "gpt-general",
            "executor": "gpt-general",
        }
        return mapping.get(specialist, "gpt-general")

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

    def _save_mission(self, mission: dict):
        """Save mission state to disk."""
        path = os.path.join(MISSIONS_DIR, f"{mission['missionId']}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(mission, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
