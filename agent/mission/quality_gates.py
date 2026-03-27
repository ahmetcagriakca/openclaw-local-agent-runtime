"""Quality gates — 3 gates that validate artifacts between stage groups."""
from dataclasses import dataclass, field

from artifacts.schema_validator import validate_artifact_data


@dataclass
class GateResult:
    passed: bool
    gate_name: str
    findings: list = field(default_factory=list)
    blocking_issues: list = field(default_factory=list)
    recommendation: str = "proceed"  # "proceed" | "rework" | "abort"


def check_gate_1(artifacts: dict, assembler) -> GateResult:
    """Gate 1: Requirements + Design Approval.

    Runs AFTER: product-owner, analyst, architect, project-manager
    Runs BEFORE: developer
    """
    findings = []
    blocking = []

    req_artifacts = _find_artifacts_by_type(assembler, "requirements_brief")
    if not req_artifacts:
        blocking.append("No requirements_brief artifact produced")
    else:
        req_data = _get_artifact_data(req_artifacts[-1], assembler)
        errors = validate_artifact_data("requirements_brief", req_data)
        if errors:
            findings.append({"check": "requirements_brief_schema",
                             "status": "fail",
                             "detail": f"{len(errors)} validation errors: {errors[:3]}"})
            blocking.extend(errors[:2])
        else:
            findings.append({"check": "requirements_brief_schema",
                             "status": "pass",
                             "detail": "All required fields present"})

    analysis_artifacts = _find_artifacts_by_type(assembler, "analysis_report")
    if analysis_artifacts:
        analysis_data = _get_artifact_data(analysis_artifacts[-1], assembler)
        rec = analysis_data.get("recommendation", "")
        if rec == "reject":
            blocking.append(f"Analysis recommends REJECT: {analysis_data.get('reason', '')}")
            findings.append({"check": "analysis_recommendation", "status": "fail",
                             "detail": f"Recommendation: {rec}"})
        else:
            findings.append({"check": "analysis_recommendation", "status": "pass",
                             "detail": f"Recommendation: {rec}"})

    discovery_artifacts = _find_artifacts_by_type(assembler, "discovery_map")
    if discovery_artifacts:
        disc_data = _get_artifact_data(discovery_artifacts[-1], assembler)
        recs = disc_data.get("working_set_recommendations", {})
        if not recs.get("developer"):
            findings.append({"check": "discovery_map_completeness", "status": "warn",
                             "detail": "No developer file recommendations"})
        else:
            findings.append({"check": "discovery_map_completeness", "status": "pass",
                             "detail": f"Developer targets: {len(recs['developer'])} files"})

    passed = len(blocking) == 0
    return GateResult(passed=passed, gate_name="gate_1_requirements_design",
                      findings=findings, blocking_issues=blocking,
                      recommendation="proceed" if passed else "rework")


def check_gate_2(artifacts: dict, assembler) -> GateResult:
    """Gate 2: Code + Test Verification.

    Runs AFTER: developer, tester
    Runs BEFORE: reviewer
    """
    findings = []
    blocking = []

    code_artifacts = _find_artifacts_by_type(assembler, "code_delivery")
    if not code_artifacts:
        blocking.append("No code_delivery artifact produced")
    else:
        code_data = _get_artifact_data(code_artifacts[-1], assembler)
        touched = code_data.get("touched_files", [])
        if not touched:
            findings.append({"check": "code_delivery_files", "status": "warn",
                             "detail": "code_delivery has no touched_files"})
        else:
            findings.append({"check": "code_delivery_files", "status": "pass",
                             "detail": f"{len(touched)} files touched"})

    test_artifacts = _find_artifacts_by_type(assembler, "test_report")
    if not test_artifacts:
        blocking.append("No test_report artifact produced")
    else:
        test_data = _get_artifact_data(test_artifacts[-1], assembler)
        verdict = test_data.get("verdict", "unknown")

        if verdict == "fail":
            blocking.append(f"Test verdict: {verdict}")
            findings.append({"check": "test_verdict", "status": "fail",
                             "detail": f"Verdict: {verdict}"})
        elif verdict in ("pass", "conditional_pass"):
            findings.append({"check": "test_verdict", "status": "pass",
                             "detail": f"Verdict: {verdict}"})
        else:
            findings.append({"check": "test_verdict", "status": "warn",
                             "detail": f"Unknown verdict: {verdict}"})

        bugs = test_data.get("bugs", [])
        critical_bugs = [b for b in bugs if b.get("severity") == "critical"]
        if critical_bugs:
            blocking.append(f"{len(critical_bugs)} critical bugs found")
            findings.append({"check": "critical_bugs", "status": "fail",
                             "detail": f"{len(critical_bugs)} critical bugs"})

    passed = len(blocking) == 0
    return GateResult(passed=passed, gate_name="gate_2_code_test",
                      findings=findings, blocking_issues=blocking,
                      recommendation="proceed" if passed else "rework")


def check_gate_3(artifacts: dict, assembler) -> GateResult:
    """Gate 3: Final Review Approval.

    Runs AFTER: reviewer
    Runs BEFORE: delivery / manager summary
    """
    findings = []
    blocking = []

    review_artifacts = _find_artifacts_by_type(assembler, "review_decision")
    if not review_artifacts:
        blocking.append("No review_decision artifact produced")
    else:
        review_data = _get_artifact_data(review_artifacts[-1], assembler)
        decision = review_data.get("decision", "unknown")

        if decision == "approve":
            findings.append({"check": "review_decision", "status": "pass",
                             "detail": "Approved"})
        elif decision == "request_changes":
            blocking.append("Reviewer requested changes")
            findings.append({"check": "review_decision", "status": "fail",
                             "detail": "Changes requested"})
        elif decision == "reject":
            blocking.append("Reviewer rejected")
            findings.append({"check": "review_decision", "status": "fail",
                             "detail": "Rejected"})

        security = review_data.get("security_concerns", "none")
        if security and security != "none":
            if isinstance(security, list) and any(
                    s.get("severity") == "critical" for s in security):
                blocking.append("Critical security concerns")

    passed = len(blocking) == 0
    rec = "proceed" if passed else (
        "rework" if "requested changes" in str(blocking).lower() else "abort")
    return GateResult(passed=passed, gate_name="gate_3_review",
                      findings=findings, blocking_issues=blocking,
                      recommendation=rec)


def _find_artifacts_by_type(assembler, artifact_type):
    if assembler:
        return [aid for aid, art in assembler.artifacts.items()
                if art.get("type") == artifact_type]
    return []


def _get_artifact_data(artifact_id, assembler):
    if assembler and artifact_id in assembler.artifacts:
        return assembler.artifacts[artifact_id].get("data", {})
    return {}
