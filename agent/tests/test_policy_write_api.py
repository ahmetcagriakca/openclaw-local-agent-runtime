"""Tests for Sprint 50 Policy Write API.

Covers: CRUD operations, validation errors, reload, audit logging,
and concurrent write conflict tests (Claude Chat condition).
"""

import os
import shutil
import tempfile
import threading

import pytest
import yaml

from mission.policy_engine import PolicyEngine


@pytest.fixture
def tmp_engine():
    """Create a PolicyEngine with temp directory."""
    d = tempfile.mkdtemp()
    # Seed with one default rule
    with open(os.path.join(d, "default-allow.yaml"), "w") as f:
        yaml.safe_dump({
            "name": "default-allow", "priority": 9999,
            "condition": {"always": True}, "decision": "allow",
        }, f)
    engine = PolicyEngine(policies_dir=d)
    yield engine
    shutil.rmtree(d)


class TestCreateRule:
    def test_create_valid_rule(self, tmp_engine):
        rule = tmp_engine.create_rule({
            "name": "test-deny", "priority": 100,
            "condition": {"always": True}, "decision": "deny",
        })
        assert rule.name == "test-deny"
        assert rule.priority == 100
        assert len(tmp_engine.rules) == 2

    def test_create_duplicate_raises(self, tmp_engine):
        with pytest.raises(ValueError, match="already exists"):
            tmp_engine.create_rule({
                "name": "default-allow", "priority": 100,
                "condition": {"always": True}, "decision": "allow",
            })

    def test_create_invalid_raises(self, tmp_engine):
        with pytest.raises(Exception):
            tmp_engine.create_rule({
                "name": "bad", "priority": -1,
                "condition": {"always": True}, "decision": "allow",
            })

    def test_create_persists_yaml(self, tmp_engine):
        tmp_engine.create_rule({
            "name": "persisted", "priority": 200,
            "condition": {"always": True}, "decision": "deny",
        })
        yaml_path = os.path.join(tmp_engine._policies_dir, "persisted.yaml")
        assert os.path.exists(yaml_path)
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        assert data["name"] == "persisted"


class TestUpdateRule:
    def test_update_existing(self, tmp_engine):
        rule = tmp_engine.update_rule("default-allow", {
            "priority": 5000,
            "condition": {"always": True},
            "decision": "deny",
        })
        assert rule.decision.value == "deny"
        assert rule.priority == 5000

    def test_update_nonexistent_raises(self, tmp_engine):
        with pytest.raises(KeyError, match="not found"):
            tmp_engine.update_rule("nonexistent", {
                "priority": 100,
                "condition": {"always": True},
                "decision": "allow",
            })


class TestDeleteRule:
    def test_delete_existing(self, tmp_engine):
        tmp_engine.create_rule({
            "name": "to-delete", "priority": 100,
            "condition": {"always": True}, "decision": "deny",
        })
        assert tmp_engine.get_rule("to-delete") is not None
        tmp_engine.delete_rule("to-delete")
        assert tmp_engine.get_rule("to-delete") is None

    def test_delete_nonexistent_raises(self, tmp_engine):
        with pytest.raises(KeyError, match="not found"):
            tmp_engine.delete_rule("nonexistent")

    def test_delete_removes_yaml(self, tmp_engine):
        tmp_engine.create_rule({
            "name": "removable", "priority": 100,
            "condition": {"always": True}, "decision": "deny",
        })
        yaml_path = os.path.join(tmp_engine._policies_dir, "removable.yaml")
        assert os.path.exists(yaml_path)
        tmp_engine.delete_rule("removable")
        assert not os.path.exists(yaml_path)


class TestConcurrentWrites:
    """Claude Chat condition: +2 concurrent-write conflict tests."""

    def test_concurrent_creates_no_corruption(self, tmp_engine):
        """Multiple threads creating different rules simultaneously."""
        errors = []
        def create_rule(name, priority):
            try:
                tmp_engine.create_rule({
                    "name": name, "priority": priority,
                    "condition": {"always": True}, "decision": "allow",
                })
            except Exception as e:
                errors.append(str(e))

        threads = [
            threading.Thread(target=create_rule, args=(f"concurrent-{i}", 100 + i))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(tmp_engine.rules) == 6  # 1 default + 5 new

    def test_concurrent_create_same_name_one_wins(self, tmp_engine):
        """Two threads creating same-name rule — one succeeds, one gets conflict."""
        results = {"success": 0, "conflict": 0}
        def create_dup():
            try:
                tmp_engine.create_rule({
                    "name": "race-rule", "priority": 100,
                    "condition": {"always": True}, "decision": "deny",
                })
                results["success"] += 1
            except ValueError:
                results["conflict"] += 1

        threads = [threading.Thread(target=create_dup) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results["success"] == 1
        assert results["conflict"] == 1
        assert tmp_engine.get_rule("race-rule") is not None
