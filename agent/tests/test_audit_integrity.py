"""D-129 / B-008: Audit log tamper resistance tests."""
import json
import os
import subprocess
import sys

import pytest

from persistence.audit_integrity import GENESIS_HASH, append_entry, verify_chain


@pytest.fixture
def audit_file(tmp_path):
    return str(tmp_path / "audit.jsonl")


class TestAuditIntegrityAppend:
    """D-129: Hash chain append."""

    def test_audit_integrity_append_creates_file(self, audit_file):
        entry = append_entry("test_event", "test_actor", "detail", audit_path=audit_file)
        assert os.path.exists(audit_file)
        assert entry["event"] == "test_event"
        assert "entry_hash" in entry
        assert "prev_hash" in entry

    def test_audit_integrity_first_entry_uses_genesis(self, audit_file):
        entry = append_entry("first", "actor", audit_path=audit_file)
        assert entry["prev_hash"] == GENESIS_HASH

    def test_audit_integrity_chain_links(self, audit_file):
        e1 = append_entry("first", "actor", audit_path=audit_file)
        e2 = append_entry("second", "actor", audit_path=audit_file)
        assert e2["prev_hash"] == e1["entry_hash"]

    def test_audit_integrity_three_entries_chain(self, audit_file):
        e1 = append_entry("a", "x", audit_path=audit_file)
        e2 = append_entry("b", "y", audit_path=audit_file)
        e3 = append_entry("c", "z", audit_path=audit_file)
        assert e2["prev_hash"] == e1["entry_hash"]
        assert e3["prev_hash"] == e2["entry_hash"]


class TestAuditIntegrityVerify:
    """D-129: Chain verification."""

    def test_audit_integrity_verify_empty(self, audit_file):
        result = verify_chain(audit_file)
        assert result["status"] == "INTEGRITY_OK"
        assert result["entry_count"] == 0

    def test_audit_integrity_verify_intact(self, audit_file):
        append_entry("a", "x", audit_path=audit_file)
        append_entry("b", "y", audit_path=audit_file)
        append_entry("c", "z", audit_path=audit_file)
        result = verify_chain(audit_file)
        assert result["status"] == "INTEGRITY_OK"
        assert result["entry_count"] == 3

    def test_audit_integrity_verify_tamper_detected(self, audit_file):
        """D-129: Tampered entry must be detected."""
        append_entry("a", "x", audit_path=audit_file)
        append_entry("b", "y", audit_path=audit_file)
        append_entry("c", "z", audit_path=audit_file)

        # Tamper with the second entry
        with open(audit_file, "r") as f:
            lines = f.readlines()
        entry = json.loads(lines[1])
        entry["detail"] = "TAMPERED"
        lines[1] = json.dumps(entry, sort_keys=True) + "\n"
        with open(audit_file, "w") as f:
            f.writelines(lines)

        result = verify_chain(audit_file)
        assert result["status"] == "INTEGRITY_FAIL"
        assert result["broken_entry_index"] == 1

    def test_audit_integrity_verify_deleted_entry(self, audit_file):
        """D-129: Deleted entry breaks chain."""
        append_entry("a", "x", audit_path=audit_file)
        append_entry("b", "y", audit_path=audit_file)
        append_entry("c", "z", audit_path=audit_file)

        # Remove the second entry
        with open(audit_file, "r") as f:
            lines = f.readlines()
        del lines[1]
        with open(audit_file, "w") as f:
            f.writelines(lines)

        result = verify_chain(audit_file)
        assert result["status"] == "INTEGRITY_FAIL"

    def test_audit_integrity_verify_malformed_json(self, audit_file):
        with open(audit_file, "w") as f:
            f.write("not json\n")
        result = verify_chain(audit_file)
        assert result["status"] == "INTEGRITY_FAIL"
        assert result["broken_entry_index"] == 0


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="subprocess.DuplicateHandle WinError 50 on Python 3.14 Win32 sandbox — CI Ubuntu unaffected"
)
class TestAuditIntegrityCLI:
    """D-129: CLI exit code verification."""

    def test_audit_integrity_cli_exit_0_on_ok(self, audit_file):
        append_entry("a", "x", audit_path=audit_file)
        result = subprocess.run(
            [sys.executable, "tools/verify-audit-chain.py", audit_file],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        assert result.returncode == 0
        assert "INTEGRITY_OK" in result.stdout

    def test_audit_integrity_cli_exit_1_on_fail(self, audit_file):
        append_entry("a", "x", audit_path=audit_file)
        # Tamper
        with open(audit_file, "r") as f:
            lines = f.readlines()
        entry = json.loads(lines[0])
        entry["detail"] = "TAMPERED"
        with open(audit_file, "w") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

        result = subprocess.run(
            [sys.executable, "tools/verify-audit-chain.py", audit_file],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        assert result.returncode == 1
        assert "INTEGRITY_FAIL" in result.stdout
