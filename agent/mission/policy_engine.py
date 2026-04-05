"""Policy Engine — rule-based, config-driven, fail-closed evaluation layer.

B-107: Implements D-133 contract. Evaluates policy rules pre-stage in
the mission controller. Rules loaded from config/policies/*.yaml.

Evaluation semantics (Sprint 49 v2 contract):
- Rules sorted by priority ascending (lower = higher priority)
- First matching rule wins
- Default on no match: deny (fail-closed)
- Rule load failure: skip bad rule + log error
- ALL rules fail to load: deny (true fail-closed)
- Malformed rules rejected via Pydantic validation
- Storage: YAML read-only (S49), write API deferred to S50
"""

import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml


def _safe_rule_name(name: str) -> str:
    """Validate rule name is safe for use as a filename (no path traversal)."""
    if not name or not re.match(r'^[a-zA-Z0-9_\-]+$', name):
        raise ValueError(f"Invalid rule name: must be alphanumeric/underscore/hyphen, got '{name}'")
    return name
from pydantic import BaseModel, ValidationError, field_validator

logger = logging.getLogger(__name__)

# Default policies directory
POLICIES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config", "policies"
)


class PolicyDecision(str, Enum):
    """D-133: Four possible evaluation outcomes."""
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"
    DEGRADE = "degrade"


class PolicyRuleModel(BaseModel):
    """Pydantic model for YAML rule validation."""
    name: str
    priority: int
    condition: dict
    decision: PolicyDecision
    fallback: Optional[dict] = None
    description: Optional[str] = None

    @field_validator("priority")
    @classmethod
    def priority_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("priority must be non-negative")
        return v

    @field_validator("condition")
    @classmethod
    def condition_must_not_be_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("condition must not be empty")
        return v


@dataclass
class PolicyRule:
    """Runtime representation of a validated policy rule."""
    name: str
    priority: int
    condition: dict
    decision: PolicyDecision
    fallback: Optional[dict] = None
    description: str = ""

    @classmethod
    def from_validated(cls, model: PolicyRuleModel) -> "PolicyRule":
        return cls(
            name=model.name,
            priority=model.priority,
            condition=model.condition,
            decision=model.decision,
            fallback=model.fallback,
            description=model.description or "",
        )


@dataclass
class EvaluationResult:
    """Result of policy evaluation."""
    decision: PolicyDecision
    matched_rule: Optional[str] = None
    fallback: Optional[dict] = None
    reason: str = ""
    eval_time_ms: float = 0.0


