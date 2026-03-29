"""Deterministic risk classification engine.

D-128: Mission-level risk classification.
- 4 levels: low/medium/high/critical (+ blocked for commands)
- Static tool-name mapping
- Unknown tools default to high (fail-safe)
- Computed once at mission creation, persisted, never recomputed
"""
import re

# Risk levels in order of severity
RISK_LEVELS = ["low", "medium", "high", "critical", "blocked"]

# D-128: Risk level ordering for mission-level classification (max of all tools)
RISK_SEVERITY = {"low": 0, "medium": 1, "high": 2, "critical": 3, "blocked": 4}

# Actions per risk level
RISK_ACTIONS = {
    "low": "auto_execute",
    "medium": "auto_execute",
    "high": "require_approval",
    "critical": "require_approval_confirmed",
    "blocked": "reject"
}

# D-128: Static tool-name to risk-level mapping
TOOL_RISK_MAP = {
    # Low: read-only, no side effects
    "file_read": "low",
    "search": "low",
    "list_files": "low",
    "get_health": "low",
    "get_status": "low",
    "list_missions": "low",
    "get_capabilities": "low",
    "read_file": "low",
    "search_files": "low",
    # Medium: write tools, reversible
    "file_write": "medium",
    "create_directory": "medium",
    "write_file": "medium",
    "create_file": "medium",
    "copy_file": "medium",
    "move_file": "medium",
    "send_message": "medium",
    # High: network/exec, potentially irreversible
    "http_request": "high",
    "run_command": "high",
    "shell_exec": "high",
    "execute_powershell": "high",
    "web_request": "high",
    "api_call": "high",
    # Critical: admin/system, broad impact
    "system_config": "critical",
    "service_restart": "critical",
    "delete_recursive": "critical",
    "format_disk": "critical",
    "modify_registry": "critical",
}

# Blocked command patterns — NEVER allowed regardless of tool or approval
BLOCKED_PATTERNS = [
    r"Invoke-Expression.*http",
    r"Net\.WebClient.*DownloadString",
    r"encodedcommand",
    r"bypass.*executionpolicy",
    r"reg.*add.*HKLM.*Security",
    r"netsh.*advfirewall.*off",
    r"Disable-WindowsOptionalFeature.*Defender",
    r"Remove-Item.*-Recurse.*C:\\Windows",
    r"Format-Volume",
    r"Clear-Disk",
]


class RiskEngine:
    def __init__(self):
        self.blocked_patterns = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]

    def classify(self, tool_name: str, tool_risk: str, powershell_command: str = None) -> dict:
        """Classify risk for a tool call.

        Returns: {
            "risk": "low"|"medium"|"high"|"critical"|"blocked",
            "action": "auto_execute"|"require_approval"|"require_approval_confirmed"|"reject",
            "reason": str
        }
        """
        # Step 1: Check blocked patterns against the actual command
        if powershell_command:
            for pattern in self.blocked_patterns:
                if pattern.search(powershell_command):
                    return {
                        "risk": "blocked",
                        "action": "reject",
                        "reason": f"Blocked pattern detected: {pattern.pattern}"
                    }

        # Step 2: Use tool's declared risk level
        risk = tool_risk if tool_risk in RISK_LEVELS else "medium"
        action = RISK_ACTIONS.get(risk, "require_approval")

        return {
            "risk": risk,
            "action": action,
            "reason": f"Tool '{tool_name}' has risk level: {risk}"
        }

    def classify_mission(self, tool_names: list[str]) -> str:
        """Classify mission risk level based on all tools used (D-128).

        Returns the highest risk level among all tools.
        Unknown tools default to 'high' (fail-safe).
        Empty tool list returns 'low'.
        """
        if not tool_names:
            return "low"

        max_severity = 0
        for tool_name in tool_names:
            level = TOOL_RISK_MAP.get(tool_name, "high")  # D-128: unknown = high
            severity = RISK_SEVERITY.get(level, 2)  # default to high severity
            max_severity = max(max_severity, severity)

        # Map severity back to level name
        for level, sev in RISK_SEVERITY.items():
            if sev == max_severity:
                return level
        return "high"
