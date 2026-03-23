"""Complexity router — Tier 0 deterministic + Tier 2 LLM classification."""
import re

# Stage templates — which roles participate at each complexity level
STAGE_TEMPLATES = {
    "trivial": [
        {"specialist": "analyst", "skill": "repository_discovery"},
        {"specialist": "developer", "skill": "targeted_code_change"},
        {"specialist": "tester", "skill": "test_validation"}
    ],
    "simple": [
        {"specialist": "analyst", "skill": "repository_discovery"},
        {"specialist": "developer", "skill": "targeted_code_change"},
        {"specialist": "tester", "skill": "test_validation"},
        {"specialist": "reviewer", "skill": "quality_review"}
    ],
    "medium": [
        {"specialist": "product-owner", "skill": "requirement_structuring"},
        {"specialist": "analyst", "skill": "repository_discovery"},
        {"specialist": "architect", "skill": "architecture_synthesis"},
        {"specialist": "developer", "skill": "targeted_code_change"},
        {"specialist": "tester", "skill": "test_validation"},
        {"specialist": "reviewer", "skill": "quality_review"},
        {"specialist": "manager", "skill": "summary_compression"}
    ],
    "complex": [
        {"specialist": "product-owner", "skill": "requirement_structuring"},
        {"specialist": "analyst", "skill": "repository_discovery"},
        {"specialist": "architect", "skill": "architecture_synthesis"},
        {"specialist": "project-manager", "skill": "work_breakdown"},
        {"specialist": "developer", "skill": "targeted_code_change"},
        {"specialist": "tester", "skill": "test_validation"},
        {"specialist": "reviewer", "skill": "quality_review"},
        {"specialist": "manager", "skill": "summary_compression"}
    ]
}

# Tier 0: Deterministic classification rules
# These patterns are checked BEFORE any LLM call
TRIVIAL_PATTERNS = [
    # Single-file edits (Turkish chars: i/ı, u/ü, o/ö, g/ğ, s/ş, c/ç all handled)
    r"(?:ekle|add)\s+.+\s+(?:sat[iı]r|line|entry)",
    r"sat[iı]r\w*\s+ekle",
    r"dosya\w*\s+.+\s+ekle",
    r"(?:g[uü]ncelle|update)\s+.+(?:version|versiyon)",
    r"(?:d[uü]zelt|fix)\s+(?:typo|yaz[iı]m|imla)",
    r"(?:de[gğ]i[sş]tir|change|replace)\s+.+\s+(?:ile|with|to)\s+",
    # Status queries
    r"(?:durumu?|status|health|sa[gğ]l[iı][kğ])",
    r"(?:kontrol\s+et|check)",
    r"(?:oku|read|g[oö]ster|show)\s+.+(?:dosya|file|i[cç]eri[kğ]|content)",
    # Simple additions
    r"docstring\s+ekle",
    r"yorum\s+ekle",
    r"comment\s+(?:ekle|add)",
]

SIMPLE_PATTERNS = [
    # Small feature additions
    r"(?:yeni|new)\s+(?:fonksiyon|function|metod|method)",
    r"(?:ekle|add)\s+(?:kontrol|check|validation|do[gğ]rulama)",
    r"(?:log|loglama|logging)\s+(?:ekle|add)",
    r"(?:hata|error)\s+(?:mesaj|message)",
    r"(?:g[uü]ncelle|update)\s+(?:mesaj|message|hata|error)",
]

COMPLEX_PATTERNS = [
    # Multi-component changes
    r"(?:yeni|new)\s+(?:mod[uü]l|module|bile[sş]en|component|servis|service)",
    r"(?:yeni|new)\s+.+\s+(?:mod[uü]l|module|tool|servis|service)",
    r"(?:mimari|architecture|refactor|yeniden\s*yaz)",
    r"(?:entegrasyon|integration|birle[sş]tir|merge)",
    r"(?:g[uü]venlik|security)\s+(?:katman[iı]|layer|hardening|sertle[sş]tir)",
    r"(?:migration|g[oö][cç]|ta[sş][iı])",
]


def classify_complexity_deterministic(message: str) -> str | None:
    """Tier 0: Deterministic classification. Returns complexity or None.

    Cost: $0.000, Latency: <1ms
    """
    message_lower = message.lower().strip()

    for pattern in TRIVIAL_PATTERNS:
        if re.search(pattern, message_lower):
            return "trivial"

    # Complex before simple — complex takes priority
    for pattern in COMPLEX_PATTERNS:
        if re.search(pattern, message_lower):
            return "complex"

    for pattern in SIMPLE_PATTERNS:
        if re.search(pattern, message_lower):
            return "simple"

    return None


def classify_complexity_llm(message: str, provider) -> str:
    """Tier 2: LLM-based classification when Tier 0 fails."""
    prompt = (
        "Classify the following task into exactly one complexity level. "
        "Respond with ONLY the word.\n\n"
        "LEVELS:\n"
        "- trivial: Single file edit, typo fix, version bump, content read\n"
        "- simple: Small feature (1-2 files), add validation, add logging\n"
        "- medium: Multi-file feature, new component, API change\n"
        "- complex: New module/service, architecture change, security hardening\n\n"
        f"TASK: {message}\n\nCOMPLEXITY:"
    )
    try:
        response = provider.chat(
            [{"role": "user", "content": prompt}],
            tools=[], max_tokens=10
        )
        result = (response.text or "").strip().lower()
        if result in ("trivial", "simple", "medium", "complex"):
            return result
        return "medium"
    except Exception:
        return "medium"


def classify_complexity(message: str, provider=None) -> dict:
    """Main entry point. Tier 0 first, Tier 2 fallback.

    Returns dict with complexity, tier_used, stage_template, role_count.
    """
    result = classify_complexity_deterministic(message)
    tier_used = 0

    if result is None:
        if provider:
            result = classify_complexity_llm(message, provider)
            tier_used = 2
        else:
            result = "medium"
            tier_used = -1

    return {
        "complexity": result,
        "tier_used": tier_used,
        "stage_template": STAGE_TEMPLATES[result],
        "role_count": len(STAGE_TEMPLATES[result])
    }


def get_stage_template(complexity: str) -> list:
    """Get stage template for a complexity class."""
    return STAGE_TEMPLATES.get(complexity, STAGE_TEMPLATES["medium"])
