"""Tests for PluginMarketplaceStore — Sprint 59 Task 59.1."""
from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

import pytest

from services.plugin_marketplace import PluginEntry, PluginMarketplaceStore, _VALID_TRANSITIONS


# -- Fixtures --

def _make_manifest(name: str, version: str = "1.0.0", **extra) -> dict:
    base = {
        "name": name,
        "version": version,
        "description": f"{name} plugin",
        "author": "test",
    }
    base.update(extra)
    return base


@pytest.fixture
def tmp_env(tmp_path):
    """Create temp plugins dir and store path."""
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    store_path = tmp_path / "marketplace.json"
    return plugins_dir, store_path


@pytest.fixture
def store_with_plugins(tmp_env):
    """Store with 3 valid plugins and 1 invalid."""
    plugins_dir, store_path = tmp_env

    # Valid plugin: alpha
    alpha = plugins_dir / "alpha"
    alpha.mkdir()
    (alpha / "manifest.json").write_text(json.dumps(_make_manifest(
        "Alpha", capabilities=["logging"], risk_tier="low",
        trust_status="trusted", category="monitoring", tags=["log", "trace"],
    )))

    # Valid plugin: beta
    beta = plugins_dir / "beta"
    beta.mkdir()
    (beta / "manifest.json").write_text(json.dumps(_make_manifest(
        "Beta", version="2.0.0", capabilities=["auth"],
        risk_tier="medium", category="security", tags=["auth"],
    )))

    # Valid plugin: gamma
    gamma = plugins_dir / "gamma"
    gamma.mkdir()
    (gamma / "manifest.json").write_text(json.dumps(_make_manifest(
        "Gamma", category="general",
    )))

    # Invalid plugin: broken
    broken = plugins_dir / "broken"
    broken.mkdir()
    (broken / "manifest.json").write_text("not valid json{{{")

    store = PluginMarketplaceStore(store_path=store_path, plugins_dir=plugins_dir)
    store.discover_and_index()
    return store


# -- Discovery Tests --

class TestDiscovery:
    def test_discover_empty_dir(self, tmp_env):
        plugins_dir, store_path = tmp_env
        store = PluginMarketplaceStore(store_path=store_path, plugins_dir=plugins_dir)
        count = store.discover_and_index()
        assert count == 0
        assert store.list_all() == []

    def test_discover_nonexistent_dir(self, tmp_path):
        store = PluginMarketplaceStore(
            store_path=tmp_path / "s.json",
            plugins_dir=tmp_path / "nonexistent",
        )
        count = store.discover_and_index()
        assert count == 0

    def test_discover_valid_plugins(self, store_with_plugins):
        store = store_with_plugins
        entries = store.list_all()
        assert len(entries) == 4  # 3 valid + 1 invalid

    def test_discover_invalid_manifest(self, store_with_plugins):
        store = store_with_plugins
        broken = store.get("broken")
        assert broken is not None
        assert broken.risk_tier == "high"
        assert broken.trust_status == "unknown"
        assert broken.version == "0.0.0"

    def test_discover_preserves_status(self, tmp_env):
        plugins_dir, store_path = tmp_env
        p = plugins_dir / "test_plugin"
        p.mkdir()
        (p / "manifest.json").write_text(json.dumps(_make_manifest("Test")))

        store = PluginMarketplaceStore(store_path=store_path, plugins_dir=plugins_dir)
        store.discover_and_index()
        store.update_status("test_plugin", "installed")
        store.discover_and_index()  # re-discover

        entry = store.get("test_plugin")
        assert entry.status == "installed"  # status preserved

    def test_discover_reads_extended_metadata(self, store_with_plugins):
        alpha = store_with_plugins.get("alpha")
        assert alpha.capabilities == ["logging"]
        assert alpha.risk_tier == "low"
        assert alpha.trust_status == "trusted"
        assert alpha.category == "monitoring"
        assert alpha.tags == ["log", "trace"]


# -- CRUD Tests --

