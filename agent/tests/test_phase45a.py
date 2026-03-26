"""Phase 4.5-A tests — telemetry analyzer + E2E runner unit tests."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.analyze_telemetry import (
    analyze_telemetry, analyze_missions, generate_report,
    load_telemetry_events, load_mission_summaries
)


class TestAnalyzeTelemetry(unittest.TestCase):
    """Test telemetry event analysis."""

    def test_01_empty_events(self):
        result = analyze_telemetry([])
        self.assertEqual(result["totalEvents"], 0)

    def test_02_event_type_counts(self):
        events = [
            {"event": "policy_denied", "reason": "read_scope", "role": "developer"},
            {"event": "policy_denied", "reason": "budget_exhausted", "role": "analyst"},
            {"event": "filesystem_tool_allowed", "role": "analyst"},
            {"event": "filesystem_tool_allowed", "role": "developer"},
            {"event": "filesystem_tool_allowed", "role": "tester"},
        ]
        result = analyze_telemetry(events)
        self.assertEqual(result["totalEvents"], 5)
        self.assertEqual(result["totalDenies"], 2)
        self.assertEqual(result["eventTypeCounts"]["policy_denied"], 2)
        self.assertEqual(result["eventTypeCounts"]["filesystem_tool_allowed"], 3)

    def test_03_deny_reasons(self):
        events = [
            {"event": "policy_denied", "reason": "read_scope", "role": "dev"},
            {"event": "policy_denied", "reason": "read_scope", "role": "dev"},
            {"event": "policy_denied", "reason": "budget_exhausted", "role": "analyst"},
        ]
        result = analyze_telemetry(events)
        self.assertEqual(result["topDenyReasons"][0]["reason"], "read_scope")
        self.assertEqual(result["topDenyReasons"][0]["count"], 2)

    def test_04_deny_by_role(self):
        events = [
            {"event": "policy_denied", "reason": "x", "role": "developer"},
            {"event": "policy_denied", "reason": "y", "role": "developer"},
            {"event": "policy_denied", "reason": "z", "role": "tester"},
        ]
        result = analyze_telemetry(events)
        self.assertEqual(result["denyByRole"]["developer"], 2)
        self.assertEqual(result["denyByRole"]["tester"], 1)


class TestAnalyzeMissions(unittest.TestCase):
    """Test mission summary analysis."""

    def _make_summary(self, status="completed", stages=None,
                      duration_ms=10000, complexity="trivial",
                      gates=None):
        return {
            "missionId": f"mission-test-{id(status)}",
            "status": status,
            "totalDurationMs": duration_ms,
            "complexity": complexity,
            "stages": stages or [
                {"specialist": "analyst", "status": "completed",
                 "agent": "claude-general", "role": "analyst",
                 "artifactType": "discovery_map"},
                {"specialist": "developer", "status": "completed",
                 "agent": "claude-general", "role": "developer",
                 "artifactType": "code_delivery"},
                {"specialist": "tester", "status": "completed",
                 "agent": "claude-general", "role": "tester",
                 "artifactType": "test_report"},
            ],
            "gatesChecked": gates or {"gate_1": False, "gate_2": True, "gate_3": True},
            "consumptionByTier": {"A": 2, "B": 3, "D": 5},
            "totalPolicyDenies": 0,
            "totalRereads": 1,
            "artifactCount": 3,
        }

    def test_05_empty_summaries(self):
        result = analyze_missions([])
        self.assertEqual(result["missionCount"], 0)

    def test_06_basic_stats(self):
        summaries = [self._make_summary()]
        result = analyze_missions(summaries)
        self.assertEqual(result["missionCount"], 1)
        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["avgDurationMs"], 10000)
        self.assertEqual(result["avgStageCount"], 3.0)

    def test_07_model_usage(self):
        summaries = [self._make_summary()]
        result = analyze_missions(summaries)
        self.assertIn("claude-general", result["modelUsage"])
        self.assertEqual(result["modelUsage"]["claude-general"]["count"], 3)

    def test_08_gate_pass_rates(self):
        summaries = [
            self._make_summary(gates={"gate_1": True, "gate_2": True, "gate_3": False}),
        ]
        result = analyze_missions(summaries)
        self.assertEqual(result["gatePassRates"]["gate_1"], "100%")
        self.assertEqual(result["gatePassRates"]["gate_2"], "100%")

    def test_09_context_tier_distribution(self):
        summaries = [self._make_summary()]
        result = analyze_missions(summaries)
        self.assertEqual(result["contextTierDistribution"]["A"], 2)
        self.assertEqual(result["contextTierDistribution"]["B"], 3)
        self.assertEqual(result["contextTierDistribution"]["D"], 5)

    def test_10_reworks(self):
        stages = [
            {"specialist": "developer", "status": "completed",
             "agent": "claude-general", "role": "developer",
             "reworkCycle": 2, "artifactType": "code_delivery"},
        ]
        summaries = [self._make_summary(stages=stages)]
        result = analyze_missions(summaries)
        self.assertEqual(result["totalReworks"], 2)

    def test_11_failed_missions(self):
        summaries = [
            self._make_summary(status="completed"),
            self._make_summary(status="failed"),
        ]
        result = analyze_missions(summaries)
        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["failed"], 1)

    def test_12_cost_estimate(self):
        summaries = [self._make_summary(complexity="trivial")]
        result = analyze_missions(summaries)
        self.assertIn("trivial", result["costEstimate"])


class TestReportGeneration(unittest.TestCase):
    """Test report output formats."""

    def test_13_text_report(self):
        telemetry = {"totalEvents": 5, "totalDenies": 1,
                     "topDenyReasons": [{"reason": "x", "count": 1}],
                     "denyByRole": {"dev": 1}}
        missions = {"missionCount": 2, "completed": 2, "failed": 0,
                    "avgDurationMs": 5000, "avgStageCount": 3,
                    "totalReworks": 0, "totalPolicyDenies": 0,
                    "totalRereads": 1, "gatePassRates": {"gate_1": "100%"},
                    "modelUsage": {}, "contextTierDistribution": {},
                    "artifactExtractionRate": {}, "costEstimate": {}}
        report = generate_report(telemetry, missions, as_json=False)
        self.assertIn("Vezir Telemetry Report", report)
        self.assertIn("Missions: 2", report)

    def test_14_json_report(self):
        telemetry = {"totalEvents": 0}
        missions = {"missionCount": 0}
        report = generate_report(telemetry, missions, as_json=True)
        data = json.loads(report)
        self.assertIn("telemetry", data)
        self.assertIn("missions", data)


class TestFileLoading(unittest.TestCase):
    """Test file loading with temp files."""

    def test_15_load_telemetry(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl',
                                         delete=False, encoding='utf-8') as f:
            f.write('{"event": "test", "timestamp": "2026-03-24T00:00:00"}\n')
            f.write('{"event": "test2", "timestamp": "2026-03-24T00:01:00"}\n')
            path = f.name

        try:
            import tools.analyze_telemetry as mod
            orig = mod.TELEMETRY_PATH
            mod.TELEMETRY_PATH = path
            events = load_telemetry_events()
            mod.TELEMETRY_PATH = orig
            self.assertEqual(len(events), 2)
        finally:
            os.unlink(path)

    def test_16_load_mission_summaries(self):
        with tempfile.TemporaryDirectory() as td:
            summary = {"missionId": "test", "status": "completed"}
            path = os.path.join(td, "mission-test-summary.json")
            with open(path, "w") as f:
                json.dump(summary, f)

            import tools.analyze_telemetry as mod
            orig = mod.MISSIONS_DIR
            mod.MISSIONS_DIR = td
            summaries = load_mission_summaries()
            mod.MISSIONS_DIR = orig
            self.assertEqual(len(summaries), 1)
            self.assertEqual(summaries[0]["missionId"], "test")


class TestRunE2EImports(unittest.TestCase):
    """Test that E2E runner imports work."""

    def test_17_test_cases_defined(self):
        from tools.run_e2e_test import TEST_CASES
        self.assertIn("trivial", TEST_CASES)
        self.assertIn("simple", TEST_CASES)
        self.assertIn("medium", TEST_CASES)
        self.assertIn("complex", TEST_CASES)

    def test_18_test_case_structure(self):
        from tools.run_e2e_test import TEST_CASES
        for complexity, tc in TEST_CASES.items():
            self.assertIn("id", tc)
            self.assertIn("message", tc)
            self.assertIn("expected_roles", tc)
            self.assertIn("budget", tc)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
