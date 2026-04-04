"""Tests for B-116 Multi-tenant isolation."""
import pytest

from auth.tenant import (
    DEFAULT_TENANT_ID,
    Tenant,
    TenantContext,
    TenantError,
    TenantStore,
    get_tenant_context,
    set_tenant_context,
)


@pytest.fixture
def store(tmp_path):
    path = str(tmp_path / "tenants.json")
    return TenantStore(store_path=path)


class TestTenantModel:
    def test_tenant_defaults(self):
        t = Tenant(tenant_id="acme", name="Acme Corp")
        assert t.tenant_id == "acme"
        assert t.enabled is True
        assert t.quota["max_missions"] == 100

    def test_tenant_to_dict(self):
        t = Tenant(tenant_id="acme", name="Acme Corp")
        d = t.to_dict()
        assert d["tenant_id"] == "acme"
        assert "quota" in d


class TestTenantStore:
    def test_default_tenant_exists(self, store):
        default = store.get(DEFAULT_TENANT_ID)
        assert default is not None
        assert default.name == "Default Tenant"

    def test_create_tenant(self, store):
        tenant = store.create("acme", "Acme Corp")
        assert tenant.tenant_id == "acme"
        assert store.count == 2  # default + acme

    def test_create_duplicate(self, store):
        store.create("acme", "Acme Corp")
        with pytest.raises(TenantError, match="already exists"):
            store.create("acme", "Acme Corp 2")

    def test_create_with_quota(self, store):
        tenant = store.create("acme", "Acme", quota={"max_missions": 50})
        assert tenant.quota["max_missions"] == 50

    def test_get_existing(self, store):
        store.create("acme", "Acme Corp")
        found = store.get("acme")
        assert found is not None
        assert found.name == "Acme Corp"

    def test_get_missing(self, store):
        assert store.get("nonexistent") is None

    def test_update_name(self, store):
        store.create("acme", "Acme Corp")
        updated = store.update("acme", name="Acme Industries")
        assert updated.name == "Acme Industries"

    def test_update_enabled(self, store):
        store.create("acme", "Acme")
        updated = store.update("acme", enabled=False)
        assert updated.enabled is False

    def test_update_settings(self, store):
        store.create("acme", "Acme")
        updated = store.update("acme", settings={"theme": "dark"})
        assert updated.settings["theme"] == "dark"

    def test_update_quota(self, store):
        store.create("acme", "Acme")
        updated = store.update("acme", quota={"max_missions": 200})
        assert updated.quota["max_missions"] == 200

    def test_update_missing(self, store):
        assert store.update("nonexistent", name="x") is None

    def test_delete_tenant(self, store):
        store.create("acme", "Acme")
        assert store.delete("acme") is True
        assert store.get("acme") is None

    def test_delete_default_forbidden(self, store):
        with pytest.raises(TenantError, match="Cannot delete default"):
            store.delete(DEFAULT_TENANT_ID)

    def test_delete_missing(self, store):
        assert store.delete("nonexistent") is False

    def test_list_all(self, store):
        store.create("acme", "Acme")
        store.create("beta", "Beta")
        tenants = store.list()
        assert len(tenants) == 3  # default + 2

    def test_list_enabled_only(self, store):
        store.create("acme", "Acme")
        store.update("acme", enabled=False)
        tenants = store.list(enabled_only=True)
        assert len(tenants) == 1  # only default


class TestTenantQuota:
    def test_check_within_limit(self, store):
        store.create("acme", "Acme", quota={"max_missions": 10})
        result = store.check_quota("acme", "max_missions", 5)
        assert result["allowed"] is True

    def test_check_exceeded(self, store):
        store.create("acme", "Acme", quota={"max_missions": 10})
        result = store.check_quota("acme", "max_missions", 10)
        assert result["allowed"] is False
        assert result["reason"] == "quota_exceeded"

    def test_check_disabled_tenant(self, store):
        store.create("acme", "Acme")
        store.update("acme", enabled=False)
        result = store.check_quota("acme", "max_missions", 1)
        assert result["allowed"] is False
        assert result["reason"] == "tenant_disabled"

    def test_check_missing_tenant(self, store):
        result = store.check_quota("nonexistent", "max_missions", 1)
        assert result["allowed"] is False

    def test_check_unlimited(self, store):
        store.create("acme", "Acme", quota={"max_missions": 0})
        result = store.check_quota("acme", "max_missions", 999)
        assert result["allowed"] is True


class TestTenantContext:
    def test_default_context(self):
        ctx = TenantContext()
        assert ctx.tenant_id == DEFAULT_TENANT_ID

    def test_scope_default_passthrough(self):
        ctx = TenantContext()
        assert ctx.scope_mission_id("m-123") == "m-123"

    def test_scope_custom_tenant(self):
        ctx = TenantContext(tenant_id="acme")
        assert ctx.scope_mission_id("m-123") == "acme:m-123"

    def test_matches_default(self):
        ctx = TenantContext()
        assert ctx.matches_mission("m-123") is True
        assert ctx.matches_mission("acme:m-123") is False

    def test_matches_custom(self):
        ctx = TenantContext(tenant_id="acme")
        assert ctx.matches_mission("acme:m-123") is True
        assert ctx.matches_mission("beta:m-123") is False

    def test_extract_mission_id(self):
        ctx = TenantContext(tenant_id="acme")
        assert ctx.extract_mission_id("acme:m-123") == "m-123"
        assert ctx.extract_mission_id("m-123") == "m-123"

    def test_to_dict(self):
        ctx = TenantContext(tenant_id="acme")
        d = ctx.to_dict()
        assert d["tenant_id"] == "acme"
        assert "resolved_at" in d


class TestTenantContextGlobal:
    def test_get_default(self):
        ctx = get_tenant_context()
        assert ctx.tenant_id == DEFAULT_TENANT_ID

    def test_set_and_get(self):
        set_tenant_context("acme")
        ctx = get_tenant_context()
        assert ctx.tenant_id == "acme"
        # Reset
        set_tenant_context(DEFAULT_TENANT_ID)


class TestTenantPersistence:
    def test_round_trip(self, tmp_path):
        path = str(tmp_path / "tenants.json")
        s1 = TenantStore(store_path=path)
        s1.create("acme", "Acme Corp")

        s2 = TenantStore(store_path=path)
        assert s2.count == 2
        assert s2.get("acme") is not None
