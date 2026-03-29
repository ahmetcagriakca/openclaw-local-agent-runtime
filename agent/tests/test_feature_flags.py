"""Tests for feature flags module — D-102 context isolation wire-up."""
import json
from unittest import mock


class TestFeatureFlagsLoad:
    """Test loading feature flags from config."""

    def setup_method(self):
        """Reset module state before each test."""
        from config import feature_flags
        feature_flags.reset()

    def test_defaults_when_no_file(self, tmp_path):
        """When features.json does not exist, defaults are used."""
        from config import feature_flags
        feature_flags.reset()
        with mock.patch.object(feature_flags, "_FEATURES_PATH",
                               tmp_path / "nonexistent.json"):
            flags = feature_flags.reload()
        assert flags["CONTEXT_ISOLATION_ENABLED"] is False

    def test_load_from_file(self, tmp_path):
        """Load flags from a valid features.json."""
        from config import feature_flags
        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps({
            "CONTEXT_ISOLATION_ENABLED": True
        }), encoding="utf-8")

        with mock.patch.object(feature_flags, "_FEATURES_PATH", features_file):
            flags = feature_flags.reload()
        assert flags["CONTEXT_ISOLATION_ENABLED"] is True

    def test_load_merges_with_defaults(self, tmp_path):
        """File with missing keys gets defaults filled in."""
        from config import feature_flags
        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps({}), encoding="utf-8")

        with mock.patch.object(feature_flags, "_FEATURES_PATH", features_file):
            flags = feature_flags.reload()
        assert flags["CONTEXT_ISOLATION_ENABLED"] is False

    def test_load_corrupted_file_uses_defaults(self, tmp_path):
        """Corrupted JSON falls back to defaults."""
        from config import feature_flags
        features_file = tmp_path / "features.json"
        features_file.write_text("NOT JSON", encoding="utf-8")

        with mock.patch.object(feature_flags, "_FEATURES_PATH", features_file):
            flags = feature_flags.reload()
        assert flags["CONTEXT_ISOLATION_ENABLED"] is False

    def test_get_flag_lazy_loads(self, tmp_path):
        """get_flag triggers lazy load if not yet loaded."""
        from config import feature_flags
        feature_flags.reset()
        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps({
            "CONTEXT_ISOLATION_ENABLED": True
        }), encoding="utf-8")

        with mock.patch.object(feature_flags, "_FEATURES_PATH", features_file):
            val = feature_flags.get_flag("CONTEXT_ISOLATION_ENABLED")
        assert val is True

    def test_get_flag_unknown_returns_false(self, tmp_path):
        """Unknown flag returns False."""
        from config import feature_flags
        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps({}), encoding="utf-8")

        with mock.patch.object(feature_flags, "_FEATURES_PATH", features_file):
            feature_flags.reload()
            val = feature_flags.get_flag("NONEXISTENT_FLAG")
        assert val is False

    def test_get_all_flags(self, tmp_path):
        """get_all_flags returns a copy of all flags."""
        from config import feature_flags
        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps({
            "CONTEXT_ISOLATION_ENABLED": True
        }), encoding="utf-8")

        with mock.patch.object(feature_flags, "_FEATURES_PATH", features_file):
            feature_flags.reload()
            all_flags = feature_flags.get_all_flags()
        assert all_flags["CONTEXT_ISOLATION_ENABLED"] is True
        # Verify it's a copy
        all_flags["CONTEXT_ISOLATION_ENABLED"] = False
        assert feature_flags.get_flag("CONTEXT_ISOLATION_ENABLED") is True


class TestFeatureFlagsPersist:
    """Test persisting flag changes."""

    def setup_method(self):
        from config import feature_flags
        feature_flags.reset()

    def test_set_flag_persists(self, tmp_path):
        """set_flag writes to disk via atomic_write_json."""
        from config import feature_flags
        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps({
            "CONTEXT_ISOLATION_ENABLED": False
        }), encoding="utf-8")

        with mock.patch.object(feature_flags, "_FEATURES_PATH", features_file):
            feature_flags.reload()
            feature_flags.set_flag("CONTEXT_ISOLATION_ENABLED", True)

        # Verify file on disk
        saved = json.loads(features_file.read_text(encoding="utf-8"))
        assert saved["CONTEXT_ISOLATION_ENABLED"] is True

    def test_set_flag_toggle(self, tmp_path):
        """Toggle a flag on and off."""
        from config import feature_flags
        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps({
            "CONTEXT_ISOLATION_ENABLED": False
        }), encoding="utf-8")

        with mock.patch.object(feature_flags, "_FEATURES_PATH", features_file):
            feature_flags.reload()
            assert feature_flags.get_flag("CONTEXT_ISOLATION_ENABLED") is False

            feature_flags.set_flag("CONTEXT_ISOLATION_ENABLED", True)
            assert feature_flags.get_flag("CONTEXT_ISOLATION_ENABLED") is True

            feature_flags.set_flag("CONTEXT_ISOLATION_ENABLED", False)
            assert feature_flags.get_flag("CONTEXT_ISOLATION_ENABLED") is False


