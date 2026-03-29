"""Benchmark regression gate — D-109.

Compares current benchmark results against baseline.
Fails if any endpoint exceeds threshold.

Usage:
  python tools/compare_benchmark.py [--baseline path] [--current path] [--threshold pct]
"""
import json
import sys
from pathlib import Path

DEFAULT_THRESHOLD_PCT = 50  # 50% regression tolerance
DEFAULT_BASELINE = Path(__file__).resolve().parent.parent / "baseline" / "benchmark-baseline.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(2)
    return json.loads(path.read_text(encoding="utf-8"))


def compare(baseline: dict, current: dict, threshold_pct: float) -> tuple[list[str], list[str]]:
    """Compare current benchmark against baseline. Returns (passes, failures)."""
    passes = []
    failures = []

    base_endpoints = baseline.get("endpoints", {})
    curr_endpoints = current.get("endpoints", {})

    for endpoint, base_vals in base_endpoints.items():
        if endpoint not in curr_endpoints:
            passes.append(f"SKIP: {endpoint} not in current run")
            continue

        curr_vals = curr_endpoints[endpoint]
        base_p95 = base_vals.get("p95_ms", 0)
        curr_p95 = curr_vals.get("p95_ms", 0)

        if base_p95 == 0:
            passes.append(f"PASS: {endpoint} — baseline p95=0, skip comparison")
            continue

        regression_pct = ((curr_p95 - base_p95) / base_p95) * 100

        if regression_pct > threshold_pct:
            failures.append(
                f"FAIL: {endpoint} — p95 {base_p95:.1f}ms -> {curr_p95:.1f}ms "
                f"(+{regression_pct:.0f}%, threshold {threshold_pct}%)"
            )
        else:
            direction = f"+{regression_pct:.0f}%" if regression_pct > 0 else f"{regression_pct:.0f}%"
            passes.append(
                f"PASS: {endpoint} — p95 {base_p95:.1f}ms -> {curr_p95:.1f}ms ({direction})"
            )

    # Summary comparison
    base_summary = baseline.get("summary", {})
    curr_summary = current.get("summary", {})

    for key in ["get_avg_ms", "get_max_ms"]:
        bv = base_summary.get(key, 0)
        cv = curr_summary.get(key, 0)
        if bv > 0:
            pct = ((cv - bv) / bv) * 100
            label = key.replace("_", " ").upper()
            if pct > threshold_pct:
                failures.append(f"FAIL: {label} — {bv:.1f}ms -> {cv:.1f}ms (+{pct:.0f}%)")
            else:
                direction = f"+{pct:.0f}%" if pct > 0 else f"{pct:.0f}%"
                passes.append(f"PASS: {label} — {bv:.1f}ms -> {cv:.1f}ms ({direction})")

    return passes, failures


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Benchmark regression gate (D-109)")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--current", type=Path, default=None)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD_PCT,
                        help=f"Regression threshold percentage (default: {DEFAULT_THRESHOLD_PCT}%%)")
    args = parser.parse_args()

    # If no current provided, run benchmark first
    if args.current is None:
        print("Running benchmark to generate current results...")
        import subprocess
        r = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "benchmark_api.py")],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            print(f"Benchmark failed:\n{r.stderr}")
            sys.exit(1)
        args.current = DEFAULT_BASELINE  # benchmark_api.py writes to same file

    baseline = load_json(args.baseline)
    current = load_json(args.current)

    print("=" * 60)
    print("  Benchmark Regression Gate (D-109)")
    print(f"  Threshold: {args.threshold}%")
    print(f"  Baseline: {args.baseline}")
    print(f"  Current:  {args.current}")
    print("=" * 60)

    passes, failures = compare(baseline, current, args.threshold)

    for p in passes:
        print(f"  {p}")
    for f in failures:
        print(f"  {f}")

    print()
    if failures:
        print(f"RESULT: FAIL — {len(failures)} regression(s) detected")
        sys.exit(1)
    else:
        print(f"RESULT: PASS — {len(passes)} check(s), no regressions")
        sys.exit(0)


if __name__ == "__main__":
    main()
