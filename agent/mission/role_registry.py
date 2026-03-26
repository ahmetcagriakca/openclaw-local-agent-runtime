"""Role registry — 9 canonical roles with tool policies, budgets, and discovery rights."""

ROLE_REGISTRY = {
    "product-owner": {
        "displayName": "Product Owner",
        "defaultSkill": "requirement_structuring",
        "allowedSkills": ["requirement_structuring", "summary_compression"],
        "forbiddenSkills": ["repository_discovery", "controlled_execution"],
        "toolPolicy": "no_tools",
        "allowedTools": [],
        "defaultModelTier": 2,
        "preferredModel": "gpt-4o",
        "discoveryRights": "forbidden",
        "maxFileReads": 0,
        "maxDirectoryReads": 0,
        "canExpand": False
    },
    "analyst": {
        "displayName": "Analyst",
        "defaultSkill": "repository_discovery",
        "allowedSkills": ["repository_discovery", "summary_compression",
                          "recovery_triage"],
        "forbiddenSkills": ["controlled_execution"],
        "toolPolicy": "read_only_13",
        "allowedTools": ["read_file", "list_directory", "search_files",
                         "find_in_files", "get_system_info",
                         "get_system_health", "check_runtime_task", "mcp_status",
                         "list_processes", "get_process_details",
                         "get_network_info", "list_scheduled_tasks"],
        "defaultModelTier": 2,
        "preferredModel": "claude-sonnet",
        "discoveryRights": "primary",
        "maxFileReads": 30,
        "maxDirectoryReads": 15,
        "canExpand": True
    },
    "architect": {
        "displayName": "Architect",
        "defaultSkill": "architecture_synthesis",
        "allowedSkills": ["architecture_synthesis", "repository_discovery",
                          "summary_compression"],
        "forbiddenSkills": ["controlled_execution"],
        "toolPolicy": "read_only_12",
        "allowedTools": ["read_file", "list_directory", "search_files",
                         "find_in_files", "get_system_info",
                         "get_system_health", "check_runtime_task", "mcp_status",
                         "list_processes", "get_process_details",
                         "get_network_info", "list_scheduled_tasks"],
        "defaultModelTier": 2,
        "preferredModel": "claude-sonnet",
        "discoveryRights": "primary",
        "maxFileReads": 15,
        "maxDirectoryReads": 10,
        "canExpand": True
    },
    "project-manager": {
        "displayName": "Project Manager",
        "defaultSkill": "work_breakdown",
        "allowedSkills": ["work_breakdown", "summary_compression"],
        "forbiddenSkills": ["repository_discovery", "controlled_execution"],
        "toolPolicy": "no_tools",
        "allowedTools": [],
        "defaultModelTier": 2,
        "preferredModel": "gpt-4o",
        "discoveryRights": "forbidden",
        "maxFileReads": 0,
        "maxDirectoryReads": 0,
        "canExpand": False
    },
    "developer": {
        "displayName": "Developer",
        "defaultSkill": "targeted_code_change",
        "allowedSkills": ["targeted_code_change"],
        "forbiddenSkills": ["repository_discovery", "controlled_execution"],
        "toolPolicy": "dev_14",
        "allowedTools": ["read_file", "write_file", "list_directory",
                         "search_files", "find_in_files", "get_system_info",
                         "take_screenshot", "check_runtime_task",
                         "list_processes", "get_process_details", "mcp_status",
                         "get_system_health", "get_network_info",
                         "list_scheduled_tasks"],
        "defaultModelTier": 2,
        "preferredModel": "claude-sonnet",
        "discoveryRights": "neighborhood",
        "maxFileReads": 20,
        "maxDirectoryReads": 5,
        "canExpand": True,
        "maxExpansions": 8
    },
    "tester": {
        "displayName": "Tester",
        "defaultSkill": "test_validation",
        "allowedSkills": ["test_validation", "quality_review",
                          "summary_compression"],
        "forbiddenSkills": ["repository_discovery", "controlled_execution"],
        "toolPolicy": "read_only_12",
        "allowedTools": ["read_file", "list_directory", "search_files",
                         "find_in_files", "get_system_info",
                         "get_system_health", "check_runtime_task", "mcp_status",
                         "list_processes", "get_process_details",
                         "get_network_info", "list_scheduled_tasks"],
        "defaultModelTier": 2,
        "preferredModel": "claude-sonnet",
        "discoveryRights": "test_surface",
        "maxFileReads": 15,
        "maxDirectoryReads": 5,
        "canExpand": True,
        "maxExpansions": 3
    },
    "reviewer": {
        "displayName": "Reviewer",
        "defaultSkill": "quality_review",
        "allowedSkills": ["quality_review", "summary_compression"],
        "forbiddenSkills": ["repository_discovery", "controlled_execution"],
        "toolPolicy": "read_only_4",
        "allowedTools": ["read_file", "list_directory", "search_files",
                         "find_in_files"],
        "defaultModelTier": 2,
        "preferredModel": "claude-sonnet",
        "discoveryRights": "diff_centric",
        "maxFileReads": 12,
        "maxDirectoryReads": 3,
        "canExpand": True,
        "maxExpansions": 5
    },
    "manager": {
        "displayName": "Manager",
        "defaultSkill": "summary_compression",
        "allowedSkills": ["summary_compression", "recovery_triage",
                          "quality_review"],
        "forbiddenSkills": ["repository_discovery", "controlled_execution"],
        "toolPolicy": "no_tools",
        "allowedTools": [],
        "defaultModelTier": 2,
        "preferredModel": "gpt-4o",
        "discoveryRights": "forbidden",
        "maxFileReads": 0,
        "maxDirectoryReads": 0,
        "canExpand": False
    },
    "remote-operator": {
        "displayName": "Remote Operator",
        "defaultSkill": "controlled_execution",
        "allowedSkills": ["controlled_execution", "recovery_triage"],
        "forbiddenSkills": ["repository_discovery", "targeted_code_change"],
        "toolPolicy": "all_24",
        "allowedTools": None,
        "defaultModelTier": 2,
        "preferredModel": "gpt-4o",
        "discoveryRights": "forbidden",
        "maxFileReads": 5,
        "maxDirectoryReads": 2,
        "canExpand": False
    }
}

# Alias table (D-048 backward compat)
_ROLE_ALIASES = {
    "executor": "remote-operator",
    "po": "product-owner",
    "pm": "project-manager",
}


def resolve_role(role_name: str) -> str:
    """Resolve alias to canonical role name."""
    return _ROLE_ALIASES.get(role_name, role_name)


def get_role(role_name: str) -> dict | None:
    """Get role definition by name or alias."""
    canonical = resolve_role(role_name)
    return ROLE_REGISTRY.get(canonical)


def get_role_tool_policy(role_name: str) -> list | None:
    """Return allowed tools for role. None means all tools."""
    role = get_role(role_name)
    if not role:
        return []
    return role.get("allowedTools")


def validate_role_registry() -> list[str]:
    """Startup check: all roles have required fields."""
    required = ["displayName", "defaultSkill", "allowedSkills",
                "toolPolicy", "defaultModelTier", "discoveryRights"]
    errors = []
    for name, role in ROLE_REGISTRY.items():
        for field in required:
            if field not in role:
                errors.append(f"Role '{name}': missing {field}")
    return errors
