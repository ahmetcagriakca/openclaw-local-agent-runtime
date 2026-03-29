"""Typed artifact storage and management."""
import json
import os
from datetime import datetime, timezone

from utils.atomic_write import atomic_write_json

ARTIFACTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs", "artifacts"
)

ARTIFACT_TYPES = {
    "text_response": {"description": "Simple text answer to user", "fields": ["message"]},
    "file_created": {"description": "Agent created or modified a file", "fields": ["path", "filename", "size"]},
    "file_content": {"description": "Agent read file contents", "fields": ["path", "content_preview", "size"]},
    "screenshot": {"description": "Agent captured a screenshot", "fields": ["path", "filename", "resolution"]},
    "process_list": {"description": "Agent listed running processes", "fields": ["count", "top_processes"]},
    "system_info": {"description": "Agent retrieved system information", "fields": ["cpu", "ram", "disk", "uptime"]},
    "health_report": {"description": "Agent retrieved system health status", "fields": ["overall", "components"]},
    "task_submitted": {"description": "Agent submitted a runtime task", "fields": ["task_id", "task_name", "status"]},
    "task_status": {"description": "Agent checked a runtime task status", "fields": ["task_id", "task_status"]},
    "approval_needed": {"description": "Agent is waiting for user approval", "fields": ["approval_id", "tool", "risk"]},
    "error": {"description": "Agent encountered an error", "fields": ["error", "recoverable"]},
    "command_result": {"description": "Generic tool execution result", "fields": ["tool", "output_preview"]},
}


class ArtifactStore:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.artifacts = []
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    def add(self, artifact_type: str, data: dict) -> dict:
        """Add a typed artifact to the session."""
        artifact = {
            "type": artifact_type,
            "data": data,
            "ts": datetime.now(timezone.utc).isoformat()
        }
        self.artifacts.append(artifact)
        return artifact

    def add_from_tool_result(self, tool_name: str, params: dict,
                              output: str, success: bool) -> dict:
        """Automatically create typed artifact from tool result."""
        if not success:
            return self.add("error", {
                "error": output[:500],
                "recoverable": True
            })

        if tool_name == "get_system_info":
            return self._parse_system_info(output)
        elif tool_name == "list_processes":
            return self._parse_process_list(output, params)
        elif tool_name == "take_screenshot":
            return self._parse_screenshot(output)
        elif tool_name == "get_system_health":
            return self._parse_health(output)
        elif tool_name == "read_file":
            return self._parse_file_content(output, params)
        elif tool_name == "write_file":
            return self._parse_file_created(output, params)
        elif tool_name == "submit_runtime_task":
            return self._parse_task_submitted(output)
        elif tool_name == "check_runtime_task":
            return self._parse_task_status(output, params)
        else:
            return self.add("command_result", {
                "tool": tool_name,
                "output_preview": output[:300]
            })

    def get_all(self) -> list:
        """Return all artifacts for the session."""
        return self.artifacts

    def save_session(self):
        """Save session artifacts to disk."""
        if not self.artifacts:
            return
        session_file = os.path.join(ARTIFACTS_DIR, f"{self.session_id}.json")
        try:
            atomic_write_json(session_file, {
                "sessionId": self.session_id,
                "artifacts": self.artifacts,
                "savedAt": datetime.now(timezone.utc).isoformat()
            })
        except Exception:
            pass

    # --- Parsers ---

    def _parse_system_info(self, output: str) -> dict:
        data = {}
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("CPU:"):
                data["cpu"] = line
            elif line.startswith("RAM:"):
                data["ram"] = line
            elif line.startswith("Disk:"):
                data["disk"] = line
            elif line.startswith("Uptime:"):
                data["uptime"] = line
        return self.add("system_info", data)

    def _parse_process_list(self, output: str, params: dict) -> dict:
        lines = [ln.strip() for ln in output.split("\n") if ln.strip()]
        return self.add("process_list", {
            "count": len(lines),
            "top_processes": lines[:5]
        })

    def _parse_screenshot(self, output: str) -> dict:
        path = ""
        if "saved:" in output.lower() or "Screenshot" in output:
            parts = output.split(":")
            if len(parts) >= 2:
                path = ":".join(parts[1:]).strip()
        filename = os.path.basename(path) if path else "screenshot.png"
        return self.add("screenshot", {
            "path": path,
            "filename": filename,
            "resolution": "primary screen"
        })

    def _parse_health(self, output: str) -> dict:
        try:
            health = json.loads(output)
            return self.add("health_report", {
                "overall": health.get("overall", "unknown"),
                "components": {k: v.get("status") for k, v in health.get("components", {}).items()}
            })
        except (json.JSONDecodeError, AttributeError):
            return self.add("health_report", {"overall": "unknown", "components": {}})

    def _parse_file_content(self, output: str, params: dict) -> dict:
        return self.add("file_content", {
            "path": params.get("path", ""),
            "content_preview": output[:200],
            "size": len(output)
        })

    def _parse_file_created(self, output: str, params: dict) -> dict:
        filename = params.get("filename", "")
        path = f"C:\\Users\\AKCA\\oc\\results\\{filename}"
        return self.add("file_created", {
            "path": path,
            "filename": filename,
            "size": len(params.get("content", ""))
        })

    def _parse_task_submitted(self, output: str) -> dict:
        try:
            result = json.loads(output)
            return self.add("task_submitted", {
                "task_id": result.get("taskId", ""),
                "task_name": result.get("taskName", ""),
                "status": result.get("status", "")
            })
        except (json.JSONDecodeError, AttributeError):
            return self.add("task_submitted", {"task_id": "", "task_name": "", "status": output[:100]})

    def _parse_task_status(self, output: str, params: dict) -> dict:
        try:
            result = json.loads(output)
            return self.add("task_status", {
                "task_id": params.get("task_id", ""),
                "task_status": result.get("taskStatus", result.get("status", ""))
            })
        except (json.JSONDecodeError, AttributeError):
            return self.add("task_status", {"task_id": params.get("task_id", ""), "task_status": output[:100]})
