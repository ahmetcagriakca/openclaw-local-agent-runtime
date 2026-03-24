"""Sprint 6D tests — Structured Artifact Extraction + Strict Approval Enforcement."""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add agent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mission.artifact_extractor import extract_artifact_fields


class TestArtifactExtractor(unittest.TestCase):
    """Test artifact_extractor.py — structured field extraction."""

    # --- JSON extraction ---

    def test_01_json_in_response_direct_parse(self):
        """JSON in response -> direct parse."""
        result = extract_artifact_fields(
            "test_report", '{"verdict": "pass", "bugs": []}')
        self.assertEqual(result, {"verdict": "pass", "bugs": []})

    def test_02_json_in_markdown_fence(self):
        """JSON in markdown code fence."""
        text = 'Results:\n```json\n{"verdict": "fail"}\n```'
        result = extract_artifact_fields("test_report", text)
        self.assertEqual(result["verdict"], "fail")

    def test_03_json_embedded_in_text(self):
        """JSON object embedded in surrounding text."""
        text = 'Analysis complete. {"recommendation": "proceed", "feasibility": "high"} End.'
        result = extract_artifact_fields("analysis_report", text)
        self.assertEqual(result["recommendation"], "proceed")
        self.assertEqual(result["feasibility"], "high")

    # --- Regex fallback ---

    def test_04_regex_verdict_in_text(self):
        """Regex fallback — verdict keyword in text."""
        result = extract_artifact_fields(
            "test_report", "Test result: PASS. All criteria met.")
        self.assertEqual(result["verdict"], "pass")

    def test_05_regex_verdict_fail(self):
        """Regex fallback — FAIL keyword."""
        result = extract_artifact_fields(
            "test_report", "Verdict: FAIL — 3 tests broken")
        self.assertEqual(result["verdict"], "fail")

    def test_06_regex_review_approve(self):
        """Review decision — APPROVE keyword."""
        result = extract_artifact_fields(
            "review_decision", "Decision: APPROVE. Code looks good.")
        self.assertEqual(result["decision"], "approve")

    def test_07_regex_review_approved_alias(self):
        """Review decision — APPROVED normalized to approve."""
        result = extract_artifact_fields(
            "review_decision", "The code is APPROVED for merge.")
        self.assertEqual(result["decision"], "approve")

    def test_08_regex_analysis_reject(self):
        """Analysis — reject recommendation."""
        result = extract_artifact_fields(
            "analysis_report", "Recommendation: reject due to risk")
        self.assertEqual(result["recommendation"], "reject")

    # --- Heuristic fallback ---

    def test_09_heuristic_fail_indicators(self):
        """Heuristic — fail indicators outweigh pass."""
        result = extract_artifact_fields(
            "test_report", "Found 3 bugs and errors in code")
        self.assertEqual(result["verdict"], "fail")

    def test_10_heuristic_pass_indicators(self):
        """Heuristic — pass indicators present."""
        result = extract_artifact_fields(
            "test_report", "Everything looks ok, tests are successful")
        self.assertEqual(result["verdict"], "pass")

    def test_11_heuristic_default_conditional(self):
        """Heuristic — no indicators -> conditional_pass."""
        result = extract_artifact_fields(
            "test_report", "Reviewed the implementation thoroughly")
        self.assertEqual(result["verdict"], "conditional_pass")

    def test_12_heuristic_review_request_changes(self):
        """Heuristic review — change indicators."""
        result = extract_artifact_fields(
            "review_decision", "Need to change error handling")
        self.assertEqual(result["decision"], "request_changes")

    # --- Code delivery ---

    def test_13_code_delivery_file_extraction(self):
        """Code delivery — extract file paths."""
        text = "Modified agent/services/tool_catalog.py and agent/mission/controller.py"
        result = extract_artifact_fields("code_delivery", text)
        self.assertIn("agent/services/tool_catalog.py", result["touched_files"])
        self.assertIn("agent/mission/controller.py", result["touched_files"])

    def test_14_code_delivery_no_files(self):
        """Code delivery — no recognizable file paths."""
        result = extract_artifact_fields(
            "code_delivery", "Made some changes to the system")
        self.assertEqual(result["touched_files"], [])

    # --- Discovery map ---

    def test_15_discovery_map_file_paths(self):
        """Discovery map — extract file paths."""
        text = "Found agent/services/tool_catalog.py and agent/mission/controller.py"
        result = extract_artifact_fields("discovery_map", text)
        self.assertGreaterEqual(len(result["relevant_files"]), 2)
        self.assertIn("working_set_recommendations", result)

    # --- Requirements brief ---

    def test_16_requirements_brief_title(self):
        """Requirements brief — extract title."""
        text = "Title: Add new monitoring tool\nSummary: We need to add..."
        result = extract_artifact_fields("requirements_brief", text)
        self.assertEqual(result["title"], "Add new monitoring tool")
        self.assertIn("summary", result)
        self.assertIn("requirements", result)

    def test_17_requirements_brief_fallback(self):
        """Requirements brief — first line as title fallback."""
        text = "Implement CPU monitoring\nThis requires changes to..."
        result = extract_artifact_fields("requirements_brief", text)
        self.assertEqual(result["title"], "Implement CPU monitoring")

    # --- Work plan ---

    def test_18_work_plan_tasks(self):
        """Work plan — extract numbered tasks."""
        text = "Task 1: Read existing code\nTask 2: Implement changes\nTask 3: Test"
        result = extract_artifact_fields("work_plan", text)
        self.assertEqual(len(result["tasks"]), 3)
        self.assertEqual(result["tasks"][0]["id"], "TASK-1")

    # --- Recovery decision ---

    def test_19_recovery_retry(self):
        """Recovery decision — retry_stage."""
        result = extract_artifact_fields(
            "recovery_decision", "Should retry_stage, transient error")
        self.assertEqual(result["recovery_action"], "retry_stage")

    def test_20_recovery_escalate(self):
        """Recovery decision — escalate heuristic."""
        result = extract_artifact_fields(
            "recovery_decision", "Need to escalate this to operator")
        self.assertEqual(result["recovery_action"], "escalate_to_operator")

    def test_21_recovery_abort_default(self):
        """Recovery decision — abort as default."""
        result = extract_artifact_fields(
            "recovery_decision", "Cannot proceed with current state")
        self.assertEqual(result["recovery_action"], "abort")

    # --- Edge cases ---

    def test_22_empty_response(self):
        """Empty response -> empty dict."""
        self.assertEqual(extract_artifact_fields("test_report", ""), {})

    def test_23_none_response(self):
        """None response -> empty dict."""
        self.assertEqual(extract_artifact_fields("test_report", None), {})

    def test_24_unknown_type(self):
        """Unknown artifact type -> empty dict."""
        self.assertEqual(extract_artifact_fields("unknown_type", "some text"), {})

    # --- Security concerns in review ---

    def test_25_review_security_concerns(self):
        """Review decision detects security keywords."""
        result = extract_artifact_fields(
            "review_decision", "Found XSS vulnerability in input handling")
        self.assertIsInstance(result["security_concerns"], list)
        self.assertTrue(any("xss" in c["description"] for c in result["security_concerns"]))

    def test_26_review_no_security_concerns(self):
        """Review decision — no security issues."""
        result = extract_artifact_fields(
            "review_decision", "Code looks clean, APPROVE")
        self.assertEqual(result["security_concerns"], "none")

    # --- Analysis feasibility ---

    def test_27_analysis_feasibility(self):
        """Analysis — feasibility extraction."""
        result = extract_artifact_fields(
            "analysis_report", "Feasibility: high. Recommendation: proceed")
        self.assertEqual(result["feasibility"], "high")
        self.assertEqual(result["recommendation"], "proceed")

    def test_28_analysis_feasibility_default(self):
        """Analysis — feasibility defaults to medium."""
        result = extract_artifact_fields(
            "analysis_report", "This looks doable. PROCEED")
        self.assertEqual(result["feasibility"], "medium")

    # --- Bug extraction ---

    def test_29_test_report_bugs(self):
        """Test report — bug extraction."""
        text = "Verdict: fail\nBug 1: Missing null check\nBug 2: Off-by-one error"
        result = extract_artifact_fields("test_report", text)
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(len(result["bugs"]), 2)


