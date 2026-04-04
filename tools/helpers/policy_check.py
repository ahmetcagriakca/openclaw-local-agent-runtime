"""Sprint policy checker — extracted from sprint-finalize.sh heredoc.

Sprint 55 Task 55.3 (B-025): Heredoc reduction.
Usage:
    python tools/helpers/policy_check.py <policy_file> <sprint_number> forced_model
    python tools/helpers/policy_check.py <policy_file> <sprint_number> reason
"""
import re
import sys


def check_policy(policy_file: str, sprint: str, field: str) -> str | None:
    """Check sprint policy for a specific field.

    Args:
        policy_file: Path to sprint-policy.yml
        sprint: Sprint number (e.g., "55")
        field: "forced_model" or "reason"

    Returns:
        Field value if found, None otherwise.
    """
    try:
        with open(policy_file, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, IOError):
        return None

    pattern = rf'^\s+{sprint}:\s*\n((?:\s{{4,}}[^\n]+\n?)*)'
    block = re.search(pattern, content, re.MULTILINE)
    if not block:
        return None

    if field == "forced_model":
        m = re.search(r'forced_model:\s*"([AB])"', block.group(1))
        return m.group(1) if m else None
    elif field == "reason":
        m = re.search(r'reason:\s*"([^"]+)"', block.group(1))
        return m.group(1) if m else None
    return None


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <policy_file> <sprint> <field>",
              file=sys.stderr)
        sys.exit(1)

    result = check_policy(sys.argv[1], sys.argv[2], sys.argv[3])
    if result:
        print(result)
