"""Tests for multi-source allowlist — B-009."""
import os

import pytest
import yaml

from services.allowlist_store import AllowlistStore


@pytest.fixture
def tmp_dir(tmp_path):
    """Temporary allowlists directory."""
    d = tmp_path / "allowlists"
    d.mkdir()
    return str(d)


@pytest.fixture
def store(tmp_dir):
    return AllowlistStore(allowlists_dir=tmp_dir)


@pytest.fixture
def sample_yaml(tmp_dir):
    """Create a sample allowlist YAML."""
    data = {
        "name": "api-sources",
        "source_type": "caller_source",
        "values": ["dashboard", "api", "cli"],
        "description": "Allowed API sources",
        "enabled": True,
    }
    path = os.path.join(tmp_dir, "api-sources.yaml")
    with open(path, "w") as f:
        yaml.safe_dump(data, f)
    return path


# ── Load tests ────────────────────────────────────────────────

class TestLoad:
    def test_load_empty_dir(self, store):
        assert len(store.entries) == 0

    def test_load_from_yaml(self, tmp_dir, sample_yaml):
        store = AllowlistStore(allowlists_dir=tmp_dir)
        assert len(store.entries) == 1
        assert store.entries[0].name == "api-sources"

    def test_load_multiple_files(self, tmp_dir):
        for name in ["a", "b", "c"]:
            data = {"name": name, "source_type": "caller_source", "values": ["x"]}
            with open(os.path.join(tmp_dir, f"{name}.yaml"), "w") as f:
                yaml.safe_dump(data, f)
        store = AllowlistStore(allowlists_dir=tmp_dir)
        assert len(store.entries) == 3

    def test_load_skips_invalid_yaml(self, tmp_dir):
        with open(os.path.join(tmp_dir, "bad.yaml"), "w") as f:
            f.write(": invalid: yaml: [")
        store = AllowlistStore(allowlists_dir=tmp_dir)
        assert len(store.entries) == 0

    def test_load_nonexistent_dir(self):
        store = AllowlistStore(allowlists_dir="/nonexistent/path")
        assert len(store.entries) == 0


# ── Check tests ───────────────────────────────────────────────

class TestCheck:
    def test_check_allowed(self, tmp_dir, sample_yaml):
        store = AllowlistStore(allowlists_dir=tmp_dir)
        assert store.check("caller_source", "dashboard") is True

    def test_check_denied(self, tmp_dir, sample_yaml):
        store = AllowlistStore(allowlists_dir=tmp_dir)
        assert store.check("caller_source", "unknown") is False

    def test_check_no_restrictions(self, store):
        # No allowlists = everything allowed
        assert store.check("caller_source", "anything") is True

    def test_check_wildcard(self, tmp_dir):
        data = {"name": "wildcard", "source_type": "caller_role", "values": ["*"]}
        with open(os.path.join(tmp_dir, "wildcard.yaml"), "w") as f:
            yaml.safe_dump(data, f)
        store = AllowlistStore(allowlists_dir=tmp_dir)
        assert store.check("caller_role", "operator") is True

    def test_check_prefix_pattern(self, tmp_dir):
        data = {"name": "prefix", "source_type": "caller_id", "values": ["admin.*"]}
        with open(os.path.join(tmp_dir, "prefix.yaml"), "w") as f:
            yaml.safe_dump(data, f)
        store = AllowlistStore(allowlists_dir=tmp_dir)
        assert store.check("caller_id", "admin.john") is True
        assert store.check("caller_id", "user.jane") is False

    def test_check_disabled_entry(self, tmp_dir):
        data = {"name": "disabled", "source_type": "caller_source",
                "values": ["dashboard"], "enabled": False}
        with open(os.path.join(tmp_dir, "disabled.yaml"), "w") as f:
            yaml.safe_dump(data, f)
        store = AllowlistStore(allowlists_dir=tmp_dir)
        # Disabled entries are ignored, so no restrictions = allowed
        assert store.check("caller_source", "unknown") is True


# ── Check caller tests ────────────────────────────────────────

class TestCheckCaller:
    def test_caller_allowed(self, tmp_dir, sample_yaml):
        store = AllowlistStore(allowlists_dir=tmp_dir)
        result = store.check_caller({
            "source": "dashboard",
            "caller_id": "user1",
            "caller_role": "operator",
        })
        assert result["allowed"] is True
        assert result["denied_by"] == []

    def test_caller_denied(self, tmp_dir, sample_yaml):
        store = AllowlistStore(allowlists_dir=tmp_dir)
        result = store.check_caller({
            "source": "telegram",
            "caller_id": "user1",
            "caller_role": "operator",
        })
        assert result["allowed"] is False
        assert len(result["denied_by"]) > 0

    def test_caller_no_restrictions(self, store):
        result = store.check_caller({
            "source": "anything",
            "caller_id": "anyone",
            "caller_role": "any",
        })
        assert result["allowed"] is True


# ── CRUD tests ────────────────────────────────────────────────

class TestCRUD:
    def test_create(self, store, tmp_dir):
        entry = store.create({
            "name": "new-list",
            "source_type": "caller_source",
            "values": ["dashboard"],
        })
        assert entry.name == "new-list"
        assert os.path.exists(os.path.join(tmp_dir, "new-list.yaml"))

    def test_create_duplicate_raises(self, store):
        store.create({"name": "dup", "source_type": "caller_source", "values": []})
        with pytest.raises(ValueError, match="already exists"):
            store.create({"name": "dup", "source_type": "caller_source", "values": []})

    def test_create_no_name_raises(self, store):
        with pytest.raises(ValueError, match="Invalid name"):
            store.create({"source_type": "caller_source"})

    def test_get_existing(self, store):
        store.create({"name": "test", "source_type": "caller_id", "values": ["a"]})
        entry = store.get("test")
        assert entry is not None
        assert entry.source_type == "caller_id"

    def test_get_nonexistent(self, store):
        assert store.get("nope") is None

    def test_update(self, store):
        store.create({"name": "upd", "source_type": "caller_source", "values": ["a"]})
        updated = store.update("upd", {"values": ["a", "b"]})
        assert "b" in updated.values

    def test_update_nonexistent_raises(self, store):
        with pytest.raises(KeyError, match="not found"):
            store.update("nope", {"values": ["x"]})

    def test_delete(self, store, tmp_dir):
        store.create({"name": "del", "source_type": "caller_source", "values": []})
        assert store.delete("del") is True
        assert not os.path.exists(os.path.join(tmp_dir, "del.yaml"))
        assert store.get("del") is None

    def test_delete_nonexistent_raises(self, store):
        with pytest.raises(KeyError, match="not found"):
            store.delete("nope")


# ── Serialization tests ──────────────────────────────────────

class TestSerialization:
    def test_to_dict(self, store):
        store.create({"name": "s1", "source_type": "caller_source", "values": ["a"]})
        store.create({"name": "s2", "source_type": "caller_id", "values": ["b"]})
        result = store.to_dict()
        assert len(result) == 2
        assert result[0]["name"] == "s1"

    def test_entry_roundtrip(self, store, tmp_dir):
        store.create({
            "name": "rt",
            "source_type": "caller_role",
            "values": ["operator", "admin"],
            "description": "Test entry",
            "enabled": True,
        })
        # Reload from disk
        store2 = AllowlistStore(allowlists_dir=tmp_dir)
        entry = store2.get("rt")
        assert entry.values == ["operator", "admin"]
        assert entry.description == "Test entry"
