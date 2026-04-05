"""Bridge contract enforcement tests — D-137.

Validates that:
1. No direct WSL subprocess calls exist in agent code (bypass prevention)
2. All PowerShell execution routes through canonical paths (mcp_client or bridge wrappers)
3. Bridge contract schemas are enforced
4. Legacy fallback paths are removed
"""
import os
import re
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = AGENT_DIR.parent


class TestBypassPrevention:
    """Ensure no direct WSL/PowerShell subprocess calls exist in agent code."""

    def _get_python_files(self):
        """Get all Python files in agent/ excluding tests/."""
        files = []
        for root, dirs, filenames in os.walk(AGENT_DIR):
            # Skip test directories
            if "tests" in root or "__pycache__" in root:
                continue
            for f in filenames:
                if f.endswith(".py"):
                    files.append(os.path.join(root, f))
        return files

    def _is_code_line(self, line: str, in_docstring: bool) -> tuple:
        """Check if line is actual code (not comment/docstring). Returns (is_code, in_docstring)."""
        stripped = line.strip()
        if stripped.startswith("#"):
            return False, in_docstring
        # Toggle docstring state on triple-quote boundaries
        triple_count = stripped.count('"""') + stripped.count("'''")
        if triple_count == 1:
            in_docstring = not in_docstring
            return False, in_docstring
        if triple_count >= 2:
            return False, in_docstring  # Single-line docstring
        return not in_docstring, in_docstring

    def test_no_direct_wsl_subprocess_calls(self):
        """No agent code should call 'wsl -d' via subprocess (D-137)."""
        violations = []
        for filepath in self._get_python_files():
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            in_docstring = False
            for i, line in enumerate(lines, 1):
                is_code, in_docstring = self._is_code_line(line, in_docstring)
                if not is_code:
                    continue
                if re.search(r'subprocess\.\w+\(', line) and 'wsl' in line.lower():
                    violations.append(f"{os.path.relpath(filepath, AGENT_DIR)}:{i}")
                # Also catch: ["wsl", on a code line after subprocess.run on a nearby line
                if re.search(r'\[\s*["\']wsl["\']', line):
                    violations.append(f"{os.path.relpath(filepath, AGENT_DIR)}:{i}")
        assert violations == [], f"Direct WSL subprocess calls found (D-137 violation): {violations}"

    def test_no_direct_powershell_subprocess_in_services(self):
        """No service code should call powershell.exe/pwsh.exe via subprocess directly."""
        violations = []
        services_dir = AGENT_DIR / "services"
        api_dir = AGENT_DIR / "api"
        mission_dir = AGENT_DIR / "mission"

        for d in [services_dir, api_dir, mission_dir]:
            if not d.exists():
                continue
            for filepath in d.rglob("*.py"):
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith('"""'):
                        continue
                    if "subprocess" in line and re.search(r"powershell|pwsh", line, re.IGNORECASE):
                        violations.append(f"{os.path.relpath(filepath, AGENT_DIR)}:{i}")
        assert violations == [], f"Direct PowerShell subprocess calls found (D-137 violation): {violations}"

    def test_mcp_client_is_canonical_powershell_path(self):
        """mcp_client.py should be the only Python module that talks to PowerShell via HTTP."""
        mcp_path = AGENT_DIR / "services" / "mcp_client.py"
        assert mcp_path.exists(), "mcp_client.py must exist as canonical PowerShell transport"

        with open(mcp_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "execute_powershell" in content, "mcp_client must have execute_powershell method"
        assert "/PowerShell" in content, "mcp_client must POST to /PowerShell endpoint"
        assert "localhost:8001" in content or "OC_MCP_BASE_URL" in content, \
            "mcp_client must target WMCP server"


class TestLegacyPathRemoval:
    """Verify legacy WSL fallback paths are removed."""

    def test_approval_service_no_wsl_fallback(self):
        """approval_service.py must not call WSL subprocess."""
        path = AGENT_DIR / "services" / "approval_service.py"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Should have the D-137 removal comment
        assert "D-137" in content, "approval_service must reference D-137"
        # Should not have active WSL subprocess call
        assert 'subprocess.run' not in content or 'wsl' not in content.split('subprocess.run')[1][:100] if 'subprocess.run' in content else True

    def test_telegram_bot_no_wsl_fallback(self):
        """telegram_bot.py _read_wsl_token must not call WSL subprocess."""
        path = AGENT_DIR / "telegram_bot.py"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "D-137" in content, "telegram_bot must reference D-137"
        # Extract _read_wsl_token function body and check no subprocess.run with wsl
        match = re.search(r'def _read_wsl_token\(.*?\):\s*\n(.*?)(?=\ndef |\Z)', content, re.DOTALL)
        assert match, "_read_wsl_token function must exist"
        func_body = match.group(1)
        # Should not have active subprocess.run call (comments/docstrings ok)
        code_lines = [line for line in func_body.split("\n")
                       if line.strip() and not line.strip().startswith("#") and not line.strip().startswith('"""') and '"""' not in line]
        has_subprocess_call = any("subprocess.run" in line for line in code_lines)
        assert not has_subprocess_call, "_read_wsl_token must not use subprocess.run"

    def test_health_api_no_wsl_fallback(self):
        """health_api.py must not have active WSL subprocess calls."""
        path = AGENT_DIR / "api" / "health_api.py"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "D-137" in content, "health_api must reference D-137"
        # No ["wsl" pattern should exist in non-comment code
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") or '"""' in stripped:
                continue
            assert '["wsl"' not in line, f"health_api.py:{i} has direct WSL subprocess call"


class TestBridgeContract:
    """Validate bridge contract structure from oc-bridge.ps1."""

    def test_bridge_script_exists(self):
        """Bridge entrypoint must exist."""
        bridge = PROJECT_ROOT / "bridge" / "oc-bridge.ps1"
        assert bridge.exists(), "oc-bridge.ps1 must exist"

    def test_bridge_has_allowlist_enforcement(self):
        """Bridge must enforce allowlist (fail-closed)."""
        bridge = PROJECT_ROOT / "bridge" / "oc-bridge.ps1"
        with open(bridge, "r", encoding="utf-8") as f:
            content = f.read()
        assert "allowlist" in content.lower()
        assert "SOURCE_NOT_ALLOWED" in content
        assert "Exit(2)" in content, "Must exit 2 on missing allowlist"

    def test_bridge_has_audit_logging(self):
        """Bridge must emit audit events."""
        bridge = PROJECT_ROOT / "bridge" / "oc-bridge.ps1"
        with open(bridge, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Write-BridgeAudit" in content
        assert "bridge-audit.jsonl" in content

    def test_bridge_has_timeout(self):
        """Bridge must have timeout for runtime invocations."""
        bridge = PROJECT_ROOT / "bridge" / "oc-bridge.ps1"
        with open(bridge, "r", encoding="utf-8") as f:
            content = f.read()
        assert "TimeoutSeconds" in content
        assert "TimedOut" in content
        assert "RUNTIME_UNAVAILABLE" in content

    def test_bridge_has_four_operations(self):
        """Bridge must support exactly 4 operations."""
        bridge = PROJECT_ROOT / "bridge" / "oc-bridge.ps1"
        with open(bridge, "r", encoding="utf-8") as f:
            content = f.read()
        for op in ["submit_task", "get_task_status", "cancel_task", "get_health"]:
            assert f"'{op}'" in content, f"Bridge must support {op}"

    def test_bridge_validates_input(self):
        """Bridge must validate required fields."""
        bridge = PROJECT_ROOT / "bridge" / "oc-bridge.ps1"
        with open(bridge, "r", encoding="utf-8") as f:
            content = f.read()
        assert "INVALID_INPUT" in content
        assert "Missing required fields" in content

    def test_bridge_has_fail_closed_default(self):
        """Bridge must fail closed on missing allowlist."""
        bridge = PROJECT_ROOT / "bridge" / "oc-bridge.ps1"
        with open(bridge, "r", encoding="utf-8") as f:
            content = f.read()
        assert "BRIDGE STARTUP FAILED" in content
        assert "Allowlist file not found" in content
        assert "Allowlist is empty" in content

    def test_bridge_exit_codes(self):
        """Bridge uses 0/1/2 exit code semantics."""
        bridge = PROJECT_ROOT / "bridge" / "oc-bridge.ps1"
        with open(bridge, "r", encoding="utf-8") as f:
            content = f.read()
        assert "exit 0" in content
        assert "exit 1" in content
        assert "Exit(2)" in content


class TestCanonicalPathInventory:
    """Verify canonical path components exist."""

    def test_wsl_wrappers_exist(self):
        """WSL bridge wrappers must exist."""
        wsl_dir = PROJECT_ROOT / "wsl"
        for wrapper in ["oc-bridge-call", "oc-bridge-submit", "oc-bridge-status",
                        "oc-bridge-cancel", "oc-bridge-health"]:
            assert (wsl_dir / wrapper).exists(), f"WSL wrapper {wrapper} must exist"

    def test_allowlist_exists(self):
        """Bridge allowlist config must exist (gitignored, skip in CI)."""
        allowlist = PROJECT_ROOT / "bridge" / "allowlist.json"
        if not allowlist.exists():
            import pytest
            pytest.skip("allowlist.json is gitignored (security), only present locally")

    def test_wmcp_degradation_policy_exists(self):
        """WMCP degradation policy must exist."""
        assert (PROJECT_ROOT / "config" / "policies" / "wmcp-degradation.yaml").exists()

    def test_tool_catalog_uses_bridge_wrappers(self):
        """Tool catalog submit_task/get_task_status must use bridge wrappers."""
        catalog = AGENT_DIR / "services" / "tool_catalog.py"
        with open(catalog, "r", encoding="utf-8") as f:
            content = f.read()
        assert "oc-bridge-submit" in content
        assert "oc-bridge-status" in content

    def test_decision_record_exists(self):
        """D-137 decision record must exist."""
        d137 = PROJECT_ROOT / "docs" / "decisions" / "D-137-wsl2-powershell-bridge-contract.md"
        assert d137.exists(), "D-137 decision record must exist"
        with open(d137, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Frozen" in content
        assert "fail-closed" in content.lower()
