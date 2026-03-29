"""B-004: Filesystem confinement tests."""
import os
import sys
import tempfile
import pytest
from services.filesystem_guard import FilesystemGuard, ConfinementError

IS_WINDOWS = sys.platform == "win32"


@pytest.fixture
def guard(tmp_path):
    """Create a guard with tmp_path as workspace."""
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    return FilesystemGuard(
        workspace_root=str(tmp_path),
        evidence_root=str(evidence),
        temp_root=tempfile.gettempdir(),
    )


class TestConfinementAllow:
    """Allowed path access."""

    def test_confine_allow_workspace_file(self, guard, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("ok")
        resolved = guard.check_path(str(test_file))
        assert resolved == os.path.realpath(str(test_file))

    def test_confine_allow_workspace_subdir(self, guard, tmp_path):
        subdir = tmp_path / "subdir" / "deep"
        subdir.mkdir(parents=True)
        resolved = guard.check_path(str(subdir))
        assert os.path.realpath(str(subdir)) in resolved

    def test_confine_allow_evidence_dir(self, guard, tmp_path):
        evidence = tmp_path / "evidence" / "sprint-35"
        evidence.mkdir(parents=True)
        resolved = guard.check_path(str(evidence))
        assert "evidence" in resolved

    def test_confine_allow_temp_dir(self, guard):
        temp = tempfile.gettempdir()
        resolved = guard.check_path(temp)
        assert resolved == os.path.realpath(temp)


class TestConfinementDeny:
    """Denied path access."""

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix paths not applicable on Windows")
    def test_confine_deny_etc(self, guard):
        with pytest.raises(ConfinementError, match="System path denied"):
            guard.check_path("/etc/passwd")

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix paths not applicable on Windows")
    def test_confine_deny_usr(self, guard):
        with pytest.raises(ConfinementError, match="System path denied"):
            guard.check_path("/usr/bin/python")

    def test_confine_deny_traversal(self, guard, tmp_path):
        """Reject .. traversal that resolves outside workspace."""
        escaped = str(tmp_path / ".." / ".." / ".." / ".." / "Windows" / "System32")
        with pytest.raises(ConfinementError):
            guard.check_path(escaped)

    def test_confine_deny_windows_system(self, guard):
        """Deny Windows system paths (works on all platforms via mock paths)."""
        with pytest.raises(ConfinementError, match="Windows system path denied"):
            guard.check_path("C:\\Windows\\System32\\cmd.exe")

    def test_confine_deny_windows_program_files(self, guard):
        with pytest.raises(ConfinementError, match="Windows system path denied"):
            guard.check_path("C:\\Program Files\\app.exe")

    def test_confine_deny_ssh_dir(self, guard):
        with pytest.raises(ConfinementError, match="Sensitive directory denied"):
            guard.check_path(os.path.expanduser("~/.ssh/id_rsa"))

    def test_confine_deny_aws_dir(self, guard):
        with pytest.raises(ConfinementError, match="Sensitive directory denied"):
            guard.check_path(os.path.expanduser("~/.aws/credentials"))

    def test_confine_deny_outside_all_roots(self, guard):
        outside = "C:\\nonexistent\\random" if IS_WINDOWS else "/some/random/path"
        with pytest.raises(ConfinementError):
            guard.check_path(outside)


class TestConfinementSymlink:
    """Symlink resolution before check."""

    def test_confine_deny_symlink_to_etc(self, guard, tmp_path):
        """Symlink inside workspace pointing to /etc should be denied."""
        link = tmp_path / "evil_link"
        try:
            os.symlink("/etc", str(link))
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this platform/permissions")
        with pytest.raises(ConfinementError):
            guard.check_path(str(link))


class TestConfinementProperties:
    """Guard properties and immutability."""

    def test_confine_allowed_roots_immutable(self, guard):
        roots = guard.allowed_roots
        roots.append("/evil")
        assert "/evil" not in guard.allowed_roots

    def test_confine_error_has_path_and_reason(self, guard):
        bad_path = "C:\\Windows\\System32" if IS_WINDOWS else "/some/random/path"
        try:
            guard.check_path(bad_path)
            assert False, "Should have raised"
        except ConfinementError as e:
            assert e.path == bad_path
            assert len(e.reason) > 0
