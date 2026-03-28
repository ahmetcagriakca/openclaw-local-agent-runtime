#!/usr/bin/env python3
"""Compare benchmark results against baseline for regression detection.

Usage:
  python tools/benchmark_compare.py                          # uses default baseline
  python tools/benchmark_compare.py baseline.json new.json   # explicit files
  python tools/benchmark_compare.py --threshold 30           # custom threshold %

Exit codes:
  0 = no regression
  1 = regression detected
  2 = error (missing files, parse error)
"""
import json
import sys
from pathlib import Path

DEFAULT_BASELINE = Path(__file__).resolve().parent.parent / "baseline" / "benchmark-baseline.json"
DEFAULT_THRESHOLD_PCT = 25  # ±25% median tolerance


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compare(baseline: dict, current: dict, threshold_pct: float) -> tuple[bool, list[str]]:
    """Compare current results against baseline. Returns (passed, messages)."""
    messages = []
    regressions = []

    base_endpoints = baseline.get("endpoints", {})
    curr_endpoints = current.get("endpoints", {})

    for endpoint, base_metrics in base_endpoints.items():
        if endpoint not in curr_endpoints:
            messages.append(f"  SKIP: {endpoint} — not in current run")
            continue

        base_median = base_metrics.get("median_ms", 0)
        curr_median = curr_endpoints[endpoint].get("median_ms", 0)

        if base_median == 0:
            messages.append(f"  SKIP: {endpoint} — baseline median is 0")
            continue

        change_pct = ((curr_median - base_median) / base_median) * 100
        status = "OK" if change_pct <= threshold_pct else "REGRESSION"

        msg = f"  {status}: {endpoint} — baseline={base_median:.1f}ms current={curr_median:.1f}ms ({change_pct:+.1f}%)"
        messages.append(msg)

        if status == "REGRESSION":
            regressions.append(endpoint)

    passed = len(regressions) == 0
    return passed, messages


def main():
    args = sys.argv[1:]
    threshold = DEFAULT_THRESHOLD_PCT

    # Parse --threshold flag
    if "--threshold" in args:
        idx = args.index("--threshold")
        threshold = float(args[idx + 1])
        args = args[:idx] + args[idx + 2:]

    # Determine file paths
    if len(args) == 0:
        baseline_path = DEFAULT_BASELINE
        current_path = DEFAULT_BASELINE  # self-compare (should always pass)
        print("NOTE: Self-comparing baseline (no new run provided). This should always pass.")
    elif len(args) == 1:
        baseline_path = DEFAULT_BASELINE
        current_path = Path(args[0])
    elif len(args) == 2:
        baseline_path = Path(args[0])
        current_path = Path(args[1])
    else:
        print("Usage: python tools/benchmark_compare.py [baseline.json] [current.json] [--threshold N]")
        sys.exit(2)

    if not baseline_path.exists():
        print(f"ERROR: Baseline not found: {baseline_path}")
        sys.exit(2)
    if not current_path.exists():
        print(f"ERROR: Current results not found: {current_path}")
        sys.exit(2)

    baseline = load_json(baseline_path)
    current = load_json(current_path)

    print("=" * 60)
    print("  Benchmark Regression Check")
    print(f"  Baseline: {baseline_path}")
    print(f"  Current:  {current_path}")
    print(f"  Threshold: ±{threshold}%")
    print(f"  Baseline generated: {baseline.get('generated', 'unknown')}")
    print("=" * 60)

    passed, messages = compare(baseline, current, threshold)

    for msg in messages:
        print(msg)

    print()
    if passed:
        print("PASS: No performance regressions detected.")
        sys.exit(0)
    else:
        print("FAIL: Performance regression detected!")
        sys.exit(1)


if __name__ == "__main__":
    main()
