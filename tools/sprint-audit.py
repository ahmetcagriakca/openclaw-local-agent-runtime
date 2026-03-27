#!/usr/bin/env python3
"""
sprint-audit.py — Sprint closure audit tool for Vezir Platform
Usage: python tools/sprint-audit.py <sprint_number> [--model A|B]

Generates: docs/review-packets/S{N}-REVIEW-PACKET.md
           docs/review-packets/S{N}-AUDIT-RESULT.json

Policy enforcement: reads tools/sprint-policy.yml for per-sprint model constraints.
If sprint has forced_model, --model flag is ignored and policy wins.

Exit codes:
  0 = ELIGIBLE FOR CLOSURE REVIEW
  1 = NOT CLOSEABLE
  2 = usage error
"""

import sys
import os
import re
import json
from pathlib import Path
from datetime import datetime, timezone

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

# ── Config ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
EVIDENCE_PATHS = [
    "evidence/sprint-{N}",
    "docs/sprints/sprint-{N}/evidence",
]
SPRINT_DOC_PATHS = [
    "docs/sprints/sprint-{N}",
]
DECISIONS_FILE = REPO_ROOT / "docs" / "ai" / "DECISIONS.md"
STATE_FILE = REPO_ROOT / "docs" / "ai" / "STATE.md"

MANDATORY_EVIDENCE_FILES = [
    "pytest-output.txt",
    "vitest-output.txt",
    "tsc-output.txt",
    "lint-output.txt",
    "build-output.txt",
    "validator-output.txt",
    "grep-evidence.txt",
    "live-checks.txt",
    "review-summary.md",
    "file-manifest.txt",
]

SPRINT_10_PLUS = ["sse-evidence.txt"]
SPRINT_12_PLUS = ["e2e-output.txt", "lighthouse.txt"]

CANONICAL_SPRINT_FILES = [
    "S{N}-README.md",
    "S{N}-CLOSURE-SUMMARY.md",
    "S{N}-RETROSPECTIVE.md",
    "S{N}-CLOSURE-CONFIRMATION.md",
    "S{N}-EVIDENCE-AUDIT-RESULT.md",
]

STALE_LANGUAGE = [
    "COMPLETE", "CODE-COMPLETE", "fully validated",
    "sorunsuz", "no issues", "all done",
]

BANNED_STATUS_TERMS = ["CODE-COMPLETE", "COMPLETE"]

GHOST_DECISION_PATTERNS = [
    r"D-\d{3}.*not proposed",
    r"D-\d{3}.*unclear",
    r"D-\d{3}.*pending decision",
    r"\bOD-\d+\b",  # open decisions still referenced
]

POLICY_FILE = REPO_ROOT / "tools" / "sprint-policy.yml"

# ── Policy loader ─────────────────────────────────────────────────────────────

def load_sprint_policy(n: int) -> dict:
    """
    Returns effective policy for sprint N.
    Reads sprint-policy.yml if available (no external yaml dep — manual parse).
    Returns: {forced_model: str|None, reason: str, require_explicit: bool}
    """
    policy = {"forced_model": None, "reason": "", "require_explicit": True}
    if not POLICY_FILE.exists():
        return policy

    content = POLICY_FILE.read_text(encoding="utf-8")

    # Find sprint block: look for "  {N}:" pattern
    sprint_block = re.search(
        rf'^\s+{n}:\s*\n((?:\s{{4,}}[^\n]+\n?)*)',
        content, re.MULTILINE
    )
    if sprint_block:
        block = sprint_block.group(1)
        fm = re.search(r'forced_model:\s*"([AB])"', block)
        reason = re.search(r'reason:\s*"([^"]+)"', block)
        if fm:
            policy["forced_model"] = fm.group(1)
        if reason:
            policy["reason"] = reason.group(1)

    return policy

# ── Helpers ───────────────────────────────────────────────────────────────────

def resolve_path(template: str, n: int) -> Path:
    return REPO_ROOT / template.replace("{N}", str(n))

def find_evidence_dir(n: int) -> tuple[Path | None, str]:
    for tmpl in EVIDENCE_PATHS:
        p = resolve_path(tmpl, n)
        if p.exists():
            return p, tmpl.replace("{N}", str(n))
    return None, ""

def find_sprint_dir(n: int) -> Path | None:
    for tmpl in SPRINT_DOC_PATHS:
        p = resolve_path(tmpl, n)
        if p.exists():
            return p
    return None

