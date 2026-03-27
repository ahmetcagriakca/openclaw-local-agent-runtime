#!/usr/bin/env python3
"""
Sprint-End Documentation Validator
===================================
Sprint kapanışında zorunlu döküman güncellemelerini kontrol eder.
FAIL varsa sprint kapanmaz.
Usage:
    python tools/validate_sprint_docs.py --sprint 7 --sprint-date 2026-03-25
    python tools/validate_sprint_docs.py --sprint 7 --check freshness
    python tools/validate_sprint_docs.py --sprint 7 -v
"""
import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# oc_root = repo root. Script cwd'ye veya env'ye göre bulur.
def find_oc_root() -> Path:
    """Walk up from script location or cwd to find repo root."""
    # Env override
    env_root = os.environ.get("OC_ROOT")
    if env_root:
        return Path(env_root)

    # Walk up from script dir
    candidate = Path(__file__).resolve().parent
    for _ in range(5):
        if (candidate / "docs" / "ai" / "STATE.md").exists():
            return candidate
        candidate = candidate.parent

    # Walk up from cwd
    candidate = Path.cwd()
    for _ in range(5):
        if (candidate / "docs" / "ai" / "STATE.md").exists():
            return candidate
        candidate = candidate.parent

    print("[ERROR] Could not find OC_ROOT. Set OC_ROOT env or run from repo.",
          file=sys.stderr)
    sys.exit(2)


# Sprint → doc expectations mapping
SPRINT_DOC_CONFIG = {
    # Döküman yolu (oc_root'a göre relative)
    # required_sections: aranacak section başlıkları (case-insensitive substring)
    # freshness_required: True ise stale check yapılır
    # condition: None=her zaman, callable=koşullu
    "docs/ai/STATE.md": {
        "required_sections": ["system status", "completed phases"],
        "freshness_required": True,
        "description": "Project state",
    },
    "docs/ai/NEXT.md": {
        "required_sections": [],  # En az 1 satır non-empty content yeterli
        "freshness_required": True,
        "description": "Next steps",
    },
    "docs/ai/DECISIONS.md": {
        "required_sections": [],
        "freshness_required": False,  # Yeni karar yoksa güncellenmeyebilir
        "description": "Frozen decisions",
    },
    "docs/ai/BACKLOG.md": {
        "required_sections": [],
        "freshness_required": False,
        "description": "Backlog",
    },
    "docs/ai/GOVERNANCE.md": {
        "required_sections": [],
        "freshness_required": False,
        "description": "Sprint governance rules",
    },
}

# SESSION-HANDOFF ayrı kontrol — root'ta veya outputs'ta olabilir
HANDOFF_SECTIONS = ["tamamlanan", "bekleyen", "sonraki adım", "bir sonraki"]

# capabilities.json ayrı kontrol
CAPABILITIES_PATH = "config/capabilities.json"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    status: str  # PASS, FAIL, SKIP, WARN
    file: str
    message: str
    details: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def parse_date_from_content(content: str) -> Optional[datetime]:
    """Extract date from 'Last updated:', 'Date:', or '**Date:**' lines."""
    patterns = [
        r"(?:Last updated|Date|Updated):\s*(\d{4}-\d{2}-\d{2})",
        r"\*\*(?:Last updated|Date):\*\*\s*(\d{4}-\d{2}-\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d")
            except ValueError:
                continue
    return None


def check_freshness(filepath: Path, sprint_date: datetime) -> CheckResult:
    """Check if file was updated on or after sprint date."""
    if not filepath.exists():
        return CheckResult("FAIL", str(filepath), "File not found")

    content = filepath.read_text(encoding="utf-8", errors="replace")
    doc_date = parse_date_from_content(content)

    if doc_date is None:
        return CheckResult("WARN", str(filepath),
                           "No date found in file — manual check needed")

    if doc_date >= sprint_date:
        return CheckResult("PASS", str(filepath),
                           f"Fresh (doc: {doc_date.date()}, sprint: {sprint_date.date()})")

    return CheckResult(
        "FAIL", str(filepath),
        f"STALE (doc: {doc_date.date()}, sprint: {sprint_date.date()})"
    )


def check_required_sections(filepath: Path, sections: list[str]) -> CheckResult:
    """Check that required sections exist in file."""
    if not filepath.exists():
        return CheckResult("FAIL", str(filepath), "File not found")

    content = filepath.read_text(encoding="utf-8", errors="replace").lower()
    missing = [s for s in sections if s.lower() not in content]

    if missing:
        return CheckResult(
            "FAIL", str(filepath),
            f"MISSING_SECTION: {', '.join(missing)}"
        )
    return CheckResult("PASS", str(filepath), "All required sections present")