class TestCRUD:
    def test_get_existing(self, store_with_plugins):
        entry = store_with_plugins.get("alpha")
        assert entry is not None
        assert entry.name == "Alpha"

    def test_get_nonexistent(self, store_with_plugins):
        assert store_with_plugins.get("nonexistent") is None

    def test_list_all(self, store_with_plugins):
        entries = store_with_plugins.list_all()
        assert len(entries) == 4
        names = {e.plugin_id for e in entries}
        assert names == {"alpha", "beta", "gamma", "broken"}

    def test_plugin_entry_fields(self, store_with_plugins):
        beta = store_with_plugins.get("beta")
        assert beta.name == "Beta"
        assert beta.version == "2.0.0"
        assert beta.description == "Beta plugin"
        assert beta.author == "test"
        assert beta.status == "available"
        assert beta.source == "local"


# -- Status Transition Tests --

class TestStatusTransitions:
    def test_available_to_installed(self, store_with_plugins):
        assert store_with_plugins.update_status("alpha", "installed")
        assert store_with_plugins.get("alpha").status == "installed"

    def test_installed_to_enabled(self, store_with_plugins):
        store_with_plugins.update_status("alpha", "installed")
        assert store_with_plugins.update_status("alpha", "enabled")
        assert store_with_plugins.get("alpha").status == "enabled"

    def test_enabled_to_disabled(self, store_with_plugins):
        store_with_plugins.update_status("alpha", "installed")
        store_with_plugins.update_status("alpha", "enabled")
        assert store_with_plugins.update_status("alpha", "disabled")
        assert store_with_plugins.get("alpha").status == "disabled"

    def test_disabled_to_enabled(self, store_with_plugins):
        store_with_plugins.update_status("alpha", "installed")
        store_with_plugins.update_status("alpha", "disabled")
        assert store_with_plugins.update_status("alpha", "enabled")

    def test_uninstall_resets_to_available(self, store_with_plugins):
        store_with_plugins.update_status("alpha", "installed")
        assert store_with_plugins.update_status("alpha", "available")
        entry = store_with_plugins.get("alpha")
        assert entry.status == "available"
        assert entry.installed_at is None

    def test_invalid_transition_rejected(self, store_with_plugins):
        # available → enabled is not valid
        assert not store_with_plugins.update_status("alpha", "enabled")
        assert store_with_plugins.get("alpha").status == "available"

    def test_status_nonexistent_plugin(self, store_with_plugins):
        assert not store_with_plugins.update_status("nonexistent", "installed")

    def test_installed_at_set(self, store_with_plugins):
        store_with_plugins.update_status("alpha", "installed")
        entry = store_with_plugins.get("alpha")
        assert entry.installed_at is not None


# -- Search & Filter Tests --

class TestSearchFilter:
    def test_search_by_name(self, store_with_plugins):
        results = store_with_plugins.search("alpha")
        assert len(results) == 1
        assert results[0].name == "Alpha"

    def test_search_by_description(self, store_with_plugins):
        results = store_with_plugins.search("plugin")
        assert len(results) >= 3  # all valid plugins have "X plugin" desc

    def test_search_case_insensitive(self, store_with_plugins):
        results = store_with_plugins.search("ALPHA")
        assert len(results) == 1

    def test_search_no_results(self, store_with_plugins):
        results = store_with_plugins.search("nonexistent_query")
        assert results == []

    def test_filter_by_status(self, store_with_plugins):
        results = store_with_plugins.filter_by_status("available")
        assert len(results) == 4  # all start as available

    def test_filter_by_category(self, store_with_plugins):
        results = store_with_plugins.filter_by_category("monitoring")
        assert len(results) == 1
        assert results[0].plugin_id == "alpha"

    def test_filter_by_tag(self, store_with_plugins):
        results = store_with_plugins.filter_by_tag("auth")
        assert len(results) == 1
        assert results[0].plugin_id == "beta"

    def test_combined_filter(self, store_with_plugins):
        results = store_with_plugins.filter(category="security")
        assert len(results) == 1
        assert results[0].plugin_id == "beta"

    def test_combined_filter_status_and_query(self, store_with_plugins):
        results = store_with_plugins.filter(status="available", query="Alpha")
        assert len(results) == 1


# -- Persistence Tests --