class TestContextIsolationFlag:
    """Test that the flag actually controls assembler behavior."""

    def setup_method(self):
        from config import feature_flags
        feature_flags.reset()

    def test_isolation_disabled_returns_full(self, tmp_path):
        """When CONTEXT_ISOLATION_ENABLED=False, get_artifact returns full tier."""
        from config import feature_flags
        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps({
            "CONTEXT_ISOLATION_ENABLED": False
        }), encoding="utf-8")

        with mock.patch.object(feature_flags, "_FEATURES_PATH", features_file):
            feature_flags.reload()

            from context.assembler import ContextAssembler
            asm = ContextAssembler("m-test-001")
            aid = asm.store_artifact(
                "requirements_brief",
                {"title": "Test", "content": "Full content here"},
                "s1", "analyst", "analysis"
            )

            # Request tier A (metadata) — should get full artifact anyway
            result = asm.get_artifact(aid, "A", "manager", "s1")
            # Full artifact is a dict with "type" and data
            assert isinstance(result, dict)
            assert result.get("type") == "requirements_brief"

    def test_isolation_enabled_respects_tier(self, tmp_path):
        """When CONTEXT_ISOLATION_ENABLED=True, tier matrix is respected."""
        from config import feature_flags
        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps({
            "CONTEXT_ISOLATION_ENABLED": True
        }), encoding="utf-8")

        with mock.patch.object(feature_flags, "_FEATURES_PATH", features_file):
            feature_flags.reload()

            from context.assembler import ContextAssembler
            asm = ContextAssembler("m-test-002")
            aid = asm.store_artifact(
                "requirements_brief",
                {"title": "Test", "content": "Full content here"},
                "s1", "analyst", "analysis"
            )

            # Request tier A (metadata) — should get metadata, not full
            result = asm.get_artifact(aid, "A", "manager", "s1")
            # Metadata view is a dict but different from full artifact
            assert isinstance(result, dict)
            # Metadata has _header with artifactId, not the full data payload
            assert "_header" in result
            assert "data" not in result  # full artifact has "data", metadata doesn't

    def test_isolation_disabled_skips_reread_downgrade(self, tmp_path):
        """When disabled, no reread downgrade occurs."""
        from config import feature_flags
        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps({
            "CONTEXT_ISOLATION_ENABLED": False
        }), encoding="utf-8")

        with mock.patch.object(feature_flags, "_FEATURES_PATH", features_file):
            feature_flags.reload()

            from context.assembler import ContextAssembler
            asm = ContextAssembler("m-test-003")
            aid = asm.store_artifact(
                "requirements_brief",
                {"title": "Test", "content": "Full content here"},
                "s1", "analyst", "analysis"
            )

            # Read full twice — should NOT downgrade
            result1 = asm.get_artifact(aid, "D", "analyst", "s1")
            result2 = asm.get_artifact(aid, "D", "analyst", "s1")
            # Both should be full artifacts (dict), not summary (str)
            assert isinstance(result1, dict)
            assert isinstance(result2, dict)

    def test_build_context_isolation_disabled(self, tmp_path):
        """build_context_for_role returns full tier D when disabled."""
        from config import feature_flags
        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps({
            "CONTEXT_ISOLATION_ENABLED": False
        }), encoding="utf-8")

        with mock.patch.object(feature_flags, "_FEATURES_PATH", features_file):
            feature_flags.reload()

            from context.assembler import ContextAssembler
            asm = ContextAssembler("m-test-004")
            aid = asm.store_artifact(
                "requirements_brief",
                {"title": "Test", "content": "Full content"},
                "s1", "analyst", "analysis"
            )

            # manager would normally get tier B for requirements_brief
            ctx = asm.build_context_for_role(
                "manager", "management", "s1", [aid])
            assert len(ctx) == 1
            _, content, tier = ctx[0]
            assert tier == "D"
            assert isinstance(content, dict)
