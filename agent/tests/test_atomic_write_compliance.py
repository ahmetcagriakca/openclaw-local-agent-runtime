"""Guard test: ensure no non-atomic JSON writes exist in agent/ source files.

D-071 requires all JSON file writes to use atomic_write_json() (temp -> fsync -> os.replace).
This test greps agent/ Python files (excluding tests/) for plain open()+json.dump() patterns
and asserts zero matches, preventing future regressions.
"""
import os
import re

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Pattern: open(..., "w"...) followed by json.dump() — the non-atomic write pattern.
# We search for files that contain both patterns in close proximity.
NON_ATOMIC_PATTERN = re.compile(
    r'open\s*\([^)]*["\']w["\']',
    re.MULTILINE,
)

JSON_DUMP_PATTERN = re.compile(
    r'json\.dump\s*\(',
    re.MULTILINE,
)

# Directories and files to exclude from the scan
EXCLUDED_DIRS = {"tests", "__pycache__", ".git", "node_modules"}
EXCLUDED_FILES = {"atomic_write.py"}

# Pre-existing violations to be fixed in future sprints.
# TODO: Remove entries as each file is migrated to atomic_write_json.
KNOWN_EXCEPTIONS = {
    os.path.normpath("mission/controller.py"),
    os.path.normpath("services/secret_store.py"),
}


def _collect_python_files():
    """Collect all .py files under agent/ excluding tests/ and __pycache__."""
    py_files = []
    for root, dirs, files in os.walk(AGENT_DIR):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for fname in files:
            if fname.endswith(".py") and fname not in EXCLUDED_FILES:
                py_files.append(os.path.join(root, fname))
    return py_files


def _find_non_atomic_writes(filepath):
    """Find lines in a file that use open(..., 'w') near json.dump().

    Returns list of (line_number, line_text) tuples for violations.
    """
    violations = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return violations

    # Quick check: file must contain both patterns to be a candidate
    if not NON_ATOMIC_PATTERN.search(content) or not JSON_DUMP_PATTERN.search(content):
        return violations

    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        # Look for json.dump() calls that are NOT using atomic_write_json
        # The violation pattern: a json.dump() call with a file handle from open()
        if JSON_DUMP_PATTERN.search(line):
            # Check surrounding context (5 lines before) for open(..., "w")
            context_start = max(0, i - 6)
            context = "\n".join(lines[context_start:i])
            if NON_ATOMIC_PATTERN.search(context):
                rel_path = os.path.relpath(filepath, AGENT_DIR)
                violations.append((rel_path, i, line.strip()))

    return violations


def test_no_non_atomic_json_writes():
    """Assert that no agent/ source files use plain open()+json.dump().

    All JSON writes must use atomic_write_json() from utils.atomic_write.
    This enforces decision D-071.
    """
    py_files = _collect_python_files()
    assert py_files, "No Python files found — test setup error"

    all_violations = []
    for filepath in py_files:
        rel = os.path.relpath(filepath, AGENT_DIR)
        if os.path.normpath(rel) in KNOWN_EXCEPTIONS:
            continue
        violations = _find_non_atomic_writes(filepath)
        all_violations.extend(violations)

    if all_violations:
        msg_lines = [
            f"D-071 VIOLATION: {len(all_violations)} non-atomic JSON write(s) found:",
        ]
        for rel_path, line_no, line_text in all_violations:
            msg_lines.append(f"  {rel_path}:{line_no}: {line_text}")
        msg_lines.append(
            "\nFix: Replace open()+json.dump() with atomic_write_json() "
            "from utils.atomic_write"
        )
        raise AssertionError("\n".join(msg_lines))