class TestPersistence:
    def test_save_and_reload(self, tmp_env):
        plugins_dir, store_path = tmp_env
        p = plugins_dir / "persist_test"
        p.mkdir()
        (p / "manifest.json").write_text(json.dumps(_make_manifest("PersistTest")))

        store1 = PluginMarketplaceStore(store_path=store_path, plugins_dir=plugins_dir)
        store1.discover_and_index()
        store1.update_status("persist_test", "installed")

        # Reload from disk
        store2 = PluginMarketplaceStore(store_path=store_path, plugins_dir=plugins_dir)
        entry = store2.get("persist_test")
        assert entry is not None
        assert entry.status == "installed"

    def test_store_file_created(self, tmp_env):
        plugins_dir, store_path = tmp_env
        p = plugins_dir / "file_test"
        p.mkdir()
        (p / "manifest.json").write_text(json.dumps(_make_manifest("FileTest")))

        store = PluginMarketplaceStore(store_path=store_path, plugins_dir=plugins_dir)
        store.discover_and_index()
        assert store_path.exists()


# -- Stats & Events Tests --

class TestStatsEvents:
    def test_stats_initial(self, store_with_plugins):
        s = store_with_plugins.stats()
        assert s["total"] == 4
        assert s["available"] == 4
        assert s["installed"] == 0

    def test_stats_after_install(self, store_with_plugins):
        store_with_plugins.update_status("alpha", "installed")
        s = store_with_plugins.stats()
        assert s["available"] == 3
        assert s["installed"] == 1

    def test_stats_by_category(self, store_with_plugins):
        s = store_with_plugins.stats()
        assert "monitoring" in s["by_category"]
        assert "security" in s["by_category"]

    def test_events_logged(self, store_with_plugins):
        events = store_with_plugins.events()
        assert len(events) > 0  # discover events logged

    def test_events_after_status_change(self, store_with_plugins):
        store_with_plugins.update_status("alpha", "installed")
        events = store_with_plugins.events()
        status_events = [e for e in events if e["action"] == "status_change"]
        assert len(status_events) == 1
        assert "available → installed" in status_events[0]["detail"]

    def test_events_limit(self, store_with_plugins):
        events = store_with_plugins.events(limit=2)
        assert len(events) <= 2


# -- PluginEntry Dataclass Tests --

class TestPluginEntry:
    def test_defaults(self):
        entry = PluginEntry(plugin_id="test", name="Test", version="1.0", description="desc", author="me")
        assert entry.status == "available"
        assert entry.risk_tier == "high"
        assert entry.trust_status == "unknown"
        assert entry.capabilities == []
        assert entry.tags == []

    def test_asdict(self):
        entry = PluginEntry(plugin_id="x", name="X", version="1", description="d", author="a")
        d = asdict(entry)
        assert d["plugin_id"] == "x"
        assert "status" in d


# -- Valid Transitions Contract --

class TestTransitionsContract:
    def test_all_states_have_transitions(self):
        for state in ["available", "installed", "enabled", "disabled"]:
            assert state in _VALID_TRANSITIONS


# ── Task 59.2: API Tests ──────────────────────────────────────────

from fastapi.testclient import TestClient

import api.plugins_api as plugins_api_module
from api.plugins_api import router