def read_file_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def find_file_icase(directory: Path, name: str) -> Path | None:
    """Find file by name, case-insensitive."""
    name_lower = name.lower()
    for f in directory.rglob("*"):
        if f.name.lower() == name_lower:
            return f
    return None

def check_stale_language(content: str, filename: str) -> list[str]:
    hits = []
    for term in STALE_LANGUAGE:
        if term.lower() in content.lower():
            hits.append(f"  '{term}' in {filename}")
    return hits

def check_ghost_decisions(content: str) -> list[str]:
    hits = []
    for pattern in GHOST_DECISION_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for m in matches:
            hits.append(f"  Ghost/open decision reference: '{m}'")
    return hits

def check_status_fields(content: str, filename: str) -> list[str]:
    issues = []
    for term in BANNED_STATUS_TERMS:
        if term in content:
            issues.append(f"  Banned status term '{term}' in {filename}")
    # Check for consistent status model
    if "closure_status=closed" in content and "implementation_status" not in content:
        issues.append(f"  closure_status=closed without implementation_status in {filename}")
    return issues

def find_broken_refs(content: str, base_dir: Path) -> list[str]:
    """Find markdown links and check if they resolve."""
    broken = []
    # [text](path) style refs
    for m in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', content):
        ref = m.group(2)
        if ref.startswith("http") or ref.startswith("#"):
            continue
        target = (base_dir / ref).resolve()
        if not target.exists():
            broken.append(f"  Broken ref: {ref}")
    return broken

def get_decision_count() -> int:
    if not DECISIONS_FILE.exists():
        return -1
    content = read_file_safe(DECISIONS_FILE)
    matches = re.findall(r'^###\s+D-(\d+)', content, re.MULTILINE)
    return len(matches)

def check_retrospective_present(sprint_dir: Path, n: int) -> bool:
    retro_name = f"S{n}-RETROSPECTIVE.md"
    return (sprint_dir / retro_name).exists()

# ── Main audit ────────────────────────────────────────────────────────────────