class PolicyEngine:
    """Rule-based policy evaluation engine.

    Loads YAML rules from config/policies/, validates with Pydantic,
    sorts by priority, and evaluates first-match against policy context.
    """

    def __init__(self, policies_dir: str = POLICIES_DIR):
        self._policies_dir = policies_dir
        self._rules: list[PolicyRule] = []
        self._load_errors: list[str] = []
        self._write_lock = threading.Lock()
        self.load_rules()

    def load_rules(self) -> int:
        """Load and validate all YAML rules from policies directory.

        Returns number of successfully loaded rules.
        """
        self._rules = []
        self._load_errors = []
        policies_path = Path(self._policies_dir)

        if not policies_path.exists():
            logger.warning("Policies directory not found: %s", self._policies_dir)
            return 0

        yaml_files = sorted(policies_path.glob("*.yaml"))
        if not yaml_files:
            logger.warning("No YAML rule files found in %s", self._policies_dir)
            return 0

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    raw = yaml.safe_load(f)

                if raw is None:
                    self._load_errors.append(f"{yaml_file.name}: empty file")
                    logger.error("Policy rule file is empty: %s", yaml_file.name)
                    continue

                model = PolicyRuleModel(**raw)
                rule = PolicyRule.from_validated(model)
                self._rules.append(rule)
                logger.info("Loaded policy rule: %s (priority=%d)",
                            rule.name, rule.priority)
            except (yaml.YAMLError, ValidationError, TypeError) as e:
                error_msg = f"{yaml_file.name}: {e}"
                self._load_errors.append(error_msg)
                logger.error("Failed to load policy rule %s: %s",
                             yaml_file.name, e)

        # Sort by priority ascending (lower = higher priority)
        self._rules.sort(key=lambda r: r.priority)
        logger.info("Policy engine loaded %d rules (%d errors)",
                     len(self._rules), len(self._load_errors))
        return len(self._rules)

    @property
    def rules(self) -> list[PolicyRule]:
        """Return loaded rules (sorted by priority)."""
        return list(self._rules)

    @property
    def load_errors(self) -> list[str]:
        """Return list of rule loading errors."""
        return list(self._load_errors)

    def evaluate(
        self,
        policy_context: dict,
        mission_config: dict,
        tool_request: Optional[dict] = None,
    ) -> EvaluationResult:
        """Evaluate policy rules against current context.

        Args:
            policy_context: PolicyContext.to_dict() output
            mission_config: dict with goal, complexity, stages
            tool_request: optional dict with tool, target, parameters

        Returns:
            EvaluationResult with decision + matched rule info
        """
        start = time.perf_counter()

        # Fail-closed: if no rules loaded at all, deny
        if not self._rules:
            elapsed = (time.perf_counter() - start) * 1000
            logger.warning("Policy engine has no rules loaded — denying (fail-closed)")
            return EvaluationResult(
                decision=PolicyDecision.DENY,
                reason="no rules loaded (fail-closed)",
                eval_time_ms=elapsed,
            )

        # Evaluate rules in priority order (first match wins)
        for rule in self._rules:
            if self._matches(rule.condition, policy_context, mission_config,
                             tool_request):
                elapsed = (time.perf_counter() - start) * 1000
                return EvaluationResult(
                    decision=rule.decision,
                    matched_rule=rule.name,
                    fallback=rule.fallback,
                    reason=f"matched rule '{rule.name}' (priority={rule.priority})",
                    eval_time_ms=elapsed,
                )

        # No rule matched — fail-closed: deny
        elapsed = (time.perf_counter() - start) * 1000
        return EvaluationResult(
            decision=PolicyDecision.DENY,
            reason="no matching rule (fail-closed default deny)",
            eval_time_ms=elapsed,
        )

    def _matches(
        self,
        condition: dict,
        policy_context: dict,
        mission_config: dict,
        tool_request: Optional[dict],
    ) -> bool:
        """Check if a rule condition matches the current context.

        Supports simple condition types:
        - dependency_state: {name: status} — check dependency availability
        - risk_level: str — check mission risk level
        - timeout_exceeded: bool — check if stage timeout exceeded
        - budget_exceeded: bool — check if budget exceeded
        - always: true — unconditional match (for default rules)
        """
        # always: true — unconditional match
        if condition.get("always") is True:
            return True

        # dependency_state check
        dep_state = condition.get("dependency_state")
        if dep_state and isinstance(dep_state, dict):
            dep_states = policy_context.get("dependencyStates", [])
            for dep_name, expected_status in dep_state.items():
                for dep in dep_states:
                    if dep.get("name") == dep_name and dep.get("status") == expected_status:
                        return True
            return False

        # B-144 Sprint 66: side_effect_scope + risk_level compound check
        scope_cond = condition.get("side_effect_scope")
        if scope_cond:
            tool_scope = (tool_request or {}).get("side_effect_scope", "")
            ctx_risk = policy_context.get("riskLevel", "medium")
            cond_risk = condition.get("risk_level")
            scope_match = tool_scope == scope_cond
            risk_match = ctx_risk == cond_risk if cond_risk else True
            return scope_match and risk_match

        # risk_level check
        risk_level = condition.get("risk_level")
        if risk_level:
            ctx_risk = policy_context.get("riskLevel", "medium")
            approval_state = condition.get("approval_state", "none")
            if ctx_risk == risk_level:
                # If approval_state is specified, check mission config
                if approval_state == "none":
                    return True
                # Check if mission has approval
                mission_approval = mission_config.get("approval_state", "none")
                return mission_approval == approval_state
            return False

        # timeout_exceeded check
        if condition.get("timeout_exceeded") is True:
            timeout_cfg = policy_context.get("timeoutConfig", {})
            freshness = policy_context.get("sourceFreshness", {})
            mission_age = freshness.get("mission_age_seconds", 0)
            mission_timeout = timeout_cfg.get("missionSeconds", 3600)
            return mission_age >= mission_timeout

        # budget_exceeded check (legacy stage-count based)
        if condition.get("budget_exceeded") is True:
            tenant_limits = policy_context.get("tenantLimits", {})
            stages = mission_config.get("stages", [])
            max_stages = tenant_limits.get("max_stages", 15)
            return len(stages) >= max_stages

        # B-140: token_budget_exceeded — hard per-mission token budget
        if condition.get("token_budget_exceeded") is True:
            total_tokens = policy_context.get("totalTokens", 0)
            max_budget = policy_context.get("maxTokenBudget", 0)
            if max_budget <= 0:
                return False  # No budget set = no enforcement
            return total_tokens >= max_budget

        # B-140: token_budget_warning — 80% threshold alert
        if condition.get("token_budget_warning") is True:
            total_tokens = policy_context.get("totalTokens", 0)
            max_budget = policy_context.get("maxTokenBudget", 0)
            if max_budget <= 0:
                return False
            return total_tokens >= max_budget * 0.8

        # B-013 Sprint 53: caller_source check
        caller_source = condition.get("caller_source")
        if caller_source:
            caller = policy_context.get("caller", {})
            return caller.get("source") == caller_source

        # B-013 Sprint 53: environment check
        env_cond = condition.get("environment")
        if env_cond:
            return policy_context.get("environment") == env_cond

        # B-013 Sprint 53: resource_tag check
        tag_cond = condition.get("resource_tag")
        if tag_cond and isinstance(tag_cond, dict):
            tags = policy_context.get("resourceTags", {})
            for key, expected in tag_cond.items():
                if tags.get(key) != expected:
                    return False
            return True

        return False

    def get_rule(self, name: str) -> Optional[PolicyRule]:
        """Get a rule by name."""
        for rule in self._rules:
            if rule.name == name:
                return rule
        return None

    def to_dict(self) -> list[dict]:
        """Serialize all rules to dict list (for API)."""
        return [
            {
                "name": r.name,
                "priority": r.priority,
                "condition": r.condition,
                "decision": r.decision.value,
                "fallback": r.fallback,
                "description": r.description,
            }
            for r in self._rules
        ]

    # ── Write API (Sprint 50) ────────────────────────────────────

    def create_rule(self, data: dict) -> PolicyRule:
        """Create a new policy rule. Validates, writes YAML, reloads.

        Raises ValueError on validation failure or name conflict.
        """
        model = PolicyRuleModel(**data)
        _safe_rule_name(model.name)
        with self._write_lock:
            if self.get_rule(model.name):
                raise ValueError(f"Rule '{model.name}' already exists")
            self._write_yaml(model.name, data)
            logger.info("Policy rule created: %s", model.name)
            self.load_rules()
        return self.get_rule(model.name)  # type: ignore[return-value]

    def update_rule(self, name: str, data: dict) -> PolicyRule:
        """Update an existing policy rule. Validates, writes YAML, reloads.

        Raises ValueError on validation failure, KeyError if not found.
        """
        name = _safe_rule_name(name)
        with self._write_lock:
            if not self.get_rule(name):
                raise KeyError(f"Rule '{name}' not found")
            merged = {"name": name, **data}
            PolicyRuleModel(**merged)
            self._write_yaml(name, merged)
            logger.info("Policy rule updated: %s", name)
            self.load_rules()
        return self.get_rule(name)  # type: ignore[return-value]

    def delete_rule(self, name: str) -> bool:
        """Delete a policy rule. Removes YAML file, reloads.

        Raises KeyError if not found.
        """
        name = _safe_rule_name(name)
        with self._write_lock:
            if not self.get_rule(name):
                raise KeyError(f"Rule '{name}' not found")
            base = Path(self._policies_dir).resolve()
            yaml_path = (base / f"{name}.yaml").resolve()
            if not str(yaml_path).startswith(str(base) + os.sep):
                raise ValueError(f"Path traversal blocked: {name}")
            if yaml_path.exists():
                yaml_path.unlink()
            logger.info("Policy rule deleted: %s", name)
            self.load_rules()
        return True

    def _write_yaml(self, name: str, data: dict) -> None:
        """Atomic write of rule YAML file (D-071 pattern)."""
        policies_path = Path(self._policies_dir).resolve()
        policies_path.mkdir(parents=True, exist_ok=True)
        target = (policies_path / f"{name}.yaml").resolve()
        if not str(target).startswith(str(policies_path) + os.sep):
            raise ValueError(f"Path traversal blocked: {name}")
        tmp = target.with_suffix(".yaml.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(target)
        except Exception:
            if tmp.exists():
                tmp.unlink()
            raise
