"""Contract check — validate OpenAPI spec against baseline for breaking changes.

Sprint 51 Task 51.1 (B-110): Detect schema drift and breaking changes.
Usage: python tools/contract_check.py [--update-baseline]
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OC_ROOT = SCRIPT_DIR.parent
SPEC_PATH = OC_ROOT / "docs" / "api" / "openapi.json"
BASELINE_PATH = OC_ROOT / "docs" / "api" / "openapi-baseline.json"


def load_spec(path: Path) -> dict:
    """Load an OpenAPI spec from file."""
    if not path.exists():
        print(f"ERROR: Spec not found at {path}")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def extract_endpoints(spec: dict) -> dict[str, dict]:
    """Extract endpoint signatures: path+method -> {params, response_schema}."""
    endpoints = {}
    for path, methods in spec.get("paths", {}).items():
        for method, detail in methods.items():
            if method in ("get", "post", "put", "delete", "patch"):
                key = f"{method.upper()} {path}"
                params = []
                for p in detail.get("parameters", []):
                    params.append({
                        "name": p.get("name"),
                        "in": p.get("in"),
                        "required": p.get("required", False),
                    })
                resp_200 = detail.get("responses", {}).get("200", {})
                resp_schema = None
                if "content" in resp_200:
                    json_content = resp_200["content"].get("application/json", {})
                    resp_schema = json_content.get("schema")
                endpoints[key] = {
                    "params": params,
                    "response_schema": resp_schema,
                    "tags": detail.get("tags", []),
                }
    return endpoints


def check_breaking_changes(baseline: dict, current: dict) -> list[str]:
    """Compare baseline vs current spec for breaking changes.

    Breaking changes:
    - Removed endpoints
    - Removed required parameters
    - Changed response schema refs
    """
    issues = []
    baseline_eps = extract_endpoints(baseline)
    current_eps = extract_endpoints(current)

    # Check for removed endpoints
    for ep in baseline_eps:
        if ep not in current_eps:
            issues.append(f"BREAKING: Endpoint removed: {ep}")

    # Check for parameter changes in existing endpoints
    for ep, baseline_detail in baseline_eps.items():
        if ep not in current_eps:
            continue
        current_detail = current_eps[ep]

        # Check required params not removed
        baseline_required = {
            p["name"] for p in baseline_detail["params"] if p.get("required")
        }
        current_params = {p["name"] for p in current_detail["params"]}
        for param in baseline_required:
            if param not in current_params:
                issues.append(f"BREAKING: Required param '{param}' removed from {ep}")

        # Check response schema ref changes
        b_schema = baseline_detail.get("response_schema")
        c_schema = current_detail.get("response_schema")
        if b_schema and c_schema:
            b_ref = b_schema.get("$ref", "")
            c_ref = c_schema.get("$ref", "")
            if b_ref and c_ref and b_ref != c_ref:
                issues.append(
                    f"BREAKING: Response schema changed for {ep}: "
                    f"{b_ref} -> {c_ref}"
                )

    # Check for new endpoints (informational)
    new_eps = set(current_eps) - set(baseline_eps)
    if new_eps:
        for ep in sorted(new_eps):
            print(f"  INFO: New endpoint: {ep}")

    return issues


def update_baseline():
    """Copy current spec as new baseline."""
    if not SPEC_PATH.exists():
        print("ERROR: Current spec not found. Run tools/export_openapi.py first.")
        sys.exit(1)
    spec = SPEC_PATH.read_text(encoding="utf-8")
    BASELINE_PATH.write_text(spec, encoding="utf-8")
    print(f"Baseline updated: {BASELINE_PATH}")


def main():
    if "--update-baseline" in sys.argv:
        update_baseline()
        return

    if not BASELINE_PATH.exists():
        print("No baseline found. Creating initial baseline...")
        update_baseline()
        print("Baseline created. Run again to check for changes.")
        return

    baseline = load_spec(BASELINE_PATH)
    current = load_spec(SPEC_PATH)

    print("Contract Check: OpenAPI Breaking Change Detection")
    print(f"  Baseline: {BASELINE_PATH}")
    print(f"  Current:  {SPEC_PATH}")
    print()

    baseline_eps = extract_endpoints(baseline)
    current_eps = extract_endpoints(current)
    print(f"  Baseline endpoints: {len(baseline_eps)}")
    print(f"  Current endpoints:  {len(current_eps)}")
    print()

    issues = check_breaking_changes(baseline, current)

    if issues:
        print(f"FAIL: {len(issues)} breaking change(s) detected:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("PASS: No breaking changes detected.")


if __name__ == "__main__":
    main()
