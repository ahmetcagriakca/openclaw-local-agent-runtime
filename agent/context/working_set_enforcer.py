"""Working Set Enforcer — intercepts filesystem tool calls and enforces bounded access."""
from dataclasses import dataclass
from context.working_set import WorkingSet
from context.path_resolver import (
    resolve_canonical, is_path_within, is_path_under_directory, is_path_forbidden
)


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


def enforce_working_set(tool_name: str, tool_params: dict,
                        working_set: WorkingSet, tool_governance: dict) -> EnforcementResult:
    """Check if a tool call is allowed by the working set.

    Called BEFORE risk engine, AFTER tool gateway.
    Returns EnforcementResult with .allowed and .message.
    """
    # Non-filesystem tools: pass through
    if not tool_governance.get("filesystemTouching", False):
        return EnforcementResult(allowed=True)

    # Extract path from tool params
    raw_path = extract_path_from_params(tool_name, tool_params)
    if raw_path is None:
        return EnforcementResult(
            allowed=False,
            message="POLICY: Cannot determine target path for filesystem operation."
        )

    # Canonical resolution (D-049)
    resolved = resolve_canonical(raw_path)
    if resolved is None:
        return EnforcementResult(
            allowed=False,
            message="POLICY: Path resolution failed. Access denied."
        )

    # Check forbidden zones first
    if is_path_forbidden(resolved, working_set.forbidden_directories,
                         working_set.forbidden_patterns):
        return EnforcementResult(
            allowed=False,
            message=f"POLICY: Path '{resolved}' is in a forbidden zone. Access denied."
        )

    # Mutation surface check (D-045)
    surface = tool_governance.get("mutationSurface", "none")
    if surface == "code":
        return _check_write_authorization(resolved, tool_name, working_set)

    # Read authorization
    return _check_read_authorization(resolved, tool_name, working_set)


def _check_read_authorization(resolved: str, tool_name: str,
                               working_set: WorkingSet) -> EnforcementResult:
    """Check if a read operation is authorized."""
    files = working_set.files
    budget = working_set.budget

    # Directory listing tools
    if tool_name in ("list_directory", "search_files"):
        # Check directory access
        if not is_path_within(resolved, files.directory_list) and \
           not is_path_under_directory(resolved, files.directory_list):
            return EnforcementResult(
                allowed=False,
                message=f"POLICY: Directory '{resolved}' is not in the allowed directory list."
            )
        if not budget.consume_directory_read():
            return EnforcementResult(
                allowed=False,
                message="POLICY: Directory read budget exhausted for this stage."
            )
        return EnforcementResult(allowed=True)

    # File reading tools (read_file, find_in_files)
    # Allow if path is in read_only, read_write, or under an allowed directory
    all_readable = files.read_only + files.read_write + files.generated_outputs
    if is_path_within(resolved, all_readable) or \
       is_path_under_directory(resolved, files.directory_list):
        if not budget.consume_file_read():
            return EnforcementResult(
                allowed=False,
                message="POLICY: File read budget exhausted for this stage."
            )
        return EnforcementResult(allowed=True)

    return EnforcementResult(
        allowed=False,
        message=f"POLICY: File '{resolved}' is not in the allowed read set."
    )


def _check_write_authorization(resolved: str, tool_name: str,
                                working_set: WorkingSet) -> EnforcementResult:
    """Check if a write operation is authorized."""
    files = working_set.files

    # Check read_write (existing files) and creatable (new files)
    all_writable = files.read_write + files.creatable + files.generated_outputs
    if is_path_within(resolved, all_writable) or \
       is_path_under_directory(resolved, [p for p in files.generated_outputs]):
        return EnforcementResult(allowed=True)

    return EnforcementResult(
        allowed=False,
        message=f"POLICY: File '{resolved}' is not in the allowed write set."
    )
