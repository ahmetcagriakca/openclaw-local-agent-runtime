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
        3. Collect: gather artifacts from each stage
        4. Report: return final result
        """
        mission_id = f"mission-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
        start_time = time.time()

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
            "currentStage": 0,
            "error": None,
            "finishedAt": None
        }
        self._save_mission(mission)

        # Step 1: Plan the mission
        try:
            plan = self._plan_mission(goal, mission_id)
            mission["stages"] = plan["stages"]
            mission["status"] = "executing"
            self._save_mission(mission)
        except Exception as e:
            mission["status"] = "failed"
            mission["error"] = f"Planning failed: {e}"
            mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
            self._save_mission(mission)
            return mission

        # Step 2: Execute each stage sequentially
        all_artifacts = []
        for i, stage in enumerate(mission["stages"]):
            mission["currentStage"] = i + 1

            # D-053: Fail-closed — working set must exist in mission mode
            working_set = stage.get("working_set")
            if working_set is None:
                stage["status"] = "failed"
                stage["error"] = (
                    f"POLICY: Stage {stage.get('id', i+1)} cannot start "
                    f"without a working set in mission mode."
                )
                mission["status"] = "failed"
                mission["error"] = stage["error"]
                mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                self._save_mission(mission)
                return mission

            stage["status"] = "running"
            self._save_mission(mission)

            try:
                result = self._execute_stage(stage, all_artifacts, mission_id, user_id)
                stage["status"] = "completed"
                stage["result"] = result.get("response", "")
                stage["artifacts"] = result.get("artifacts", [])
                stage["duration_ms"] = result.get("totalDurationMs", 0)
                all_artifacts.extend(stage["artifacts"])
            except Exception as e:
                stage["status"] = "failed"
                stage["error"] = str(e)
                mission["status"] = "failed"
                mission["error"] = f"Stage {i+1} failed: {e}"
                mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
                self._save_mission(mission)
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

        return mission

    def _plan_mission(self, goal: str, mission_id: str) -> dict:
        """Use planner LLM to break goal into stages."""
        from providers.factory import create_provider

        provider, _ = create_provider(self.planner_agent_id)

        planning_prompt = """You are a mission planner for a Windows automation system. Break the user's request into sequential stages. Each stage is executed by a specialist agent.

Available specialists:
- "analyst": Can read files, search content, get system info, check processes, network — READ ONLY operations
- "executor": Can write files, open apps, manage clipboard, submit tasks — WRITE/ACTION operations

Rules:
- Use "analyst" for any information gathering, research, or read operations
- Use "executor" for any write, create, launch, or modification operations
- Keep stages minimal — don't over-plan
- Each stage should have a clear, single objective
- Later stages can reference results from earlier stages

Respond ONLY with a JSON object, no markdown, no explanation:
{
  "stages": [
    {
      "id": "stage-1",
      "specialist": "analyst",
      "objective": "What this stage should accomplish",
      "instruction": "Specific instruction for the specialist agent"
    }
  ]
}"""

        messages = [
            {"role": "system", "content": planning_prompt},
            {"role": "user", "content": goal}
        ]

        response = provider.chat(messages, tools=[], max_tokens=1000)

        # Parse JSON response
        text = response.text or ""
        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        plan = json.loads(text)

        # Validate and enrich stages
        for stage in plan.get("stages", []):
            stage["status"] = "pending"
            stage["result"] = None
            stage["artifacts"] = []
            stage["error"] = None
            stage["duration_ms"] = 0
            # D-053: Assign default working set per specialist role
            stage["working_set"] = self._build_default_working_set(
                stage.get("id", "unknown"),
                stage.get("specialist", "analyst")
            )

        return plan

    def _execute_stage(self, stage: dict, previous_artifacts: list,
                       mission_id: str, user_id: str) -> dict:
        """Execute a single stage with the appropriate specialist."""
        specialist = stage.get("specialist", "analyst")
        instruction = stage.get("instruction", stage.get("objective", ""))

        # Build context from previous artifacts
        context = ""
        if previous_artifacts:
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

        # Get specialist agent ID from mapping
        agent_id = self._get_specialist_agent(specialist)

        # Run the agent (reuse existing agent runner)
        from oc_agent_runner_lib import run_agent_with_config

        # Pass working set to agent runner for enforcement
        working_set = stage.get("working_set")

        result = run_agent_with_config(
            message=full_instruction,
            agent_id=agent_id,
            user_id=user_id,
            session_id=f"{mission_id}-{stage.get('id', 'stage')}",
            max_turns=10,
            tool_policy=specialist,
            working_set=working_set
        )

        return result

    def _build_default_working_set(self, stage_id: str, specialist: str):
        """Build a default working set for a specialist role.

        D-053: Every mission stage must have a working set.
        Default sets are permissive — future sprints will narrow these
        based on discovery map and skill contracts.
        """
        from context.working_set import WorkingSet, FileAccess, ReadBudget

        # Default paths — permissive for now, will be narrowed in Sprint 3+
        oc_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        results_dir = os.path.join(oc_root, "results")

        if specialist == "executor":
            files = FileAccess(
                read_only=[],
                read_write=[],
                creatable=[],
                generated_outputs=[results_dir],
                directory_list=[oc_root, results_dir]
            )
            budget = ReadBudget(
                max_file_reads=10, max_directory_reads=5, max_expansions=2,
                remaining_file_reads=10, remaining_directory_reads=5,
                remaining_expansions=2
            )
        else:
            # analyst and other read-only roles
            files = FileAccess(
                read_only=[],
                read_write=[],
                creatable=[],
                generated_outputs=[],
                directory_list=[oc_root, results_dir]
            )
            budget = ReadBudget(
                max_file_reads=20, max_directory_reads=10, max_expansions=3,
                remaining_file_reads=20, remaining_directory_reads=10,
                remaining_expansions=3
            )

        return WorkingSet(
            stage_id=stage_id,
            role=specialist,
            skill="",
            files=files,
            budget=budget,
            forbidden_directories=[
                r"C:\Windows\System32",
                r"C:\Program Files",
            ],
            forbidden_patterns=[r"\.env$", r"credentials", r"\.key$"]
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
