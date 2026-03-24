"""Artifact extractor — parse structured fields from LLM response text."""
import json
import re


def extract_artifact_fields(artifact_type: str, response_text: str) -> dict:
    """Extract structured fields from LLM response text.

    Strategy: JSON extraction → regex fallback → safe defaults.
    Returns dict with extracted fields merged into existing data.
    """
    if not response_text:
        return {}

    # Strategy 1: Try to find a JSON block in the response
    extracted = _try_json_extraction(response_text)
    if extracted:
        return extracted

    # Strategy 2: Type-specific regex extraction
    type_extractors = {
        "test_report": _extract_test_report,
        "review_decision": _extract_review_decision,
        "analysis_report": _extract_analysis_report,
        "discovery_map": _extract_discovery_map,
        "code_delivery": _extract_code_delivery,
        "requirements_brief": _extract_requirements_brief,
        "work_plan": _extract_work_plan,
        "recovery_decision": _extract_recovery_decision,
    }

    extractor = type_extractors.get(artifact_type)
    if extractor:
        return extractor(response_text)

    return {}


def _try_json_extraction(text: str) -> dict | None:
    """Try to extract a JSON object from response text."""
    # Try full text as JSON
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to find JSON block in markdown code fence
    json_patterns = [
        r'```json\s*\n(.*?)\n```',
        r'```\s*\n(\{.*?\})\n```',
        r'(\{[^{}]*"(?:verdict|decision|recommendation|touched_files|title|recovery_action)"[^{}]*\})',
    ]

    for pattern in json_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, ValueError):
                continue

    # Try to find the largest JSON object in text
    brace_start = text.find('{')
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(text[brace_start:i+1])
                        if isinstance(data, dict):
                            return data
                    except (json.JSONDecodeError, ValueError):
                        break

    return None


def _extract_test_report(text: str) -> dict:
    """Extract test_report fields: verdict, bugs."""
    result = {}

    # Verdict extraction
    verdict_patterns = [
        r'(?:verdict|sonuç|karar)\s*[:=]\s*["\']?(pass|fail|conditional_pass)["\']?',
        r'\b(PASS|FAIL|CONDITIONAL_PASS)\b',
        r'(?:test\s+)?(?:result|verdict)\s*[:]\s*["\']?(pass|fail|conditional[_\s]pass)["\']?',
    ]
    for pattern in verdict_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            verdict = match.group(1).lower().replace(' ', '_')
            if verdict in ('pass', 'fail', 'conditional_pass'):
                result["verdict"] = verdict
                break

    if "verdict" not in result:
        # Heuristic: if text contains "fail", "error", "bug" -> fail
        fail_indicators = ['fail', 'error', 'bug', 'broken', 'hata', 'başarısız']
        pass_indicators = ['pass', 'success', 'ok', 'başarılı', 'geçti']

        text_lower = text.lower()
        fail_count = sum(1 for w in fail_indicators if w in text_lower)
        pass_count = sum(1 for w in pass_indicators if w in text_lower)

        if fail_count > pass_count:
            result["verdict"] = "fail"
        elif pass_count > 0:
            result["verdict"] = "pass"
        else:
            result["verdict"] = "conditional_pass"  # safe default

    # Bug extraction (best effort)
    bug_pattern = r'(?:bug|issue|problem|hata)\s*(?:\d+)?\s*[:]\s*(.+?)(?:\n|$)'
    bugs = re.findall(bug_pattern, text, re.IGNORECASE)
    if bugs:
        result["bugs"] = [{"description": b.strip(), "severity": "major"} for b in bugs[:10]]

    return result


def _extract_review_decision(text: str) -> dict:
    """Extract review_decision fields: decision, findings."""
    result = {}

    decision_patterns = [
        r'(?:decision|karar|sonuç)\s*[:=]\s*["\']?(approve|request_changes|reject)["\']?',
        r'\b(APPROVE|APPROVED|REQUEST_CHANGES|REJECT|REJECTED)\b',
    ]
    for pattern in decision_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            decision = match.group(1).lower()
            if decision == 'approved':
                decision = 'approve'
            elif decision == 'rejected':
                decision = 'reject'
            if decision in ('approve', 'request_changes', 'reject'):
                result["decision"] = decision
                break

    if "decision" not in result:
        text_lower = text.lower()
        if 'reject' in text_lower:
            result["decision"] = "reject"
        elif 'change' in text_lower or 'düzelt' in text_lower or 'değiştir' in text_lower:
            result["decision"] = "request_changes"
        else:
            result["decision"] = "approve"  # safe default

    # Security concerns
    security_patterns = ['security', 'güvenlik', 'vulnerability', 'injection', 'xss', 'csrf']
    text_lower = text.lower()
    security_found = [s for s in security_patterns if s in text_lower]
    if security_found:
        result["security_concerns"] = [{"description": s, "severity": "major"} for s in security_found]
    else:
        result["security_concerns"] = "none"

    return result


