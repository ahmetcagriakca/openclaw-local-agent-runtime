"""Working Set Enforcer — intercepts filesystem tool calls and enforces bounded access."""
from dataclasses import dataclass

from context.path_resolver import (
    is_path_forbidden,
    is_path_under_directory,
    is_path_within,
    resolve_canonical,
)
from context.policy_telemetry import emit_policy_event
from context.working_set import WorkingSet


@dataclass
class EnforcementResult:
    """Result of a working set enforcement check."""
    allowed: bool
    message: str = ""


# Maps tool names to the parameter key that contains the target path
_PATH_PARAM_MAP = {
    "read_file": "path",
    "list_directory": "path",
    "search_files": "path",
    "find_in_files": "path",
    "write_file": "filename",  # write_file uses filename (relative to results dir)
}

# write_file always writes to this base directory
_WRITE_FILE_BASE = "C:\\Users\\AKCA\\oc\\results"


def extract_path_from_params(tool_name: str, tool_params: dict) -> str | None:
    """Extract the filesystem path from tool parameters."""
    param_key = _PATH_PARAM_MAP.get(tool_name)
    if not param_key:
        return None

    raw = tool_params.get(param_key)
    if not raw:
        return None

    # write_file uses filename only — resolve against results dir
    if tool_name == "write_file":
        import os
        return os.path.join(_WRITE_FILE_BASE, raw)

    return raw


def _expansion_hint(working_set: WorkingSet, expansion_broker) -> str:
    """Build expansion budget hint for deny messages."""
    if not expansion_broker:
        return ""
    role = working_set.role
    role_max = {"developer": 8, "tester": 3, "reviewer": 5, "analyst": 999, "architect": 999}
    max_allowed = role_max.get(role, 0)
    if max_allowed == 0:
        return ""
    prior = sum(
        1 for r in expansion_broker.requests
        if r["requestingRole"] == role and r["decision"] == "granted"
    )
    remaining = max(0, max_allowed - prior)
    return f" To request access, provide a reason via expansion request. Remaining expansion budget: {remaining}/{max_allowed}."


def _telemetry_base(tool_name: str, working_set: WorkingSet) -> dict:
    """Common telemetry fields."""
    return {"tool": tool_name, "role": working_set.role, "stage_id": working_set.stage_id}


def enforce_working_set(tool_name: str, tool_params: dict,
                        working_set: WorkingSet, tool_governance: dict,
                        expansion_broker=None) -> EnforcementResult:
    """Check if a tool call is allowed by the working set.

    Called BEFORE risk engine, AFTER tool gateway.
    Returns EnforcementResult with .allowed and .message.
    """
    base = _telemetry_base(tool_name, working_set)

    # Non-filesystem tools: pass through (no telemetry — too noisy)
    if not tool_governance.get("filesystemTouching", False):
        return EnforcementResult(allowed=True)

    # Extract path from tool params
    raw_path = extract_path_from_params(tool_name, tool_params)
    if raw_path is None:
        msg = "POLICY: Cannot determine target path for filesystem operation."
        emit_policy_event("policy_denied", {**base, "reason": "no_path_param", "raw_path": None})
        return EnforcementResult(allowed=False, message=msg)

    # Canonical resolution (D-049)
    resolved = resolve_canonical(raw_path)
    if resolved is None:
        msg = "POLICY: Path resolution failed. Access denied."
        emit_policy_event("path_resolution_failed", {**base, "raw_path": raw_path})
        return EnforcementResult(allowed=False, message=msg)

    # Check forbidden zones first
    if is_path_forbidden(resolved, working_set.forbidden_directories,
                         working_set.forbidden_patterns):
        msg = f"POLICY: Path '{resolved}' is in a forbidden zone. Access denied."
        emit_policy_event("policy_denied", {**base, "reason": "forbidden_zone", "resolved_path": resolved})
        return EnforcementResult(allowed=False, message=msg)

    # Mutation surface check (D-045)
    surface = tool_governance.get("mutationSurface", "none")
    role = working_set.role

    # D-055: mutation_surface_mismatch — role vs surface authorization
    if surface == "system" and role != "remote-operator":
        msg = f"POLICY: Tool '{tool_name}' has system mutation surface, requires remote-operator role (current: {role})."
        emit_policy_event("mutation_surface_mismatch", {
            **base, "expected_role": "remote-operator",
            "mutation_surface": "system", "resolved_path": resolved
        })
        return EnforcementResult(allowed=False, message=msg)

    if surface == "code" and role not in ("developer", "remote-operator", "executor"):
        msg = f"POLICY: Tool '{tool_name}' has code mutation surface, requires developer role (current: {role})."
        emit_policy_event("mutation_surface_mismatch", {
            **base, "expected_role": "developer",
            "mutation_surface": "code", "resolved_path": resolved
        })
        return EnforcementResult(allowed=False, message=msg)

    if surface == "code":
        return _check_write_authorization(resolved, tool_name, working_set, base, expansion_broker)

    # Read authorization
    return _check_read_authorization(resolved, tool_name, working_set, base, expansion_broker)


