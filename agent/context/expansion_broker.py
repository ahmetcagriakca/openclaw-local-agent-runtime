"""Expansion broker — D-042 working set expansion request handling."""
from datetime import datetime, timezone


class ExpansionBroker:
    """D-042: Handle working set expansion requests."""

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.requests = []

    def request_expansion(self, role: str, stage_id: str,
                         requested_files: list = None,
                         requested_artifacts: list = None,
                         reason: str = "") -> dict:
        """Process an expansion request.

        Returns D-042 schema-compliant expansion record.
        """
        # Budget check — role-based max expansions
        role_max = {
            "developer": 8, "tester": 3, "reviewer": 5,
            "analyst": 999, "architect": 999  # self-expanding
        }

        max_allowed = role_max.get(role, 0)
        prior_grants = sum(
            1 for r in self.requests
            if r["requestingRole"] == role
            and r["stageId"] == stage_id
            and r["decision"] == "granted"
        )

        if max_allowed == 0:
            decision = "denied"
            deny_reason = f"Role '{role}' has no expansion rights"
        elif prior_grants >= max_allowed:
            decision = "denied"
            deny_reason = f"Expansion budget exhausted ({prior_grants}/{max_allowed})"
        elif not reason:
            decision = "denied"
            deny_reason = "Expansion request requires justification"
        else:
            decision = "granted"
            deny_reason = None

        record = {
            "type": "working_set_expansion",
            "requestingRole": role,
            "missionId": self.mission_id,
            "stageId": stage_id,
            "requested": {
                "files": requested_files or [],
                "artifacts": requested_artifacts or [],
                "reason": reason
            },
            "decision": decision,
            "decidedBy": "controller",
            "budgetImpact": {
                "priorGrants": prior_grants,
                "maxAllowed": max_allowed,
                "remainingAfter": max(0, max_allowed - prior_grants - (1 if decision == "granted" else 0))
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if deny_reason:
            record["denyReason"] = deny_reason

        self.requests.append(record)
        return record

    def get_expansion_history(self, role: str = None,
                              stage_id: str = None) -> list:
        """Get expansion request history with optional filters."""
        result = self.requests
        if role:
            result = [r for r in result if r["requestingRole"] == role]
        if stage_id:
            result = [r for r in result if r["stageId"] == stage_id]
        return result

    def get_stats(self) -> dict:
        total = len(self.requests)
        granted = sum(1 for r in self.requests if r["decision"] == "granted")
        denied = total - granted
        return {"total": total, "granted": granted, "denied": denied}
