"""Tests for Grafana dashboard pack — B-117."""
import json
import os
import sys
from pathlib import Path

# Add tools/ to path for grafana_setup import
ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, str(ROOT / "tools"))

from grafana_setup import (
    GRAFANA_DIR,
    export_dashboard,
    list_dashboards,
    validate_all,
    validate_dashboard,
)

# ── Dashboard file tests ─────────────────────────────────────

class TestDashboardFiles:
    """Validate that shipped dashboard JSON files are well-formed."""

    def test_grafana_dir_exists(self):
        assert GRAFANA_DIR.exists(), f"Grafana dir not found: {GRAFANA_DIR}"

    def test_at_least_three_dashboards(self):
        files = list(GRAFANA_DIR.glob("*.json"))
        assert len(files) >= 3, f"Expected >= 3 dashboards, found {len(files)}"

    def test_missions_dashboard_valid(self):
        path = GRAFANA_DIR / "vezir-missions.json"
        assert path.exists()
        errors = validate_dashboard(path)
        assert errors == [], f"Validation errors: {errors}"

    def test_policy_dashboard_valid(self):
        path = GRAFANA_DIR / "vezir-policy.json"
        assert path.exists()
        errors = validate_dashboard(path)
        assert errors == [], f"Validation errors: {errors}"

    def test_api_dashboard_valid(self):
        path = GRAFANA_DIR / "vezir-api.json"
        assert path.exists()
        errors = validate_dashboard(path)
        assert errors == [], f"Validation errors: {errors}"

    def test_all_dashboards_valid(self):
        results = validate_all()
        for filename, errors in results.items():
            assert errors == [], f"{filename}: {errors}"


# ── Dashboard content tests ──────────────────────────────────

class TestDashboardContent:
    def test_missions_has_panels(self):
        with open(GRAFANA_DIR / "vezir-missions.json") as f:
            data = json.load(f)
        panels = data["dashboard"]["panels"]
        assert len(panels) >= 4

    def test_policy_has_security_panels(self):
        with open(GRAFANA_DIR / "vezir-policy.json") as f:
            data = json.load(f)
        panels = data["dashboard"]["panels"]
        titles = [p["title"] for p in panels]
        assert any("Secret" in t or "Rotation" in t for t in titles)
        assert any("Allowlist" in t or "Denial" in t for t in titles)

    def test_api_has_latency_panel(self):
        with open(GRAFANA_DIR / "vezir-api.json") as f:
            data = json.load(f)
        panels = data["dashboard"]["panels"]
        titles = [p["title"] for p in panels]
        assert any("Latency" in t for t in titles)

    def test_unique_uids(self):
        uids = set()
        for path in GRAFANA_DIR.glob("*.json"):
            with open(path) as f:
                data = json.load(f)
            uid = data.get("dashboard", data).get("uid", "")
            assert uid not in uids, f"Duplicate UID: {uid}"
            uids.add(uid)

    def test_unique_panel_ids_per_dashboard(self):
        for path in GRAFANA_DIR.glob("*.json"):
            with open(path) as f:
                data = json.load(f)
            panels = data.get("dashboard", data).get("panels", [])
            ids = [p["id"] for p in panels]
            assert len(ids) == len(set(ids)), f"Duplicate panel IDs in {path.name}"

    def test_all_panels_have_targets(self):
        for path in GRAFANA_DIR.glob("*.json"):
            with open(path) as f:
                data = json.load(f)
            panels = data.get("dashboard", data).get("panels", [])
            for panel in panels:
                targets = panel.get("targets", [])
                assert len(targets) > 0, f"Panel '{panel['title']}' in {path.name} has no targets"

    def test_all_targets_have_expr(self):
        for path in GRAFANA_DIR.glob("*.json"):
            with open(path) as f:
                data = json.load(f)
            panels = data.get("dashboard", data).get("panels", [])
            for panel in panels:
                for target in panel.get("targets", []):
                    assert "expr" in target, f"Target in '{panel['title']}' missing expr"


# ── Validation logic tests ───────────────────────────────────

class TestValidation:
    def test_valid_minimal_dashboard(self, tmp_path):
        data = {
            "dashboard": {
                "uid": "test",
                "title": "Test",
                "panels": [{
                    "id": 1, "title": "P1", "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
                    "targets": [{"expr": "up"}]
                }]
            }
        }
        path = tmp_path / "test.json"
        with open(path, "w") as f:
            json.dump(data, f)
        assert validate_dashboard(path) == []

    def test_missing_uid(self, tmp_path):
        data = {"dashboard": {"title": "Test", "panels": []}}
        path = tmp_path / "bad.json"
        with open(path, "w") as f:
            json.dump(data, f)
        errors = validate_dashboard(path)
        assert any("uid" in e for e in errors)

    def test_empty_panels(self, tmp_path):
        data = {"dashboard": {"uid": "x", "title": "X", "panels": []}}
        path = tmp_path / "empty.json"
        with open(path, "w") as f:
            json.dump(data, f)
        errors = validate_dashboard(path)
        assert any("no panels" in e for e in errors)

    def test_duplicate_panel_ids(self, tmp_path):
        data = {
            "dashboard": {
                "uid": "dup", "title": "Dup", "panels": [
                    {"id": 1, "title": "A", "type": "stat",
                     "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
                     "targets": [{"expr": "up"}]},
                    {"id": 1, "title": "B", "type": "stat",
                     "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0},
                     "targets": [{"expr": "up"}]},
                ]
            }
        }
        path = tmp_path / "dup.json"
        with open(path, "w") as f:
            json.dump(data, f)
        errors = validate_dashboard(path)
        assert any("duplicate" in e for e in errors)

    def test_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        with open(path, "w") as f:
            f.write("not json")
        errors = validate_dashboard(path)
        assert any("Invalid JSON" in e for e in errors)

    def test_unknown_panel_type(self, tmp_path):
        data = {
            "dashboard": {
                "uid": "t", "title": "T", "panels": [{
                    "id": 1, "title": "P", "type": "banana",
                    "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
                    "targets": [{"expr": "up"}]
                }]
            }
        }
        path = tmp_path / "bad_type.json"
        with open(path, "w") as f:
            json.dump(data, f)
        errors = validate_dashboard(path)
        assert any("unknown type" in e for e in errors)


# ── List and export tests ────────────────────────────────────

class TestListExport:
    def test_list_dashboards(self):
        result = list_dashboards()
        assert len(result) >= 3
        assert all("uid" in d for d in result)

    def test_export_existing(self):
        data = export_dashboard("vezir-missions")
        assert data is not None
        assert "dashboard" in data

    def test_export_with_prefix(self):
        data = export_dashboard("missions")
        assert data is not None

    def test_export_nonexistent(self):
        data = export_dashboard("nonexistent-dashboard-xyz")
        assert data is None


# ── Metrics API tests ────────────────────────────────────────

class TestMetricsAPI:
    def test_metrics_endpoint_returns_text(self):
        from api.metrics_api import _collect_metrics
        result = _collect_metrics()
        assert isinstance(result, str)
        assert "vezir_missions_active" in result

    def test_metrics_contains_help_lines(self):
        from api.metrics_api import _collect_metrics
        result = _collect_metrics()
        assert "# HELP" in result
        assert "# TYPE" in result

    def test_metrics_json_format(self):
        from api.metrics_api import metrics_json
        result = metrics_json()
        assert "missions" in result
        assert "timestamp" in result
        assert "total" in result["missions"]