def check_handoff(oc_root: Path, sprint_date: datetime) -> list[CheckResult]:
    """Check SESSION-HANDOFF.md exists and has required sections."""
    results = []

    # Handoff olası yerlerde aranır
    candidates = [
        oc_root / "SESSION-HANDOFF.md",
        oc_root / "docs" / "SESSION-HANDOFF.md",
        oc_root / "docs" / "ai" / "SESSION-HANDOFF.md",
    ]

    handoff_path = None
    for c in candidates:
        if c.exists():
            handoff_path = c
            break

    if handoff_path is None:
        results.append(CheckResult(
            "FAIL", "SESSION-HANDOFF.md",
            "File not found in any expected location"
        ))
        return results

    # Freshness
    results.append(check_freshness(handoff_path, sprint_date))

    # Required sections
    content = handoff_path.read_text(encoding="utf-8", errors="replace").lower()

    # En az 1 "sonraki adım" varyantı olmalı
    has_next = any(term in content
                   for term in ["sonraki adım", "bir sonraki", "next step"])
    if not has_next:
        results.append(CheckResult(
            "FAIL", str(handoff_path),
            "MISSING_SECTION: 'Bir Sonraki Adım' / 'Next Step'"
        ))
    else:
        results.append(CheckResult("PASS", str(handoff_path),
                                   "Handoff sections present"))

    return results