class TestStrictApprovalEnforcement(unittest.TestCase):
    """Test approval_service.py — strict approve <id> / deny <id>."""

    def _make_service(self):
        """Create ApprovalService with mocked externals."""
        with patch.dict(os.environ, {
            "OC_TELEGRAM_BOT_TOKEN": "test-token",
            "OC_TELEGRAM_CHAT_ID": "12345"
        }):
            from services.approval_service import ApprovalService
            svc = ApprovalService(timeout_seconds=5)
            svc.bot_token = "test-token"
            svc.chat_id = "12345"
            return svc

    def _mock_updates(self, svc, messages, pending_count=1):
        """Mock Telegram getUpdates and pending count."""
        updates = []
        for i, text in enumerate(messages):
            updates.append({
                "message": {
                    "date": 1000 + i,
                    "text": text,
                    "chat": {"id": 12345}
                }
            })

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": updates}

        svc._count_pending_approvals = MagicMock(return_value=pending_count)
        svc._send_telegram = MagicMock()

        return mock_resp

    def test_30_strict_approve_with_id(self):
        """Strict ID match — approve."""
        svc = self._make_service()
        mock_resp = self._mock_updates(svc, ["approve apv-20260324-001"])

        with patch("requests.get", return_value=mock_resp):
            result = svc._peek_telegram_reply("apv-20260324-001", 999)
        self.assertEqual(result, "approve")

    def test_31_strict_deny_with_id(self):
        """Strict ID match — deny."""
        svc = self._make_service()
        mock_resp = self._mock_updates(svc, ["deny apv-20260324-001"])

        with patch("requests.get", return_value=mock_resp):
            result = svc._peek_telegram_reply("apv-20260324-001", 999)
        self.assertEqual(result, "deny")

    def test_32_single_pending_yes_approve_with_deprecation(self):
        """Single pending + 'yes' -> approve with deprecation warning."""
        svc = self._make_service()
        mock_resp = self._mock_updates(svc, ["yes"], pending_count=1)

        with patch("requests.get", return_value=mock_resp):
            result = svc._peek_telegram_reply("apv-20260324-001", 999)
        self.assertEqual(result, "approve")
        svc._send_telegram.assert_called_once()
        call_args = svc._send_telegram.call_args[0][0]
        self.assertIn("DEPRECATION", call_args)

    def test_33_multiple_pending_yes_rejected(self):
        """Multiple pending + 'yes' -> rejected (None)."""
        svc = self._make_service()
        mock_resp = self._mock_updates(svc, ["yes"], pending_count=3)

        with patch("requests.get", return_value=mock_resp):
            result = svc._peek_telegram_reply("apv-20260324-001", 999)
        self.assertIsNone(result)
        svc._send_telegram.assert_called_once()
        call_args = svc._send_telegram.call_args[0][0]
        self.assertIn("Ambiguous", call_args)

    def test_34_multiple_pending_strict_id_still_works(self):
        """Multiple pending + 'approve <id>' -> approve (strict always works)."""
        svc = self._make_service()
        mock_resp = self._mock_updates(
            svc, ["approve apv-20260324-001"], pending_count=3)

        with patch("requests.get", return_value=mock_resp):
            result = svc._peek_telegram_reply("apv-20260324-001", 999)
        self.assertEqual(result, "approve")

    def test_35_wrong_id_returns_none(self):
        """Wrong ID -> None."""
        svc = self._make_service()
        mock_resp = self._mock_updates(svc, ["approve apv-different-id"])

        with patch("requests.get", return_value=mock_resp):
            result = svc._peek_telegram_reply("apv-20260324-001", 999)
        self.assertIsNone(result)

    def test_36_unrelated_message_returns_none(self):
        """Unrelated message -> None."""
        svc = self._make_service()
        mock_resp = self._mock_updates(svc, ["hello"])

        with patch("requests.get", return_value=mock_resp):
            result = svc._peek_telegram_reply("apv-20260324-001", 999)
        self.assertIsNone(result)

    def test_37_single_pending_deny_with_deprecation(self):
        """Single pending + 'hayir' -> deny with deprecation."""
        svc = self._make_service()
        mock_resp = self._mock_updates(svc, ["hayır"], pending_count=1)

        with patch("requests.get", return_value=mock_resp):
            result = svc._peek_telegram_reply("apv-20260324-001", 999)
        self.assertEqual(result, "deny")
        call_args = svc._send_telegram.call_args[0][0]
        self.assertIn("DEPRECATION", call_args)

    def test_38_multiple_pending_deny_rejected(self):
        """Multiple pending + 'no' -> rejected."""
        svc = self._make_service()
        mock_resp = self._mock_updates(svc, ["no"], pending_count=2)

        with patch("requests.get", return_value=mock_resp):
            result = svc._peek_telegram_reply("apv-20260324-001", 999)
        self.assertIsNone(result)

    def test_39_old_message_ignored(self):
        """Messages before send_time are ignored."""
        svc = self._make_service()
        mock_resp = self._mock_updates(svc, ["approve apv-20260324-001"])
        # Set after_unix to future — all messages should be ignored
        with patch("requests.get", return_value=mock_resp):
            result = svc._peek_telegram_reply("apv-20260324-001", 9999)
        self.assertIsNone(result)

    def test_40_wrong_chat_ignored(self):
        """Messages from wrong chat are ignored."""
        svc = self._make_service()
        updates = [{
            "message": {
                "date": 1000,
                "text": "approve apv-20260324-001",
                "chat": {"id": 99999}  # wrong chat
            }
        }]
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": updates}
        svc._count_pending_approvals = MagicMock(return_value=1)

        with patch("requests.get", return_value=mock_resp):
            result = svc._peek_telegram_reply("apv-20260324-001", 999)
        self.assertIsNone(result)


class TestCountPendingApprovals(unittest.TestCase):
    """Test _count_pending_approvals."""

    def test_41_count_pending(self):
        """Count pending approval files."""
        with patch.dict(os.environ, {
            "OC_TELEGRAM_BOT_TOKEN": "test-token",
            "OC_TELEGRAM_CHAT_ID": "12345"
        }):
            from services.approval_service import ApprovalService
            svc = ApprovalService(timeout_seconds=5)

        with tempfile.TemporaryDirectory() as td:
            import services.approval_service as mod
            orig_dir = mod.APPROVALS_DIR
            mod.APPROVALS_DIR = td

            # Create 2 pending + 1 approved
            for i, status in enumerate(["pending", "pending", "approved"]):
                path = os.path.join(td, f"apv-test-{i}.json")
                with open(path, "w") as f:
                    json.dump({"status": status}, f)

            count = svc._count_pending_approvals()
            mod.APPROVALS_DIR = orig_dir

        self.assertEqual(count, 2)


if __name__ == "__main__":
    # Run from agent/ directory
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