def _check_read_authorization(resolved: str, tool_name: str,
                               working_set: WorkingSet, base: dict,
                               expansion_broker=None) -> EnforcementResult:
    """Check if a read operation is authorized."""
    files = working_set.files
    budget = working_set.budget

    # Directory listing tools
    if tool_name in ("list_directory", "search_files"):
        if not is_path_within(resolved, files.directory_list) and \
           not is_path_under_directory(resolved, files.directory_list):
            msg = f"POLICY: Directory '{resolved}' is not in the allowed directory list."
            msg += _expansion_hint(working_set, expansion_broker)
            emit_policy_event("policy_denied", {**base, "reason": "directory_scope", "resolved_path": resolved})
            return EnforcementResult(allowed=False, message=msg)
        if not budget.consume_directory_read():
            msg = "POLICY: Directory read budget exhausted for this stage."
            emit_policy_event("budget_exhausted", {**base, "budget_type": "directory_read", "resolved_path": resolved})
            emit_policy_event("policy_soft_denied", {**base, "reason": "budget_exhausted", "budget_type": "directory_read"})
            return EnforcementResult(allowed=False, message=msg)
        emit_policy_event("filesystem_tool_allowed", {**base, "resolved_path": resolved})
        return EnforcementResult(allowed=True)

    # File reading tools (read_file, find_in_files)
    all_readable = files.read_only + files.read_write + files.generated_outputs
    if is_path_within(resolved, all_readable) or \
       is_path_under_directory(resolved, files.directory_list):
        if not budget.consume_file_read():
            msg = "POLICY: File read budget exhausted for this stage."
            emit_policy_event("budget_exhausted", {**base, "budget_type": "file_read", "resolved_path": resolved})
            emit_policy_event("policy_soft_denied", {**base, "reason": "budget_exhausted", "budget_type": "file_read"})
            return EnforcementResult(allowed=False, message=msg)
        emit_policy_event("filesystem_tool_allowed", {**base, "resolved_path": resolved})
        return EnforcementResult(allowed=True)

    msg = f"POLICY: File '{resolved}' is not in the allowed read set."
    msg += _expansion_hint(working_set, expansion_broker)
    emit_policy_event("policy_denied", {**base, "reason": "read_scope", "resolved_path": resolved})
    return EnforcementResult(allowed=False, message=msg)


def _check_write_authorization(resolved: str, tool_name: str,
                                working_set: WorkingSet, base: dict,
                                expansion_broker=None) -> EnforcementResult:
    """Check if a write operation is authorized."""
    files = working_set.files

    all_writable = files.read_write + files.creatable + files.generated_outputs
    if is_path_within(resolved, all_writable) or \
       is_path_under_directory(resolved, [p for p in files.generated_outputs]):
        emit_policy_event("filesystem_tool_allowed", {**base, "resolved_path": resolved, "surface": "code"})
        return EnforcementResult(allowed=True)

    msg = f"POLICY: File '{resolved}' is not in the allowed write set."
    msg += _expansion_hint(working_set, expansion_broker)
    emit_policy_event("policy_denied", {**base, "reason": "write_scope", "resolved_path": resolved, "surface": "code"})
    return EnforcementResult(allowed=False, message=msg)