def check_capabilities(oc_root: Path) -> CheckResult:
    """Check capabilities.json is auto-generated."""
    cap_path = oc_root / CAPABILITIES_PATH
    if not cap_path.exists():
        return CheckResult("FAIL", CAPABILITIES_PATH, "File not found")

    try:
        data = json.loads(cap_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return CheckResult("FAIL", CAPABILITIES_PATH, f"Invalid JSON: {e}")

    if not data.get("autoGenerated"):
        return CheckResult("FAIL", CAPABILITIES_PATH,
                           "autoGenerated is not true — manual edit suspected")

    cap_count = len(data.get("capabilities", {}))
    available = sum(1 for v in data.get("capabilities", {}).values()
                    if v.get("available"))
    return CheckResult(
        "PASS", CAPABILITIES_PATH,
        f"autoGenerated: true, {available}/{cap_count} capabilities available"
    )


def check_open_checkboxes(oc_root: Path, sprint: int) -> CheckResult:
    """Check sprint plan doc for unchecked checkboxes."""
    # Sprint plan doc naming patterns
    patterns = [
        f"SPRINT-{sprint}-*.md",
        f"*SPRINT*{sprint}*.md",
        f"*sprint*{sprint}*.md",
    ]

    # Arama dizinleri
    search_dirs = [oc_root, oc_root / "docs", oc_root / "docs" / "ai",
                   oc_root / "docs" / "phase-reports"]

    plan_path = None
    for d in search_dirs:
        if not d.exists():
            continue
        for p in patterns:
            matches = list(d.glob(p))
            if matches:
                plan_path = matches[0]
                break
        if plan_path:
            break

    # Fallback: search phase-reports for files mentioning this sprint
    if plan_path is None:
        reports_dir = oc_root / "docs" / "phase-reports"
        if reports_dir.exists():
            for f in sorted(reports_dir.iterdir(), reverse=True):
                if f.suffix == ".md" and f"Sprint {sprint}" in f.read_text(
                        encoding="utf-8", errors="replace"):
                    plan_path = f
                    break

    if plan_path is None:
        return CheckResult("WARN", f"Sprint {sprint} plan",
                           "Sprint plan doc not found — manual check needed")

    content = plan_path.read_text(encoding="utf-8", errors="replace")
    open_boxes = re.findall(r"- \[ \]", content)
    if open_boxes:
        return CheckResult(
            "FAIL", str(plan_path),
            f"{len(open_boxes)} open checkboxes remain"
        )
    return CheckResult("PASS", str(plan_path), "All checkboxes completed")


def check_test_count(oc_root: Path, expected_min: int = 129) -> CheckResult:
    """Check that STATE.md mentions test count >= expected minimum."""
    state_path = oc_root / "docs" / "ai" / "STATE.md"
    if not state_path.exists():
        return CheckResult("SKIP", "Test count", "STATE.md not found")

    content = state_path.read_text(encoding="utf-8", errors="replace")

    # "129 test", "130 tests", "129 unit" vb. pattern
    match = re.search(r"(\d+)\s*(?:unit|integration|test)",
                      content, re.IGNORECASE)
    if not match:
        return CheckResult("WARN", "Test count",
                           "No test count found in STATE.md")

    count = int(match.group(1))
    if count < expected_min:
        return CheckResult(
            "FAIL", "Test count",
            f"Test count {count} < expected minimum {expected_min}"
        )
    return CheckResult("PASS", "Test count",
                       f"{count} tests (>= {expected_min})")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_checks(
    oc_root: Path,
    sprint: int,
    sprint_date: datetime,
    check_filter: Optional[str] = None,
    verbose: bool = False,
) -> list[CheckResult]:
    results: list[CheckResult] = []

    # 1. Standard docs
    for rel_path, config in SPRINT_DOC_CONFIG.items():
        filepath = oc_root / rel_path

        if not filepath.exists():
            # DECISIONS, BACKLOG, PROTOCOL → SKIP eğer değişiklik yoksa
            if not config["freshness_required"]:
                results.append(CheckResult(
                    "SKIP", rel_path,
                    f"No changes expected — {config['description']}"))
                continue
            else:
                results.append(CheckResult("FAIL", rel_path, "File not found"))
                continue

        # Freshness check
        if config["freshness_required"] and (
                check_filter is None or check_filter == "freshness"):
            results.append(check_freshness(filepath, sprint_date))

        # Section check
        if config["required_sections"] and (
                check_filter is None or check_filter == "sections"):
            results.append(check_required_sections(
                filepath, config["required_sections"]))

    # 2. SESSION-HANDOFF
    if check_filter is None or check_filter in ("freshness", "sections"):
        results.extend(check_handoff(oc_root, sprint_date))

    # 3. capabilities.json
    if check_filter is None or check_filter == "capabilities":
        results.append(check_capabilities(oc_root))

    # 4. Sprint plan checkboxes
    if check_filter is None or check_filter == "checkboxes":
        results.append(check_open_checkboxes(oc_root, sprint))

    # 5. Test count
    if check_filter is None or check_filter == "tests":
        results.append(check_test_count(oc_root))

    return results


def print_results(results: list[CheckResult], sprint: int,
                  sprint_date: datetime,
                  verbose: bool = False):
    print(f"\n{'=' * 50}")
    print("  Sprint-End Doc Validation")
    print(f"  Sprint: {sprint}")
    print(f"  Date: {sprint_date.date()}")
    print(f"{'=' * 50}\n")

    fail_count = 0
    warn_count = 0

    for r in results:
        icon = {
            "PASS": "\033[32m[PASS]\033[0m",
            "FAIL": "\033[31m[FAIL]\033[0m",
            "WARN": "\033[33m[WARN]\033[0m",
            "SKIP": "\033[90m[SKIP]\033[0m",
        }.get(r.status, f"[{r.status}]")

        print(f"  {icon} {r.file} — {r.message}")
        if verbose and r.details:
            for d in r.details:
                print(f"         {d}")

        if r.status == "FAIL":
            fail_count += 1
        elif r.status == "WARN":
            warn_count += 1

    print()
    if fail_count > 0:
        print(f"\033[31m  Result: {fail_count} FAIL"
              f" — sprint NOT ready to close\033[0m")
    elif warn_count > 0:
        print(f"\033[33m  Result: 0 FAIL, {warn_count} WARN"
              f" — review warnings before close\033[0m")
    else:
        print("\033[32m  Result: All checks passed"
              " — sprint ready to close\033[0m")
    print()
    return fail_count


def main():
    parser = argparse.ArgumentParser(
        description="Sprint-End Documentation Validator")
    parser.add_argument("--sprint", type=int, required=True,
                        help="Sprint number")
    parser.add_argument("--sprint-date", type=str, default=None,
                        help="Sprint end date (YYYY-MM-DD). Default: today")
    parser.add_argument("--check", type=str, default=None,
                        choices=["freshness", "sections", "capabilities",
                                 "checkboxes", "tests"],
                        help="Run only specific check type")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")
    parser.add_argument("--oc-root", type=str, default=None,
                        help="Override OC_ROOT path")
    args = parser.parse_args()

    # Resolve root
    if args.oc_root:
        oc_root = Path(args.oc_root)
    else:
        oc_root = find_oc_root()

    # Resolve date
    if args.sprint_date:
        try:
            sprint_date = datetime.strptime(args.sprint_date, "%Y-%m-%d")
        except ValueError:
            print(f"[ERROR] Invalid date format: {args.sprint_date}. "
                  f"Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(2)
    else:
        sprint_date = datetime.now()

    # Run
    results = run_all_checks(oc_root, args.sprint, sprint_date,
                             args.check, args.verbose)
    fail_count = print_results(results, args.sprint, sprint_date, args.verbose)
    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
