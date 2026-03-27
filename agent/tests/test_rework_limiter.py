"""Tests for D-103 complexity-based rework limiter."""
from mission.feedback_loops import REWORK_LIMITS, FeedbackLoop


class TestComplexityBasedLimits:
    """D-103: Rework limits scale with mission complexity."""

    def test_trivial_limits(self):
        fl = FeedbackLoop("m1", complexity="trivial")
        assert fl.max_dev_test_cycles == 1
        assert fl.max_dev_review_cycles == 1

    def test_simple_limits(self):
        fl = FeedbackLoop("m1", complexity="simple")
        assert fl.max_dev_test_cycles == 2
        assert fl.max_dev_review_cycles == 1

    def test_medium_limits(self):
        fl = FeedbackLoop("m1", complexity="medium")
        assert fl.max_dev_test_cycles == 3
        assert fl.max_dev_review_cycles == 2

    def test_complex_limits(self):
        fl = FeedbackLoop("m1", complexity="complex")
        assert fl.max_dev_test_cycles == 4
        assert fl.max_dev_review_cycles == 3

    def test_default_is_medium(self):
        """No complexity arg defaults to medium."""
        fl = FeedbackLoop("m1")
        assert fl.max_dev_test_cycles == 3
        assert fl.max_dev_review_cycles == 2

    def test_unknown_complexity_uses_default(self):
        fl = FeedbackLoop("m1", complexity="unknown_tier")
        assert fl.max_dev_test_cycles == 3
        assert fl.max_dev_review_cycles == 2


class TestSimpleMissionEscalatesEarly:
    """Simple missions should escalate after fewer rework cycles."""

    def test_simple_escalates_after_2_dev_test(self):
        fl = FeedbackLoop("m1", complexity="simple")
        # Cycle 1: rework
        r1 = fl.evaluate_test_result({"verdict": "fail", "bugs": ["b1"]})
        assert r1["action"] == "rework"
        # Cycle 2: rework
        r2 = fl.evaluate_test_result({"verdict": "fail", "bugs": ["b2"]})
        assert r2["action"] == "rework"
        # Cycle 3: should escalate (limit is 2)
        r3 = fl.evaluate_test_result({"verdict": "fail", "bugs": ["b3"]})
        assert r3["action"] == "escalate"

    def test_trivial_escalates_after_1_dev_test(self):
        fl = FeedbackLoop("m1", complexity="trivial")
        r1 = fl.evaluate_test_result({"verdict": "fail", "bugs": ["b1"]})
        assert r1["action"] == "rework"
        r2 = fl.evaluate_test_result({"verdict": "fail", "bugs": ["b2"]})
        assert r2["action"] == "escalate"

    def test_complex_allows_4_dev_test_cycles(self):
        fl = FeedbackLoop("m1", complexity="complex")
        for i in range(4):
            r = fl.evaluate_test_result({"verdict": "fail", "bugs": [f"b{i}"]})
            assert r["action"] == "rework", f"Cycle {i+1} should be rework"
        r5 = fl.evaluate_test_result({"verdict": "fail", "bugs": ["b5"]})
        assert r5["action"] == "escalate"

    def test_simple_review_escalates_after_1(self):
        fl = FeedbackLoop("m1", complexity="simple")
        r1 = fl.evaluate_review_result({"decision": "request_changes",
                                         "findings": [{"severity": "major"}]})
        assert r1["action"] == "rework"
        r2 = fl.evaluate_review_result({"decision": "request_changes",
                                         "findings": [{"severity": "major"}]})
        assert r2["action"] == "escalate"


class TestReworkLimitsConfig:
    """REWORK_LIMITS dict has all 4 tiers."""

    def test_all_tiers_present(self):
        assert set(REWORK_LIMITS.keys()) == {"trivial", "simple", "medium", "complex"}

    def test_limits_are_monotonically_increasing(self):
        order = ["trivial", "simple", "medium", "complex"]
        for i in range(len(order) - 1):
            a = REWORK_LIMITS[order[i]]
            b = REWORK_LIMITS[order[i + 1]]
            assert a["dev_test"] <= b["dev_test"]
            assert a["dev_review"] <= b["dev_review"]
