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
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
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

        # budget_exceeded check
        if condition.get("budget_exceeded") is True:
            tenant_limits = policy_context.get("tenantLimits", {})
            stages = mission_config.get("stages", [])
            max_stages = tenant_limits.get("max_stages", 15)
            return len(stages) >= max_stages

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