def audit_sprint(n: int, model: str = "B") -> dict:
    # ── Policy enforcement ────────────────────────────────────────────────────
    policy = load_sprint_policy(n)
    policy_note = None
    if policy["forced_model"] and policy["forced_model"] != model:
        policy_note = (
            f"POLICY OVERRIDE: Sprint {n} requires Model {policy['forced_model']} "
            f"(you passed: --model {model}). "
            f"Reason: {policy['reason']}"
        )
        model = policy["forced_model"]

    result = {
        "sprint": n,
        "model": model,
        "policy_note": policy_note,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "eligible": True,
        "blockers": [],
        "warnings": [],
        "evidence": {},
        "canonical": {},
        "archive_candidates": [],
        "stale_language": [],
        "ghost_decisions": [],
        "broken_refs": [],
        "status_issues": [],
        "waivers": [],
        "verdict": "",
    }

    if policy_note:
        # Model A enforcement: if user passed B but policy says A, this is an error, not just a warning
        if policy["forced_model"] == "A":
            result["blockers"].append(
                f"BLOCKER: {policy_note} — Model B is forbidden for Sprint {n}. "
                f"Re-run with --model A or omit --model flag."
            )
            result["eligible"] = False
        else:
            result["warnings"].insert(0, policy_note)

    # ── 1. Evidence directory ─────────────────────────────────────────────────
    ev_dir, ev_path = find_evidence_dir(n)
    if ev_dir is None:
        result["blockers"].append(f"BLOCKER: Evidence directory not found (checked: {', '.join(t.replace('{N}', str(n)) for t in EVIDENCE_PATHS)})")
        result["eligible"] = False
    else:
        result["evidence"]["path"] = str(ev_dir.relative_to(REPO_ROOT))
        # Path compliance
        compliant_path = f"evidence/sprint-{n}"
        if not str(ev_dir.relative_to(REPO_ROOT)).startswith(compliant_path):
            result["warnings"].append(f"NON-COMPLIANT path: evidence at '{ev_path}' not '{compliant_path}' (process debt)")

        # File inventory
        all_files = list(ev_dir.rglob("*"))
        evidence_files = [f for f in all_files if f.is_file()]
        result["evidence"]["file_count"] = len(evidence_files)
        result["evidence"]["files"] = []

        for f in sorted(evidence_files):
            size = f.stat().st_size
            lines = len(f.read_bytes().splitlines())
            result["evidence"]["files"].append({
                "name": f.name,
                "lines": lines,
                "empty": size == 0,
            })
            if size == 0:
                result["blockers"].append(f"BLOCKER: Empty evidence file: {f.name}")
                result["eligible"] = False

        # Mandatory file check
        mandatory = list(MANDATORY_EVIDENCE_FILES)
        if n >= 10:
            mandatory += SPRINT_10_PLUS
        if n >= 12:
            mandatory += SPRINT_12_PLUS

        result["evidence"]["mandatory_check"] = []
        for mf in mandatory:
            found = find_file_icase(ev_dir, mf)
            if found:
                result["evidence"]["mandatory_check"].append({"file": mf, "status": "PRESENT"})
            else:
                # Check if there's an equivalent by content category
                result["evidence"]["mandatory_check"].append({"file": mf, "status": "ABSENT — waiver required"})
                result["waivers"].append(f"WAIVER NEEDED: {mf} absent from evidence")

    # ── 2. Sprint doc directory ───────────────────────────────────────────────
    sprint_dir = find_sprint_dir(n)
    if sprint_dir is None:
        result["blockers"].append(f"BLOCKER: Sprint doc directory not found under docs/sprints/sprint-{n}/")
        result["eligible"] = False
    else:
        result["canonical"]["path"] = str(sprint_dir.relative_to(REPO_ROOT))

        # Canonical file check
        result["canonical"]["files"] = []
        for tmpl in CANONICAL_SPRINT_FILES:
            fname = tmpl.replace("{N}", str(n))
            p = sprint_dir / fname
            if p.exists():
                result["canonical"]["files"].append({"file": fname, "status": "PRESENT"})
                # Content checks
                content = read_file_safe(p)
                result["stale_language"] += check_stale_language(content, fname)
                result["ghost_decisions"] += check_ghost_decisions(content)
                result["status_issues"] += check_status_fields(content, fname)
                result["broken_refs"] += find_broken_refs(content, sprint_dir)
            else:
                result["canonical"]["files"].append({"file": fname, "status": "MISSING"})
                if fname in [f"S{n}-README.md", f"S{n}-RETROSPECTIVE.md", f"S{n}-CLOSURE-CONFIRMATION.md"]:
                    result["blockers"].append(f"BLOCKER: Canonical file missing: {fname}")
                    result["eligible"] = False
                else:
                    result["warnings"].append(f"WARNING: Canonical file missing: {fname}")

        # Retrospective check (never waivable)
        if not check_retrospective_present(sprint_dir, n):
            result["blockers"].append(f"BLOCKER: S{n}-RETROSPECTIVE.md missing — retrospective is never waivable")
            result["eligible"] = False

        # Archive candidates
        for f in sprint_dir.rglob("*"):
            if f.is_file():
                fname_lower = f.name.lower()
                if any(x in fname_lower for x in ["advance-plan", "draft", "temp", "old", "backup"]):
                    content = read_file_safe(f)
                    has_historical = "HISTORICAL" in content or "historical" in content.lower()
                    result["archive_candidates"].append({
                        "file": str(f.relative_to(REPO_ROOT)),
                        "annotated": has_historical,
                        "action": "OK — annotated" if has_historical else "NEEDS HISTORICAL ANNOTATION",
                    })

    # ── 3. Decision governance ────────────────────────────────────────────────
    decision_count = get_decision_count()
    result["decisions"] = {"frozen_count": decision_count}

    if DECISIONS_FILE.exists():
        decisions_content = read_file_safe(DECISIONS_FILE)
        result["ghost_decisions"] += check_ghost_decisions(decisions_content)
        # Check for any OD- open decisions referenced
        od_refs = re.findall(r'\bOD-\d+\b', decisions_content)
        if od_refs:
            result["warnings"].append(f"Open decision references in DECISIONS.md: {', '.join(set(od_refs))}")

    # ── 4. State sync check ───────────────────────────────────────────────────
    if STATE_FILE.exists():
        state_content = read_file_safe(STATE_FILE)
        sprint_pattern = rf"sprint[_\s-]*{n}[^\n]*closed"
        if not re.search(sprint_pattern, state_content, re.IGNORECASE):
            result["warnings"].append(f"WARNING: Sprint {n} closure not reflected in STATE.md")

    # ── 5. Verdict ────────────────────────────────────────────────────────────
    if result["eligible"] and not result["blockers"]:
        result["verdict"] = "ELIGIBLE FOR CLOSURE REVIEW"
    else:
        result["verdict"] = "NOT CLOSEABLE"
        result["eligible"] = False

    return result


