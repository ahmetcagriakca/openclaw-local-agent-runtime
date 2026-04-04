"""Intent mapper — explicit intent-to-mission-type mapping layer.

Sprint 56 Task 56.3 (B-019): Refine intent detection with configurable
keyword-based mapping. Sits on top of complexity_router, provides
higher-level intent classification before complexity routing.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger("mcc.mission.intent_mapper")

# Default intent rules — keyword patterns → mission intent
# Each intent maps to a complexity override and metadata
DEFAULT_INTENT_RULES: list[dict] = [
    {
        "intent": "status_check",
        "description": "System or mission status inquiry",
        "patterns": [
            r"(?:sistem|system)\s*(?:durumu?|status|health)",
            r"(?:sa[gğ]l[iı]k|health)\s*(?:kontrol|check)",
            r"ne\s+durumda",
            r"(?:mission|g[oö]rev)\s*(?:durumu?|status)",
            r"ka[cç]\s+(?:g[oö]rev|mission|test)",
        ],
        "complexity_override": "trivial",
        "tags": ["readonly", "fast"],
    },
    {
        "intent": "code_change",
        "description": "Direct code modification request",
        "patterns": [
            r"(?:de[gğ]i[sş]tir|change|modify|update)\s+.+\s+(?:kod|code|dosya|file)",
            r"(?:ekle|add)\s+.+\s+(?:fonksiyon|function|metod|method|endpoint)",
            r"(?:yeni|new)\s+(?:fonksiyon|function|metod|method|endpoint)\s+(?:ekle|add)",
            r"(?:kald[iı]r|remove|sil|delete)\s+.+\s+(?:kod|code|fonksiyon|function)",
            r"refactor\s+",
            r"(?:yeniden\s*yaz|rewrite)\s+",
        ],
        "complexity_override": None,  # defer to complexity router
        "tags": ["mutation", "code"],
    },
    {
        "intent": "test_run",
        "description": "Test execution or validation request",
        "patterns": [
            r"(?:test|testler)\w*\s*(?:[cç]al[iı][sş]t[iı]r|run|ko[sş])",
            r"pytest\s+",
            r"vitest\s+",
            r"(?:do[gğ]rula|validate|verify)\s+",
        ],
        "complexity_override": "simple",
        "tags": ["readonly", "validation"],
    },
    {
        "intent": "deployment",
        "description": "Deployment or release operation",
        "patterns": [
            r"(?:deploy|da[gğ][iı]t|yay[iı]nla|release|publish)",
            r"(?:prod|production|canl[iı])\s*(?:ortam|env)",
            r"docker\s+(?:build|push|deploy)",
        ],
        "complexity_override": "complex",
        "tags": ["mutation", "infra"],
    },
    {
        "intent": "security_audit",
        "description": "Security check or audit request",
        "patterns": [
            r"(?:g[uü]venlik|security)\s*(?:kontrol|check|audit|tara|scan)",
            r"(?:zafiyet|vulnerability|vuln)\s*(?:tara|scan|kontrol)",
            r"(?:secret|gizli|credential)\s*(?:tara|scan|kontrol|check)",
        ],
        "complexity_override": "medium",
        "tags": ["readonly", "security"],
    },
    {
        "intent": "documentation",
        "description": "Documentation generation or update",
        "patterns": [
            r"(?:dok[uü]man|doc|documentation)\s*(?:olu[sş]tur|generate|yaz|write|update)",
            r"readme\s*(?:g[uü]ncelle|update|yaz|write)",
            r"api\s*(?:dok[uü]man\w*|doc\w*)\s*(?:olu[sş]tur|generate)",
        ],
        "complexity_override": "simple",
        "tags": ["mutation", "docs"],
    },
    {
        "intent": "analysis",
        "description": "Code or data analysis request",
        "patterns": [
            r"(?:analiz|analyze|incel[ey]|examine|review)\s+",
            r"(?:performans|performance)\s*(?:analiz|analysis|[oö]l[cç]|measure)",
            r"(?:ka[cç]|how\s+many|count)\s+",
            r"(?:kar[sş][iı]la[sş]t[iı]r|compare)\s+",
        ],
        "complexity_override": "simple",
        "tags": ["readonly", "analysis"],
    },
    {
        "intent": "infrastructure",
        "description": "Infrastructure or configuration change",
        "patterns": [
            r"(?:config|yap[iı]land[iı]r|configure)\s+",
            r"(?:ci|cd|pipeline)\s*(?:ekle|add|de[gğ]i[sş]tir|change)",
            r"(?:docker|container|kubernetes|k8s)\s+",
            r"(?:environment|ortam)\s*(?:kur|setup|de[gğ]i[sş]tir)",
        ],
        "complexity_override": "medium",
        "tags": ["mutation", "infra"],
    },
]


class IntentMapper:
    """Maps user goals to mission intents with configurable rules.

    The intent mapper provides a higher-level classification layer
    that runs before the complexity router. When an intent is matched
    and has a complexity_override, it takes precedence over Tier 0
    deterministic patterns.
    """

    def __init__(self, rules: list[dict] | None = None):
        self.rules = rules if rules is not None else DEFAULT_INTENT_RULES
        self._compiled: list[tuple[dict, list[re.Pattern]]] = []
        self._compile_rules()

    def _compile_rules(self):
        """Pre-compile regex patterns for performance."""
        self._compiled = []
        for rule in self.rules:
            patterns = [re.compile(p, re.IGNORECASE) for p in rule.get("patterns", [])]
            self._compiled.append((rule, patterns))

    def classify(self, message: str) -> dict | None:
        """Classify a user message into an intent.

        Returns intent dict with keys: intent, description, complexity_override, tags, confidence.
        Returns None if no intent matched.
        """
        message_lower = message.lower().strip()
        if not message_lower:
            return None

        best_match = None
        best_score = 0

        for rule, patterns in self._compiled:
            match_count = 0
            for pattern in patterns:
                if pattern.search(message_lower):
                    match_count += 1

            if match_count > 0:
                # Score: matched patterns / total patterns for this rule
                score = match_count / len(patterns) if patterns else 0
                if score > best_score:
                    best_score = score
                    best_match = rule

        if best_match is None:
            return None

        return {
            "intent": best_match["intent"],
            "description": best_match["description"],
            "complexity_override": best_match.get("complexity_override"),
            "tags": best_match.get("tags", []),
            "confidence": round(best_score, 3),
        }

    def classify_with_fallback(self, message: str, provider=None) -> dict:
        """Classify intent, falling back to complexity router.

        Returns full classification including intent (if matched) and
        complexity (always present).
        """
        from mission.complexity_router import classify_complexity

        intent_result = self.classify(message)
        complexity_result = classify_complexity(message, provider)

        if intent_result and intent_result["complexity_override"]:
            # Intent override takes precedence
            from mission.complexity_router import STAGE_TEMPLATES
            override = intent_result["complexity_override"]
            complexity_result = {
                "complexity": override,
                "tier_used": 0,
                "stage_template": STAGE_TEMPLATES[override],
                "role_count": len(STAGE_TEMPLATES[override]),
            }

        return {
            "intent": intent_result,
            "complexity": complexity_result,
            "source": "intent_override" if (intent_result and intent_result["complexity_override"]) else "complexity_router",
        }

    def list_intents(self) -> list[dict]:
        """Return all configured intents with metadata."""
        return [
            {
                "intent": r["intent"],
                "description": r["description"],
                "complexity_override": r.get("complexity_override"),
                "tags": r.get("tags", []),
                "pattern_count": len(r.get("patterns", [])),
            }
            for r in self.rules
        ]


# Module-level singleton
_default_mapper: IntentMapper | None = None


def get_mapper() -> IntentMapper:
    """Get or create the default intent mapper singleton."""
    global _default_mapper
    if _default_mapper is None:
        _default_mapper = IntentMapper()
    return _default_mapper


def classify_intent(message: str) -> dict | None:
    """Convenience function — classify a message using default mapper."""
    return get_mapper().classify(message)


def classify_with_fallback(message: str, provider=None) -> dict:
    """Convenience — classify with intent + complexity fallback."""
    return get_mapper().classify_with_fallback(message, provider)
