"""Filesystem confinement guard — B-004 / Sprint 35.

Restricts file operations to allowed directories only.
- Path normalization via os.path.realpath()
- Reject relative traversal (.. resolving outside allowed roots)
- Symlinks resolved to real path, then checked
- Deny behavior: raise ConfinementError, log to audit
"""
import logging
import os

logger = logging.getLogger("mcc.filesystem_guard")


class ConfinementError(Exception):
    """Raised when a file operation is denied by the filesystem guard."""

    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Confinement denied: {path} — {reason}")


class FilesystemGuard:
    """Restricts file operations to allowed directory roots.

    Allowed roots are resolved via os.path.realpath() at init and immutable after.
    All path checks resolve the target path before comparison.
    """

    def __init__(self, workspace_root: str, evidence_root: str = None, temp_root: str = None):
        import tempfile
        self._allowed_roots = []

        # Workspace root (required)
        self._allowed_roots.append(os.path.realpath(workspace_root))

        # Evidence root (default: workspace/evidence/)
        if evidence_root:
            self._allowed_roots.append(os.path.realpath(evidence_root))
        else:
            self._allowed_roots.append(os.path.realpath(os.path.join(workspace_root, "evidence")))

        # Temp root
        if temp_root:
            self._allowed_roots.append(os.path.realpath(temp_root))
        else:
            self._allowed_roots.append(os.path.realpath(tempfile.gettempdir()))

        # Windows-specific denied paths (checked as normalized lowercase)
        self._windows_denied = [
            "c:\\windows",
            "c:\\program files",
            "c:\\program files (x86)",
        ]
        # User-sensitive denied paths
        self._sensitive_denied_suffixes = [
            ".ssh",
            ".aws",
            ".gnupg",
            ".config" + os.sep + "gcloud",
        ]

    @property
    def allowed_roots(self) -> list[str]:
        """Return immutable copy of allowed roots."""
        return list(self._allowed_roots)

    def check_path(self, path: str) -> str:
        """Check if path is allowed. Returns resolved real path if allowed.

        Raises ConfinementError if denied.
        """
        resolved = os.path.realpath(path)

        # Check Windows-specific denials
        resolved_lower = resolved.lower()
        for denied in self._windows_denied:
            if resolved_lower.startswith(denied):
                self._deny(path, f"Windows system path denied: {denied}")

        # Check sensitive user directories
        for suffix in self._sensitive_denied_suffixes:
            if os.sep + suffix in resolved or resolved.endswith(suffix):
                self._deny(path, f"Sensitive directory denied: {suffix}")

        # Check Unix system paths
        unix_denied = ["/etc", "/usr", "/bin", "/sbin", "/boot", "/proc", "/sys"]
        for denied in unix_denied:
            if resolved == denied or resolved.startswith(denied + "/"):
                self._deny(path, f"System path denied: {denied}")

        # Check if under any allowed root
        for root in self._allowed_roots:
            if resolved.startswith(root + os.sep) or resolved == root:
                return resolved

        # Not under any allowed root
        self._deny(path, "Path is outside all allowed roots")

    def _deny(self, path: str, reason: str):
        """Deny access and log."""
        logger.warning("Confinement denied: %s — %s", path, reason)
        raise ConfinementError(path, reason)