# ── Report generation ─────────────────────────────────────────────────────────

def generate_report(r: dict) -> str:
    n = r["sprint"]
    ts = r["timestamp"]
    verdict = r["verdict"]
    model = r["model"]

    # Audit summary counts for human-readable header
    blocker_count  = len(r["blockers"])
    warning_count  = len(r["warnings"])
    waiver_count   = len(r["waivers"])
    ev_files       = r.get("evidence", {}).get("file_count", "?")
    ev_mandatory   = r.get("evidence", {}).get("mandatory_check", [])
    covered        = sum(1 for m in ev_mandatory if m["status"] == "PRESENT")
    total_mandatory = len(ev_mandatory)
    canon_files    = r.get("canonical", {}).get("files", [])
    canon_present  = sum(1 for c in canon_files if c["status"] == "PRESENT")
    canon_total    = len(canon_files)
    frozen_decisions = r.get("decisions", {}).get("frozen_count", "?")
    ghost_count    = len(r["ghost_decisions"])
    stale_count    = len(r["stale_language"])
    broken_count   = len(r["broken_refs"])

    verdict_icon = "✅" if verdict == "ELIGIBLE FOR CLOSURE REVIEW" else "❌"
    policy_line  = f"\n**Policy Note:** {r['policy_note']}" if r.get("policy_note") else ""

    lines = [
        f"# S{n}-REVIEW-PACKET.md",
        f"",
        f"**Sprint:** {n}",
        f"**Generated:** {ts}",
        f"**Closure Model:** Model {model}",
        f"**Verdict:** {verdict_icon} {verdict}",
        policy_line if policy_line else "",
        f"",
        f"---",
        f"",
        f"## AUDIT SUMMARY",
        f"",
        f"| Dimension | Result |",
        f"|-----------|--------|",
        f"| Verdict | {verdict_icon} **{verdict}** |",
        f"| Closure Model | Model {model} |",
        f"| Blockers | {'❌ ' + str(blocker_count) if blocker_count else '✅ 0'} |",
        f"| Warnings | {'⚠️ ' + str(warning_count) if warning_count else '✅ 0'} |",
        f"| Waivers required | {'⚠️ ' + str(waiver_count) if waiver_count else '✅ 0'} |",
        f"| Evidence files | {ev_files} |",
        f"| Mandatory coverage | {covered}/{total_mandatory} |",
        f"| Canonical files | {canon_present}/{canon_total} |",
        f"| Frozen decisions | {frozen_decisions} |",
        f"| Ghost decision refs | {'❌ ' + str(ghost_count) if ghost_count else '✅ 0'} |",
        f"| Stale language hits | {'⚠️ ' + str(stale_count) if stale_count else '✅ 0'} |",
        f"| Broken refs | {'⚠️ ' + str(broken_count) if broken_count else '✅ 0'} |",
        f"",
        f"**Reviewer action required:**",
    ]

    if blocker_count:
        lines.append(f"- Fix {blocker_count} blocker(s) listed in Section 2 before closure.")
    if waiver_count:
        lines.append(f"- Confirm or reject {waiver_count} waiver(s) in Section 7.")
    if not blocker_count and not waiver_count:
        lines.append(f"- Review findings below and return: **PASS** or **HOLD + patch list**.")

    lines += [
        f"",
        f"---",
        f"",
        f"",
        f"---",
        f"",
        f"## 1. Verdict",
        f"",
        f"```",
        f"{verdict}",
        f"```",
        f"",
    ]

    # Blockers
    if r["blockers"]:
        lines += [f"## 2. Blockers ({len(r['blockers'])})", ""]
        for b in r["blockers"]:
            lines.append(f"- {b}")
        lines.append("")
    else:
        lines += [f"## 2. Blockers", "", "None.", ""]

    # Warnings
    if r["warnings"]:
        lines += [f"## 3. Warnings ({len(r['warnings'])})", ""]
        for w in r["warnings"]:
            lines.append(f"- {w}")
        lines.append("")
    else:
        lines += [f"## 3. Warnings", "", "None.", ""]

    # Evidence
    lines += [f"## 4. Evidence Audit", ""]
    ev = r.get("evidence", {})
    if "path" in ev:
        lines.append(f"**Path:** `{ev['path']}`")
        lines.append(f"**File count:** {ev.get('file_count', 0)}")
        lines.append("")
        if ev.get("files"):
            lines.append("| File | Lines | Status |")
            lines.append("|------|-------|--------|")
            for f in ev["files"]:
                status = "⚠️ EMPTY" if f["empty"] else "✅"
                lines.append(f"| `{f['name']}` | {f['lines']} | {status} |")
            lines.append("")

        lines.append("**Mandatory coverage:**")
        lines.append("")
        lines.append("| Mandatory File | Status |")
        lines.append("|----------------|--------|")
        for mc in ev.get("mandatory_check", []):
            icon = "✅" if mc["status"] == "PRESENT" else "❌"
            lines.append(f"| `{mc['file']}` | {icon} {mc['status']} |")
        lines.append("")
    else:
        lines.append("Evidence directory not found.")
        lines.append("")

    # Canonical files
    lines += ["## 5. Canonical File Set", ""]
    canon = r.get("canonical", {})
    if canon.get("files"):
        lines.append("| File | Status |")
        lines.append("|------|--------|")
        for cf in canon["files"]:
            icon = "✅" if cf["status"] == "PRESENT" else "❌"
            lines.append(f"| `{cf['file']}` | {icon} {cf['status']} |")
        lines.append("")

    # Archive candidates
    if r["archive_candidates"]:
        lines += ["## 6. Archive Candidates", ""]
        lines.append("| File | Annotated? | Action |")
        lines.append("|------|------------|--------|")
        for ac in r["archive_candidates"]:
            icon = "✅" if ac["annotated"] else "⚠️"
            lines.append(f"| `{ac['file']}` | {icon} | {ac['action']} |")
        lines.append("")

    # Waivers needed
    if r["waivers"]:
        lines += ["## 7. Waivers Required", ""]
        for w in r["waivers"]:
            lines.append(f"- {w}")
        lines.append("")

    # Stale language
    if r["stale_language"]:
        lines += ["## 8. Stale Language Detected", ""]
        for s in r["stale_language"]:
            lines.append(f"- {s}")
        lines.append("")

    # Ghost decisions
    if r["ghost_decisions"]:
        lines += ["## 9. Ghost / Open Decision References", ""]
        for g in r["ghost_decisions"]:
            lines.append(f"- {g}")
        lines.append("")

    # Broken refs
    if r["broken_refs"]:
        lines += ["## 10. Broken Document References", ""]
        for br in r["broken_refs"]:
            lines.append(f"- {br}")
        lines.append("")

    # Status issues
    if r["status_issues"]:
        lines += ["## 11. Status Field Issues", ""]
        for si in r["status_issues"]:
            lines.append(f"- {si}")
        lines.append("")

    # Decision governance
    dc = r.get("decisions", {})
    lines += [
        "## 12. Decision Governance",
        "",
        f"**Frozen decisions in DECISIONS.md:** {dc.get('frozen_count', 'unknown')}",
        "",
    ]

    # Footer
    lines += [
        "---",
        "",
        f"*Generated by `tools/sprint-audit.py {n}` — {ts}*",
        f"*Verdict: {verdict}*",
    ]

    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/sprint-audit.py <sprint_number> [--model A|B]")
        sys.exit(2)

    try:
        n = int(sys.argv[1])
    except ValueError:
        print(f"Error: sprint number must be an integer, got '{sys.argv[1]}'")
        sys.exit(2)

    model = "B"
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            model = sys.argv[idx + 1].upper()
            if model not in ("A", "B"):
                print("Error: --model must be A or B")
                sys.exit(2)

    print(f"[sprint-audit] Auditing Sprint {n}, Model {model}...")

    result = audit_sprint(n, model)
    report = generate_report(result)

    # Write review packet
    out_dir = REPO_ROOT / "docs" / "review-packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"S{n}-REVIEW-PACKET.md"
    out_file.write_text(report, encoding="utf-8")

    print(f"[sprint-audit] Review packet: {out_file.relative_to(REPO_ROOT)}")
    print(f"[sprint-audit] Verdict: {result['verdict']}")

    if result["blockers"]:
        print(f"[sprint-audit] BLOCKERS ({len(result['blockers'])}):")
        for b in result["blockers"]:
            print(f"  {b}")

    if result["warnings"]:
        print(f"[sprint-audit] Warnings ({len(result['warnings'])}):")
        for w in result["warnings"]:
            print(f"  {w}")

    # Also write JSON for programmatic use
    json_file = out_dir / f"S{n}-AUDIT-RESULT.json"
    json_file.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    exit_code = 0 if result["eligible"] else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