def _make_test_app(store):
    """Create a FastAPI test app with a pre-configured store."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    plugins_api_module._store = store
    return app


@pytest.fixture
def api_client(store_with_plugins):
    app = _make_test_app(store_with_plugins)
    return TestClient(app)


class TestPluginListAPI:
    def test_list_plugins(self, api_client):
        r = api_client.get("/api/v1/plugins")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 4
        assert len(data["plugins"]) == 4

    def test_list_has_required_fields(self, api_client):
        r = api_client.get("/api/v1/plugins")
        plugin = r.json()["plugins"][0]
        for field in ["plugin_id", "name", "version", "description", "author",
                       "status", "capabilities", "risk_tier", "source", "trust_status"]:
            assert field in plugin


class TestPluginSearchAPI:
    def test_search_by_query(self, api_client):
        r = api_client.get("/api/v1/plugins/search", params={"q": "Alpha"})
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_search_by_status(self, api_client):
        r = api_client.get("/api/v1/plugins/search", params={"status": "available"})
        assert r.status_code == 200
        assert r.json()["total"] == 4

    def test_search_by_category(self, api_client):
        r = api_client.get("/api/v1/plugins/search", params={"category": "security"})
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_search_no_match(self, api_client):
        r = api_client.get("/api/v1/plugins/search", params={"q": "zzzzz"})
        assert r.json()["total"] == 0


class TestPluginDetailAPI:
    def test_get_detail(self, api_client):
        r = api_client.get("/api/v1/plugins/alpha")
        assert r.status_code == 200
        assert r.json()["name"] == "Alpha"
        assert r.json()["risk_tier"] == "low"

    def test_get_detail_404(self, api_client):
        r = api_client.get("/api/v1/plugins/nonexistent")
        assert r.status_code == 404


class TestPluginEventsAPI:
    def test_events(self, api_client):
        r = api_client.get("/api/v1/plugins/events")
        assert r.status_code == 200
        assert "events" in r.json()

    def test_events_with_limit(self, api_client):
        r = api_client.get("/api/v1/plugins/events", params={"limit": 2})
        assert r.status_code == 200


class TestPluginStatsAPI:
    def test_stats(self, api_client):
        r = api_client.get("/api/v1/plugins/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 4
        assert "by_category" in data
        assert "by_risk_tier" in data


class TestPluginInstallAPI:
    def test_install(self, api_client):
        r = api_client.post("/api/v1/plugins/alpha/install")
        assert r.status_code == 200
        assert r.json()["status"] == "installed"

    def test_install_already_installed(self, api_client):
        api_client.post("/api/v1/plugins/alpha/install")
        r = api_client.post("/api/v1/plugins/alpha/install")
        assert r.status_code == 409

    def test_install_404(self, api_client):
        r = api_client.post("/api/v1/plugins/nonexistent/install")
        assert r.status_code == 404


class TestPluginUninstallAPI:
    def test_uninstall(self, api_client):
        api_client.post("/api/v1/plugins/alpha/install")
        r = api_client.post("/api/v1/plugins/alpha/uninstall")
        assert r.status_code == 200
        assert r.json()["status"] == "available"

    def test_uninstall_not_installed(self, api_client):
        r = api_client.post("/api/v1/plugins/alpha/uninstall")
        assert r.status_code == 404


class TestPluginEnableDisableAPI:
    def test_enable(self, api_client):
        api_client.post("/api/v1/plugins/alpha/install")
        r = api_client.post("/api/v1/plugins/alpha/enable")
        assert r.status_code == 200
        assert r.json()["status"] == "enabled"

    def test_enable_not_installed(self, api_client):
        r = api_client.post("/api/v1/plugins/alpha/enable")
        assert r.status_code == 422

    def test_disable(self, api_client):
        api_client.post("/api/v1/plugins/alpha/install")
        api_client.post("/api/v1/plugins/alpha/enable")
        r = api_client.post("/api/v1/plugins/alpha/disable")
        assert r.status_code == 200
        assert r.json()["status"] == "disabled"


class TestPluginConfigAPI:
    def test_update_config(self, api_client):
        r = api_client.put("/api/v1/plugins/alpha/config", json={"config": {"key": "val"}})
        assert r.status_code == 200

    def test_update_config_404(self, api_client):
        r = api_client.put("/api/v1/plugins/nonexistent/config", json={"config": {}})
        assert r.status_code == 404


# ── Task 59.3: Installer Tests ────────────────────────────────────

from services.plugin_installer import PluginInstaller, PluginInstallError


@pytest.fixture
def installer_env(tmp_path):
    """Create temp environment for installer tests."""
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    config_dir = tmp_path / "config" / "plugins"
    config_dir.mkdir(parents=True)

    # Create a valid plugin
    p = plugins_dir / "test_plugin"
    p.mkdir()
    (p / "manifest.json").write_text(json.dumps({
        "name": "TestPlugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "author": "tester",
        "handlers": [{"event_type": "mission.started", "handler": "on_start", "priority": 600}],
    }))

    # Create invalid plugin
    bad = plugins_dir / "bad_plugin"
    bad.mkdir()
    (bad / "manifest.json").write_text("{invalid json")

    installer = PluginInstaller(plugins_dir=plugins_dir, config_dir=config_dir)
    return installer, plugins_dir, config_dir


class MockBus:
    """Minimal EventBus mock for testing handler registration."""

    def __init__(self):
        self.handlers = {}

    def on(self, event_type, handler, priority=0, name=""):
        self.handlers[name] = {"event_type": event_type, "priority": priority, "handler": handler}

    def off(self, name):
        self.handlers.pop(name, None)


class TestPluginInstaller:
    def test_install_success(self, installer_env):
        installer, _, config_dir = installer_env
        manifest = installer.install("test_plugin")
        assert manifest.name == "TestPlugin"
        assert manifest.version == "1.0.0"
        assert (config_dir / "test_plugin.json").exists()

    def test_install_invalid_manifest(self, installer_env):
        installer, _, _ = installer_env
        with pytest.raises(PluginInstallError, match="manifest validation failed"):
            installer.install("bad_plugin")

    def test_install_nonexistent(self, installer_env):
        installer, _, _ = installer_env
        with pytest.raises(PluginInstallError, match="manifest not found"):
            installer.install("nonexistent")

    def test_install_already_installed(self, installer_env):
        installer, _, _ = installer_env
        installer.install("test_plugin")
        with pytest.raises(PluginInstallError, match="already installed"):
            installer.install("test_plugin")

    def test_install_creates_config(self, installer_env):
        installer, _, config_dir = installer_env
        installer.install("test_plugin")
        config = json.loads((config_dir / "test_plugin.json").read_text())
        assert config["enabled"] is True
        assert config["installed"] is True
        assert config["version"] == "1.0.0"


class TestPluginUninstaller:
    def test_uninstall_success(self, installer_env):
        installer, _, config_dir = installer_env
        installer.install("test_plugin")
        assert installer.uninstall("test_plugin")
        assert not (config_dir / "test_plugin.json").exists()

    def test_uninstall_not_installed(self, installer_env):
        installer, _, _ = installer_env
        with pytest.raises(PluginInstallError, match="not installed"):
            installer.uninstall("test_plugin")


class TestPluginEnableDisable:
    def test_enable(self, installer_env):
        installer, _, config_dir = installer_env
        installer.install("test_plugin")
        installer.disable("test_plugin")
        assert installer.enable("test_plugin")
        config = json.loads((config_dir / "test_plugin.json").read_text())
        assert config["enabled"] is True

    def test_disable(self, installer_env):
        installer, _, config_dir = installer_env
        installer.install("test_plugin")
        assert installer.disable("test_plugin")
        config = json.loads((config_dir / "test_plugin.json").read_text())
        assert config["enabled"] is False

    def test_enable_not_installed(self, installer_env):
        installer, _, _ = installer_env
        with pytest.raises(PluginInstallError, match="not installed"):
            installer.enable("test_plugin")

    def test_disable_not_installed(self, installer_env):
        installer, _, _ = installer_env
        with pytest.raises(PluginInstallError, match="not installed"):
            installer.disable("test_plugin")


class TestEventBusHotReload:
    def test_install_registers_handlers(self, installer_env):
        installer, _, _ = installer_env
        bus = MockBus()
        installer.install("test_plugin", bus=bus)
        assert len(bus.handlers) == 1
        assert "plugin:test_plugin:mission.started" in bus.handlers

    def test_handler_priority_500_plus(self, installer_env):
        installer, _, _ = installer_env
        bus = MockBus()
        installer.install("test_plugin", bus=bus)
        handler = bus.handlers["plugin:test_plugin:mission.started"]
        assert handler["priority"] >= 500

    def test_uninstall_deregisters_handlers(self, installer_env):
        installer, _, _ = installer_env
        bus = MockBus()
        installer.install("test_plugin", bus=bus)
        assert len(bus.handlers) == 1
        installer.uninstall("test_plugin", bus=bus)
        assert len(bus.handlers) == 0

    def test_disable_deregisters_handlers(self, installer_env):
        installer, _, _ = installer_env
        bus = MockBus()
        installer.install("test_plugin", bus=bus)
        installer.disable("test_plugin", bus=bus)
        assert len(bus.handlers) == 0

    def test_enable_registers_handlers(self, installer_env):
        installer, _, _ = installer_env
        bus = MockBus()
        installer.install("test_plugin", bus=bus)
        installer.disable("test_plugin", bus=bus)
        installer.enable("test_plugin", bus=bus)
        assert len(bus.handlers) == 1


class TestInstallerConcurrency:
    def test_concurrent_lock_prevents_race(self, installer_env):
        installer, _, _ = installer_env
        lock = installer._get_lock("test_plugin")
        lock.acquire()
        with pytest.raises(PluginInstallError, match="already in progress"):
            installer.install("test_plugin")
        lock.release()
