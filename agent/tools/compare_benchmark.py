"""Compare benchmark results against baseline.

Sprint 16 Task 16.15: Fail if any endpoint regressed > threshold%.
Usage: python compare_benchmark.py baseline.json current.json --threshold 10
"""
import json
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Compare benchmark results")
    parser.add_argument("baseline", help="Baseline benchmark JSON file")
    parser.add_argument("current", help="Current benchmark JSON file")
    parser.add_argument("--threshold", type=float, default=10.0,
                        help="Regression threshold percentage (default: 10)")
    args = parser.parse_args()

    try:
        with open(args.baseline) as f:
            baseline = json.load(f)
        with open(args.current) as f:
            current = json.load(f)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        sys.exit(1)

    regressions = []
    print(f"Comparing benchmarks (threshold: {args.threshold}%)")
    print("=" * 60)

    baseline_results = baseline.get("results", baseline)
    current_results = current.get("results", current)

    for endpoint, b_data in baseline_results.items():
        c_data = current_results.get(endpoint)
        if not c_data:
            continue

        b_avg = b_data.get("avg_ms", b_data.get("avg", 0))
        c_avg = c_data.get("avg_ms", c_data.get("avg", 0))

        if b_avg <= 0:
            continue

        change_pct = ((c_avg - b_avg) / b_avg) * 100
        status = "OK" if change_pct <= args.threshold else "REGRESSED"

        print(f"  {endpoint:40s} {b_avg:6.1f}ms → {c_avg:6.1f}ms ({change_pct:+.1f}%) {status}")

        if change_pct > args.threshold:
            regressions.append({
                "endpoint": endpoint,
                "baseline": b_avg,
                "current": c_avg,
                "change_pct": change_pct,
            })

    print("=" * 60)

    if regressions:
        print(f"\nFAILED: {len(regressions)} endpoint(s) regressed > {args.threshold}%:")
        for r in regressions:
            print(f"  - {r['endpoint']}: {r['change_pct']:+.1f}%")
        sys.exit(1)
    else:
        print("\nPASSED: No regressions detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
