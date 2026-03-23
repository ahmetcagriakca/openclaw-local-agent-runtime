"""Feedback loops — Dev-Tester and Dev-Reviewer rework cycle management."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from context.policy_telemetry import emit_policy_event


@dataclass
class FeedbackLoop:
    """Tracks rework cycles. D-034: Dev-Tester max 3, Dev-Reviewer max 2."""
    mission_id: str
    max_dev_test_cycles: int = 3
    max_dev_review_cycles: int = 2
    dev_test_count: int = 0
    dev_review_count: int = 0
    rework_history: list = field(default_factory=list)

    def evaluate_test_result(self, test_report_data: dict) -> dict:
        """After Tester produces test_report, decide next action.

        Returns: {action, reason, cycle, [bugs]}
        Actions: "proceed" | "rework" | "escalate"
        """
        verdict = test_report_data.get("verdict", "unknown")

        if verdict in ("pass", "conditional_pass"):
            return {"action": "proceed",
                    "reason": f"Test verdict: {verdict}",
                    "cycle": self.dev_test_count}

        self.dev_test_count += 1

        if self.dev_test_count > self.max_dev_test_cycles:
            self._log_rework("dev_test", "escalate",
                             "Max dev-test cycles exceeded")
            emit_policy_event("feedback_loop_escalated", {
                "mission_id": self.mission_id, "loop": "dev_test",
                "cycle": self.dev_test_count,
                "max": self.max_dev_test_cycles,
                "reason": "max_cycles_exceeded"})
            return {"action": "escalate",
                    "reason": f"Dev-Test cycle {self.dev_test_count}/{self.max_dev_test_cycles} exceeded",
                    "cycle": self.dev_test_count}

        bugs = test_report_data.get("bugs", [])
        self._log_rework("dev_test", "rework",
                         f"{len(bugs)} bugs, cycle {self.dev_test_count}")
        emit_policy_event("feedback_loop_rework", {
            "mission_id": self.mission_id, "loop": "dev_test",
            "cycle": self.dev_test_count,
            "max": self.max_dev_test_cycles,
            "bug_count": len(bugs)})

        return {"action": "rework",
                "reason": f"Test failed with {len(bugs)} bugs (cycle {self.dev_test_count}/{self.max_dev_test_cycles})",
                "cycle": self.dev_test_count,
                "bugs": bugs}

    def evaluate_review_result(self, review_decision_data: dict) -> dict:
        """After Reviewer produces review_decision, decide next action.

        Returns: {action, reason, cycle, [must_fix]}
        Actions: "proceed" | "rework" | "escalate"
        """
        decision = review_decision_data.get("decision", "unknown")

        if decision == "approve":
            return {"action": "proceed",
                    "reason": "Review approved",
                    "cycle": self.dev_review_count}

        if decision == "reject":
            self._log_rework("dev_review", "escalate", "Review rejected")
            emit_policy_event("feedback_loop_escalated", {
                "mission_id": self.mission_id, "loop": "dev_review",
                "cycle": self.dev_review_count,
                "reason": "review_rejected"})
            return {"action": "escalate",
                    "reason": "Reviewer rejected — escalating to manager",
                    "cycle": self.dev_review_count}

        # request_changes
        self.dev_review_count += 1

        if self.dev_review_count > self.max_dev_review_cycles:
            self._log_rework("dev_review", "escalate",
                             "Max dev-review cycles exceeded")
            emit_policy_event("feedback_loop_escalated", {
                "mission_id": self.mission_id, "loop": "dev_review",
                "cycle": self.dev_review_count,
                "max": self.max_dev_review_cycles,
                "reason": "max_cycles_exceeded"})
            return {"action": "escalate",
                    "reason": f"Dev-Review cycle {self.dev_review_count}/{self.max_dev_review_cycles} exceeded",
                    "cycle": self.dev_review_count}

        findings = review_decision_data.get("findings", [])
        must_fix = [f for f in findings
                    if f.get("severity") in ("critical", "major")]
        self._log_rework("dev_review", "rework",
                         f"{len(must_fix)} must-fix, cycle {self.dev_review_count}")
        emit_policy_event("feedback_loop_rework", {
            "mission_id": self.mission_id, "loop": "dev_review",
            "cycle": self.dev_review_count,
            "max": self.max_dev_review_cycles,
            "finding_count": len(findings),
            "must_fix_count": len(must_fix)})

        return {"action": "rework",
                "reason": f"Changes requested: {len(must_fix)} must-fix (cycle {self.dev_review_count}/{self.max_dev_review_cycles})",
                "cycle": self.dev_review_count,
                "must_fix": must_fix}

    def get_stats(self) -> dict:
        return {"dev_test_cycles": self.dev_test_count,
                "dev_review_cycles": self.dev_review_count,
                "total_reworks": len(self.rework_history),
                "history": self.rework_history}

    def _log_rework(self, loop_type, action, detail):
        self.rework_history.append({
            "loop": loop_type, "action": action, "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat()})
