"""Tests for B-107 Policy Engine (Sprint 49).

Covers: rule loading, Pydantic validation, evaluation semantics,
priority ordering, fail-closed, all 4 decisions, benchmark.
"""

import os
import shutil
import tempfile

import pytest
import yaml

from mission.policy_engine import (
    PolicyDecision,
    PolicyEngine,
    PolicyRuleModel,
)


@pytest.fixture
def tmp_policies_dir():
    """Create a temporary policies directory."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


def _write_rule(directory: str, filename: str, rule: dict):
    """Helper to write a YAML rule file."""
    with open(os.path.join(directory, filename), "w", encoding="utf-8") as f:
        yaml.safe_dump(rule, f)


# ─── Rule Loading ───

class TestRuleLoading:
    def test_load_from_default_config(self):
        """Load rules from actual config/policies/ directory."""
        engine = PolicyEngine()
        assert len(engine.rules) >= 5
        assert len(engine.load_errors) == 0

    def test_load_empty_directory(self, tmp_policies_dir):
        engine = PolicyEngine(policies_dir=tmp_policies_dir)
        assert len(engine.rules) == 0

    def test_load_nonexistent_directory(self):
        engine = PolicyEngine(policies_dir="/nonexistent/path")
        assert len(engine.rules) == 0

    def test_priority_sort_order(self, tmp_policies_dir):
        _write_rule(tmp_policies_dir, "high.yaml", {
            "name": "high", "priority": 500, "condition": {"always": True},
            "decision": "allow"
        })
        _write_rule(tmp_policies_dir, "low.yaml", {
            "name": "low", "priority": 100, "condition": {"always": True},
            "decision": "deny"
        })
        engine = PolicyEngine(policies_dir=tmp_policies_dir)
        assert engine.rules[0].name == "low"
        assert engine.rules[1].name == "high"

    def test_skip_malformed_yaml(self, tmp_policies_dir):
        # Valid rule
        _write_rule(tmp_policies_dir, "good.yaml", {
            "name": "good", "priority": 100, "condition": {"always": True},
            "decision": "allow"
        })
        # Malformed: missing required fields
        _write_rule(tmp_policies_dir, "bad.yaml", {
            "name": "bad"
        })
        engine = PolicyEngine(policies_dir=tmp_policies_dir)
        assert len(engine.rules) == 1
        assert engine.rules[0].name == "good"
        assert len(engine.load_errors) == 1

    def test_skip_empty_yaml_file(self, tmp_policies_dir):
        with open(os.path.join(tmp_policies_dir, "empty.yaml"), "w") as f:
            f.write("")
        engine = PolicyEngine(policies_dir=tmp_policies_dir)
        assert len(engine.rules) == 0
        assert len(engine.load_errors) == 1

    def test_reload_rules(self, tmp_policies_dir):
        engine = PolicyEngine(policies_dir=tmp_policies_dir)
        assert len(engine.rules) == 0
        _write_rule(tmp_policies_dir, "new.yaml", {
            "name": "new", "priority": 100, "condition": {"always": True},
            "decision": "allow"
        })
        count = engine.load_rules()
        assert count == 1
        assert len(engine.rules) == 1


# ─── Pydantic Validation ───

class TestPydanticValidation:
    def test_valid_rule(self):
        model = PolicyRuleModel(
            name="test", priority=100,
            condition={"always": True}, decision="allow"
        )
        assert model.name == "test"

    def test_negative_priority_rejected(self):
        with pytest.raises(Exception):
            PolicyRuleModel(
                name="bad", priority=-1,
                condition={"always": True}, decision="allow"
            )

    def test_empty_condition_rejected(self):
        with pytest.raises(Exception):
            PolicyRuleModel(
                name="bad", priority=100,
                condition={}, decision="allow"
            )

    def test_invalid_decision_rejected(self):
        with pytest.raises(Exception):
            PolicyRuleModel(
                name="bad", priority=100,
                condition={"always": True}, decision="invalid"
            )

    def test_optional_fields(self):
        model = PolicyRuleModel(
            name="test", priority=100,
            condition={"always": True}, decision="deny",
            fallback={"provider": "ollama"}, description="test rule"
        )
        assert model.fallback == {"provider": "ollama"}
        assert model.description == "test rule"


# ─── Evaluation Semantics ───

class TestEvaluation:
    def _engine_with_rules(self, tmp_policies_dir, rules):
        for i, rule in enumerate(rules):
            _write_rule(tmp_policies_dir, f"rule_{i}.yaml", rule)
        return PolicyEngine(policies_dir=tmp_policies_dir)

    def test_fail_closed_no_rules(self, tmp_policies_dir):
        engine = PolicyEngine(policies_dir=tmp_policies_dir)
        result = engine.evaluate({}, {})
        assert result.decision == PolicyDecision.DENY
        assert "no rules loaded" in result.reason

    def test_fail_closed_no_match(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "specific",
            "priority": 100,
            "condition": {"dependency_state": {"wmcp": "unreachable"}},
            "decision": "degrade"
        }])
        result = engine.evaluate({"dependencyStates": []}, {})
        assert result.decision == PolicyDecision.DENY
        assert "no matching rule" in result.reason

    def test_allow_decision(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "allow-all", "priority": 9999,
            "condition": {"always": True}, "decision": "allow"
        }])
        result = engine.evaluate({}, {})
        assert result.decision == PolicyDecision.ALLOW
        assert result.matched_rule == "allow-all"

    def test_deny_decision(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "deny-all", "priority": 100,
            "condition": {"always": True}, "decision": "deny"
        }])
        result = engine.evaluate({}, {})
        assert result.decision == PolicyDecision.DENY

    def test_escalate_decision(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "escalate-critical", "priority": 100,
            "condition": {"risk_level": "critical", "approval_state": "none"},
            "decision": "escalate"
        }])
        ctx = {"riskLevel": "critical"}
        mission = {"approval_state": "none"}
        result = engine.evaluate(ctx, mission)
        assert result.decision == PolicyDecision.ESCALATE

    def test_degrade_decision(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "degrade-wmcp", "priority": 100,
            "condition": {"dependency_state": {"wmcp": "unreachable"}},
            "decision": "degrade",
            "fallback": {"provider": "ollama"}
        }])
        ctx = {"dependencyStates": [{"name": "wmcp", "status": "unreachable"}]}
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.DEGRADE
        assert result.fallback == {"provider": "ollama"}

    def test_first_match_wins(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [
            {"name": "deny-first", "priority": 100,
             "condition": {"always": True}, "decision": "deny"},
            {"name": "allow-second", "priority": 200,
             "condition": {"always": True}, "decision": "allow"},
        ])
        result = engine.evaluate({}, {})
        assert result.decision == PolicyDecision.DENY
        assert result.matched_rule == "deny-first"

    def test_higher_priority_overrides(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [
            {"name": "allow-low", "priority": 9999,
             "condition": {"always": True}, "decision": "allow"},
            {"name": "deny-high", "priority": 50,
             "condition": {"always": True}, "decision": "deny"},
        ])
        result = engine.evaluate({}, {})
        assert result.decision == PolicyDecision.DENY
        assert result.matched_rule == "deny-high"


# ─── Condition Matching ───

class TestConditionMatching:
    def _engine_with_rules(self, tmp_policies_dir, rules):
        for i, rule in enumerate(rules):
            _write_rule(tmp_policies_dir, f"rule_{i}.yaml", rule)
        return PolicyEngine(policies_dir=tmp_policies_dir)

    def test_dependency_state_match(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "test", "priority": 100,
            "condition": {"dependency_state": {"wmcp": "degraded"}},
            "decision": "degrade"
        }])
        ctx = {"dependencyStates": [{"name": "wmcp", "status": "degraded"}]}
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.DEGRADE

    def test_dependency_state_no_match(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "test", "priority": 100,
            "condition": {"dependency_state": {"wmcp": "unreachable"}},
            "decision": "degrade"
        }])
        ctx = {"dependencyStates": [{"name": "wmcp", "status": "reachable"}]}
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.DENY  # fail-closed

    def test_timeout_exceeded_match(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "timeout", "priority": 100,
            "condition": {"timeout_exceeded": True},
            "decision": "deny"
        }])
        ctx = {
            "timeoutConfig": {"missionSeconds": 3600},
            "sourceFreshness": {"mission_age_seconds": 4000}
        }
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.DENY

    def test_budget_exceeded_match(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "budget", "priority": 100,
            "condition": {"budget_exceeded": True},
            "decision": "deny"
        }])
        ctx = {"tenantLimits": {"max_stages": 3}}
        mission = {"stages": [1, 2, 3]}
        result = engine.evaluate(ctx, mission)
        assert result.decision == PolicyDecision.DENY


# ─── Default Rules Integration ───

class TestDefaultRules:
    def test_default_config_loads_five_rules(self):
        engine = PolicyEngine()
        assert len(engine.rules) == 5

    def test_default_allow_is_last(self):
        engine = PolicyEngine()
        last_rule = engine.rules[-1]
        assert last_rule.name == "default-allow"
        assert last_rule.priority == 9999

    def test_normal_context_allows(self):
        engine = PolicyEngine()
        ctx = {
            "dependencyStates": [{"name": "wmcp", "status": "reachable"}],
            "riskLevel": "medium",
            "sourceFreshness": {"mission_age_seconds": 100},
            "timeoutConfig": {"missionSeconds": 3600},
            "tenantLimits": {"max_stages": 15},
        }
        mission = {"stages": [1, 2], "approval_state": "approved"}
        result = engine.evaluate(ctx, mission)
        assert result.decision == PolicyDecision.ALLOW
        assert result.matched_rule == "default-allow"

    def test_wmcp_unreachable_degrades(self):
        engine = PolicyEngine()
        ctx = {
            "dependencyStates": [{"name": "wmcp", "status": "unreachable"}],
            "riskLevel": "medium",
        }
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.DEGRADE
        assert result.matched_rule == "wmcp-degradation"


# ─── API Serialization ───

class TestSerialization:
    def test_to_dict(self):
        engine = PolicyEngine()
        rules_dict = engine.to_dict()
        assert isinstance(rules_dict, list)
        assert len(rules_dict) == 5
        assert all("name" in r for r in rules_dict)
        assert all("decision" in r for r in rules_dict)

    def test_get_rule(self):
        engine = PolicyEngine()
        rule = engine.get_rule("default-allow")
        assert rule is not None
        assert rule.priority == 9999

    def test_get_rule_not_found(self):
        engine = PolicyEngine()
        assert engine.get_rule("nonexistent") is None


# ─── Benchmark (p99 < 5ms) ───

class TestBenchmark:
    def test_eval_time_under_5ms(self):
        """Sprint 49 perf gate: p99 eval time < 5ms."""
        engine = PolicyEngine()
        ctx = {
            "dependencyStates": [{"name": "wmcp", "status": "reachable"}],
            "riskLevel": "medium",
            "sourceFreshness": {"mission_age_seconds": 100},
            "timeoutConfig": {"missionSeconds": 3600},
            "tenantLimits": {"max_stages": 15},
        }
        mission = {"stages": [1, 2], "approval_state": "approved"}

        times = []
        for _ in range(100):
            result = engine.evaluate(ctx, mission)
            times.append(result.eval_time_ms)

        times.sort()
        p99 = times[98]  # 99th percentile of 100 samples
        assert p99 < 5.0, f"p99 eval time {p99:.2f}ms exceeds 5ms budget"

    def test_eval_returns_timing(self):
        engine = PolicyEngine()
        result = engine.evaluate({}, {})
        assert result.eval_time_ms >= 0


# ─── B-013 Sprint 53: New Condition Types ───

class TestCallerSourceCondition:
    """B-013 Sprint 53: caller_source condition matching."""

    def _engine_with_rules(self, tmp_policies_dir, rules):
        for i, rule in enumerate(rules):
            _write_rule(tmp_policies_dir, f"rule_{i}.yaml", rule)
        return PolicyEngine(policies_dir=tmp_policies_dir)

    def test_caller_source_match(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "telegram-escalate", "priority": 100,
            "condition": {"caller_source": "telegram"},
            "decision": "escalate",
        }])
        ctx = {"caller": {"callerId": "u1", "callerRole": "op", "source": "telegram"}}
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.ESCALATE

    def test_caller_source_no_match(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "telegram-escalate", "priority": 100,
            "condition": {"caller_source": "telegram"},
            "decision": "escalate",
        }])
        ctx = {"caller": {"source": "dashboard"}}
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.DENY  # fail-closed


class TestEnvironmentCondition:
    """B-013 Sprint 53: environment condition matching."""

    def _engine_with_rules(self, tmp_policies_dir, rules):
        for i, rule in enumerate(rules):
            _write_rule(tmp_policies_dir, f"rule_{i}.yaml", rule)
        return PolicyEngine(policies_dir=tmp_policies_dir)

    def test_environment_match(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "dev-allow", "priority": 100,
            "condition": {"environment": "development"},
            "decision": "allow",
        }])
        ctx = {"environment": "development"}
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.ALLOW

    def test_environment_no_match(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "dev-allow", "priority": 100,
            "condition": {"environment": "development"},
            "decision": "allow",
        }])
        ctx = {"environment": "production"}
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.DENY


class TestResourceTagCondition:
    """B-013 Sprint 53: resource_tag condition matching."""

    def _engine_with_rules(self, tmp_policies_dir, rules):
        for i, rule in enumerate(rules):
            _write_rule(tmp_policies_dir, f"rule_{i}.yaml", rule)
        return PolicyEngine(policies_dir=tmp_policies_dir)

    def test_single_tag_match(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "vip-allow", "priority": 100,
            "condition": {"resource_tag": {"priority": "high"}},
            "decision": "allow",
        }])
        ctx = {"resourceTags": {"priority": "high", "team": "platform"}}
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.ALLOW

    def test_multi_tag_match(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "tag-match", "priority": 100,
            "condition": {"resource_tag": {"team": "ops", "env": "prod"}},
            "decision": "allow",
        }])
        ctx = {"resourceTags": {"team": "ops", "env": "prod", "extra": "x"}}
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.ALLOW

    def test_tag_partial_mismatch(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "tag-match", "priority": 100,
            "condition": {"resource_tag": {"team": "ops", "env": "prod"}},
            "decision": "allow",
        }])
        ctx = {"resourceTags": {"team": "ops", "env": "staging"}}
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.DENY

    def test_tag_missing(self, tmp_policies_dir):
        engine = self._engine_with_rules(tmp_policies_dir, [{
            "name": "tag-match", "priority": 100,
            "condition": {"resource_tag": {"team": "ops"}},
            "decision": "allow",
        }])
        ctx = {"resourceTags": {}}
        result = engine.evaluate(ctx, {})
        assert result.decision == PolicyDecision.DENY