def _extract_analysis_report(text: str) -> dict:
    """Extract analysis_report fields: feasibility, recommendation."""
    result = {}

    rec_patterns = [
        r'(?:recommendation|öneri|tavsiye)\s*[:=]\s*["\']?(proceed|proceed_with_caution|defer|reject)["\']?',
        r'\b(PROCEED|DEFER|REJECT)\b',
    ]
    for pattern in rec_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            rec = match.group(1).lower()
            if rec in ('proceed', 'proceed_with_caution', 'defer', 'reject'):
                result["recommendation"] = rec
                break

    if "recommendation" not in result:
        text_lower = text.lower()
        if 'reject' in text_lower or 'reddet' in text_lower:
            result["recommendation"] = "reject"
        elif 'defer' in text_lower or 'ertele' in text_lower:
            result["recommendation"] = "defer"
        else:
            result["recommendation"] = "proceed"

    # Feasibility
    feas_patterns = [
        r'(?:feasibility|fizibilite|uygulanabilirlik)\s*[:=]\s*["\']?(high|medium|low)["\']?',
    ]
    for pattern in feas_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["feasibility"] = match.group(1).lower()
            break

    if "feasibility" not in result:
        result["feasibility"] = "medium"

    return result


def _extract_discovery_map(text: str) -> dict:
    """Extract discovery_map fields -- best effort from text."""
    result = {
        "repo_structure": [],
        "relevant_files": [],
        "component_map": [],
        "working_set_recommendations": {}
    }

    # File path extraction
    file_pattern = r'(?:agent|bin|bridge|wsl|docs|actions|config|defs)[/\\][\w./\\-]+'
    files = re.findall(file_pattern, text)
    if files:
        result["relevant_files"] = [
            {"path": f, "purpose": "discovered", "relevance_score": 0.7}
            for f in list(set(files))[:20]
        ]
        result["working_set_recommendations"] = {
            "developer": list(set(files))[:10],
            "tester": list(set(files))[:5],
            "reviewer": list(set(files))[:5],
        }

    return result


def _extract_code_delivery(text: str) -> dict:
    """Extract code_delivery fields: touched_files."""
    result = {}

    file_pattern = r'(?:agent|bin|bridge|wsl|docs|actions|config|defs)[/\\][\w./\\-]+\.(?:py|ps1|json|md|txt|sh)'
    files = re.findall(file_pattern, text)
    if files:
        result["touched_files"] = list(set(files))
    else:
        result["touched_files"] = []

    return result


def _extract_requirements_brief(text: str) -> dict:
    """Extract requirements_brief fields: title, summary, requirements."""
    result = {}

    # Title
    title_match = re.search(r'(?:title|başlık)\s*[:=]\s*["\']?(.+?)["\']?\s*$', text, re.IGNORECASE | re.MULTILINE)
    if title_match:
        result["title"] = title_match.group(1).strip()
    else:
        # First line as title
        first_line = text.strip().split('\n')[0][:100]
        result["title"] = first_line

    result["summary"] = text[:500] if len(text) > 500 else text
    result["requirements"] = [
        {"id": "REQ-1", "description": text[:200], "acceptance_criteria": "Implemented as described"}
    ]

    return result


def _extract_work_plan(text: str) -> dict:
    """Extract work_plan fields: tasks."""
    result = {"tasks": []}

    task_pattern = r'(?:task|görev|adım)\s*(\d+)\s*[:]\s*(.+?)(?:\n|$)'
    tasks = re.findall(task_pattern, text, re.IGNORECASE)
    for tid, desc in tasks[:10]:
        result["tasks"].append({
            "id": f"TASK-{tid}",
            "description": desc.strip(),
            "acceptance_criteria": "Completed as described"
        })

    if not result["tasks"]:
        result["tasks"] = [
            {"id": "TASK-1", "description": text[:200], "acceptance_criteria": "Completed"}
        ]

    return result


def _extract_recovery_decision(text: str) -> dict:
    """Extract recovery_decision fields: diagnosis, recovery_action."""
    result = {}

    action_patterns = [
        r'(?:recovery_action|aksiyon|karar)\s*[:=]\s*["\']?(retry_stage|abort|escalate_to_operator|retry_from_stage_N)["\']?',
    ]
    for pattern in action_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["recovery_action"] = match.group(1).lower()
            break

    if "recovery_action" not in result:
        text_lower = text.lower()
        if 'retry' in text_lower or 'tekrar' in text_lower:
            result["recovery_action"] = "retry_stage"
        elif 'escalate' in text_lower or 'yükselt' in text_lower:
            result["recovery_action"] = "escalate_to_operator"
        else:
            result["recovery_action"] = "abort"

    result["diagnosis"] = text[:500] if len(text) > 500 else text

    return result
