"""Grafana dashboard provisioning tool — B-117.

Validates and deploys Grafana dashboard JSON files.
Usage: python tools/grafana_setup.py [--validate] [--list] [--export <name>]
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("grafana_setup")

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GRAFANA_DIR = ROOT / "config" / "grafana"

REQUIRED_DASHBOARD_FIELDS = ["uid", "title", "panels"]
REQUIRED_PANEL_FIELDS = ["id", "title", "type", "gridPos", "targets"]
VALID_PANEL_TYPES = [
    "timeseries", "stat", "piechart", "bargauge", "table",
    "gauge", "heatmap", "barchart", "text", "row",
]


def list_dashboards() -> list[dict]:
    """List all available dashboard definitions."""
    dashboards = []
    if not GRAFANA_DIR.exists():
        return dashboards

    for path in sorted(GRAFANA_DIR.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            db = data.get("dashboard", data)
            dashboards.append({
                "file": path.name,
                "uid": db.get("uid", ""),
                "title": db.get("title", ""),
                "panels": len(db.get("panels", [])),
                "tags": db.get("tags", []),
            })
        except (json.JSONDecodeError, OSError) as e:
            dashboards.append({"file": path.name, "error": str(e)})

    return dashboards


def validate_dashboard(path: Path) -> list[str]:
    """Validate a dashboard JSON file. Returns list of errors (empty = valid)."""
    errors = []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except OSError as e:
        return [f"Cannot read file: {e}"]

    # Unwrap envelope if present
    dashboard = data.get("dashboard", data)

    # Required fields
    for field in REQUIRED_DASHBOARD_FIELDS:
        if field not in dashboard:
            errors.append(f"Missing required field: {field}")

    # Validate panels
    panels = dashboard.get("panels", [])
    if not isinstance(panels, list):
        errors.append("panels must be a list")
        return errors

    if len(panels) == 0:
        errors.append("Dashboard has no panels")

    panel_ids = set()
    for i, panel in enumerate(panels):
        prefix = f"Panel {i+1}"

        # Check required fields
        for field in REQUIRED_PANEL_FIELDS:
            if field not in panel:
                errors.append(f"{prefix}: missing '{field}'")

        # Check panel type
        ptype = panel.get("type", "")
        if ptype and ptype not in VALID_PANEL_TYPES:
            errors.append(f"{prefix}: unknown type '{ptype}'")

        # Check duplicate IDs
        pid = panel.get("id")
        if pid is not None:
            if pid in panel_ids:
                errors.append(f"{prefix}: duplicate id {pid}")
            panel_ids.add(pid)

        # Check gridPos
        grid = panel.get("gridPos", {})
        for dim in ["h", "w", "x", "y"]:
            if dim not in grid:
                errors.append(f"{prefix}: gridPos missing '{dim}'")

        # Check targets
        targets = panel.get("targets", [])
        if isinstance(targets, list):
            for j, target in enumerate(targets):
                if "expr" not in target:
                    errors.append(f"{prefix} target {j+1}: missing 'expr'")

    return errors


def validate_all() -> dict:
    """Validate all dashboard files. Returns {file: errors} dict."""
    results = {}
    if not GRAFANA_DIR.exists():
        return {"error": "Grafana directory not found"}

    for path in sorted(GRAFANA_DIR.glob("*.json")):
        errors = validate_dashboard(path)
        results[path.name] = errors

    return results


def export_dashboard(name: str) -> dict | None:
    """Export a specific dashboard definition."""
    path = GRAFANA_DIR / f"{name}.json"
    if not path.exists():
        # Try without vezir- prefix
        path = GRAFANA_DIR / f"vezir-{name}.json"
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Grafana dashboard provisioning tool")
    parser.add_argument("--validate", action="store_true", help="Validate all dashboards")
    parser.add_argument("--list", action="store_true", help="List available dashboards")
    parser.add_argument("--export", type=str, help="Export a specific dashboard")
    args = parser.parse_args()

    if args.list:
        dashboards = list_dashboards()
        if not dashboards:
            print("No dashboards found")
            return
        for db in dashboards:
            if "error" in db:
                print(f"  {db['file']}: ERROR - {db['error']}")
            else:
                print(f"  {db['uid']:20s} | {db['title']:40s} | {db['panels']} panels | {db['tags']}")
        return

    if args.validate:
        results = validate_all()
        all_valid = True
        for filename, errors in results.items():
            if errors:
                print(f"FAIL {filename}:")
                for e in errors:
                    print(f"  - {e}")
                all_valid = False
            else:
                print(f"OK   {filename}")
        sys.exit(0 if all_valid else 1)

    if args.export:
        data = export_dashboard(args.export)
        if data is None:
            print(f"Dashboard '{args.export}' not found")
            sys.exit(1)
        print(json.dumps(data, indent=2))
        return

    # Default: validate
    results = validate_all()
    for filename, errors in results.items():
        status = "OK" if not errors else f"FAIL ({len(errors)} errors)"
        print(f"  {filename}: {status}")


if __name__ == "__main__":
    main()
