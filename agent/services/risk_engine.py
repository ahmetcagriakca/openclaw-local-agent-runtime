"""Deterministic risk classification engine."""
import re

# Risk levels in order of severity
RISK_LEVELS = ["low", "medium", "high", "critical", "blocked"]

# Actions per risk level
RISK_ACTIONS = {
    "low": "auto_execute",
    "medium": "auto_execute",
    "high": "require_approval",
    "critical": "require_approval_confirmed",
    "blocked": "reject"
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
