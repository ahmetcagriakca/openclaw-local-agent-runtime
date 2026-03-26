"""Skill contracts — machine-readable contracts for each specialist skill."""

SKILL_CONTRACTS = {
    "requirement_structuring": {
        "owningRoles": ["product-owner"],
        "secondaryRoles": ["analyst"],
        "forbiddenRoles": ["pm", "developer", "tester", "reviewer",
                           "manager", "remote-operator", "architect"],
        "inputArtifacts": [
            {"type": "user_message", "contextTier": "D"}
        ],
        "outputArtifact": "requirements_brief",
        "allowedTools": [],
        "forbiddenTools": ["all"],
        "budgets": {
            "maxTurns": 3,
            "maxFileReads": 0,
            "maxDirectoryReads": 0,
            "maxToolCalls": 0,
            "maxWorkingSetExpansions": 0
        },
        "costClass": "minimal",
        "defaultModelTier": 2,
        "preferredModels": ["gpt-4o"],
        "escalationTier": None,
        "claudeJustified": False
    },
    "repository_discovery": {
        "owningRoles": ["analyst", "architect"],
        "secondaryRoles": [],
        "forbiddenRoles": ["product-owner", "pm", "developer", "tester",
                           "reviewer", "manager", "remote-operator"],
        "inputArtifacts": [
            {"type": "requirements_brief", "contextTier": "D"}
        ],
        "outputArtifact": "discovery_map",
        "allowedTools": ["read_file", "list_directory", "search_files",
                         "find_in_files", "get_system_info",
                         "get_system_health", "check_runtime_task", "mcp_status",
                         "list_processes", "get_process_details",
                         "get_network_info", "list_scheduled_tasks"],
        "forbiddenTools": ["write_file", "set_clipboard", "open_application",
                           "open_url", "close_application", "lock_screen",
                           "system_shutdown", "system_restart",
                           "submit_runtime_task", "mcp_restart",
                           "take_screenshot"],
        "budgets": {
            "maxTurns": 10,
            "maxFileReads": 30,
            "maxDirectoryReads": 15,
            "maxToolCalls": 25,
            "maxWorkingSetExpansions": 999
        },
        "costClass": "high",
        "defaultModelTier": 2,
        "preferredModels": ["claude-sonnet"],
        "escalationTier": 4,
        "escalateOnlyIf": ["repo_over_50_files"],
        "claudeJustified": True
    },
    "architecture_synthesis": {
        "owningRoles": ["architect"],
        "secondaryRoles": ["analyst"],
        "forbiddenRoles": ["product-owner", "pm", "developer", "tester",
                           "reviewer", "manager", "remote-operator"],
        "inputArtifacts": [
            {"type": "requirements_brief", "contextTier": "D"},
            {"type": "analysis_report", "contextTier": "D"},
            {"type": "discovery_map", "contextTier": "D"}
        ],
        "outputArtifact": "technical_design",
        "allowedTools": ["read_file", "list_directory", "search_files",
                         "find_in_files"],
        "forbiddenTools": ["write_file"],
        "budgets": {
            "maxTurns": 8,
            "maxFileReads": 15,
            "maxDirectoryReads": 10,
            "maxToolCalls": 25,
            "maxWorkingSetExpansions": 999
        },
        "costClass": "high",
        "defaultModelTier": 2,
        "preferredModels": ["claude-sonnet"],
        "escalationTier": 4,
        "escalateOnlyIf": ["xl_complexity"],
        "claudeJustified": True
    },
    "work_breakdown": {
        "owningRoles": ["project-manager"],
        "secondaryRoles": ["architect"],
        "forbiddenRoles": ["product-owner", "analyst", "developer",
                           "tester", "reviewer", "manager", "remote-operator"],
        "inputArtifacts": [
            {"type": "technical_design", "contextTier": "D"},
            {"type": "requirements_brief", "contextTier": "B"},
            {"type": "discovery_map", "contextTier": "B"}
        ],
        "outputArtifact": "work_plan",
        "allowedTools": [],
        "forbiddenTools": ["all"],
        "budgets": {
            "maxTurns": 3,
            "maxFileReads": 0,
            "maxDirectoryReads": 0,
            "maxToolCalls": 0,
            "maxWorkingSetExpansions": 0
        },
        "costClass": "minimal",
        "defaultModelTier": 2,
        "preferredModels": ["gpt-4o"],
        "escalationTier": None,
        "claudeJustified": False
    },
    "targeted_code_change": {
        "owningRoles": ["developer"],
        "secondaryRoles": [],
        "forbiddenRoles": ["product-owner", "analyst", "architect", "pm",
                           "tester", "reviewer", "manager", "remote-operator"],
        "inputArtifacts": [
            {"type": "technical_design", "contextTier": "C"},
            {"type": "work_plan", "contextTier": "C"},
            {"type": "discovery_map", "contextTier": "C"}
        ],
        "outputArtifact": "code_delivery",
        "allowedTools": ["read_file", "write_file", "list_directory",
                         "search_files", "find_in_files", "get_system_info",
                         "take_screenshot", "check_runtime_task",
                         "list_processes", "get_process_details", "mcp_status",
                         "get_system_health", "get_network_info",
                         "list_scheduled_tasks"],
        "forbiddenTools": ["set_clipboard", "open_application", "open_url",
                           "submit_runtime_task", "close_application",
                           "system_shutdown", "system_restart", "mcp_restart",
                           "lock_screen"],
        "budgets": {
            "maxTurns": 15,
            "maxFileReads": 20,
            "maxDirectoryReads": 5,
            "maxToolCalls": 40,
            "maxWorkingSetExpansions": 3
        },
        "workingSetPolicy": {
            "writeTargetsOnly": True,
            "writeAuthorizationFields": ["readWrite", "creatable",
                                          "generatedOutputs"],
            "searchRoots": "directoryListOnly"
        },
        "costClass": "high",
        "defaultModelTier": 2,
        "preferredModels": ["claude-sonnet", "gpt-4o"],
        "escalationTier": 4,
        "escalateOnlyIf": ["quality_gate_failed_twice", "xl_complexity"],
        "claudeJustified": True
    },
    "test_validation": {
        "owningRoles": ["tester"],
        "secondaryRoles": ["reviewer"],
        "forbiddenRoles": ["product-owner", "analyst", "architect", "pm",
                           "developer", "manager", "remote-operator"],
        "inputArtifacts": [
            {"type": "code_delivery", "contextTier": "D"},
            {"type": "requirements_brief", "contextTier": "C"},
            {"type": "technical_design", "contextTier": "C"}
        ],
        "outputArtifact": "test_report",
        "allowedTools": ["read_file", "list_directory", "search_files",
                         "find_in_files", "get_system_info",
                         "get_system_health", "check_runtime_task", "mcp_status",
                         "list_processes", "get_process_details",
                         "get_network_info", "list_scheduled_tasks"],
        "forbiddenTools": ["write_file", "take_screenshot"],
        "budgets": {
            "maxTurns": 10,
            "maxFileReads": 15,
            "maxDirectoryReads": 5,
            "maxToolCalls": 25,
            "maxWorkingSetExpansions": 3
        },
        "costClass": "medium",
        "defaultModelTier": 2,
        "preferredModels": ["claude-sonnet"],
        "escalationTier": None,
        "claudeJustified": True
    },
    "quality_review": {
        "owningRoles": ["reviewer"],
        "secondaryRoles": ["tester", "manager"],
        "forbiddenRoles": ["product-owner", "analyst", "architect", "pm",
                           "developer", "remote-operator"],
        "inputArtifacts": [
            {"type": "code_delivery", "contextTier": "D"},
            {"type": "technical_design", "contextTier": "C"},
            {"type": "test_report", "contextTier": "D"},
            {"type": "discovery_map", "contextTier": "B"}
        ],
        "outputArtifact": "review_decision",
        "allowedTools": ["read_file", "list_directory", "search_files",
                         "find_in_files"],
        "forbiddenTools": ["write_file"],
        "budgets": {
            "maxTurns": 8,
            "maxFileReads": 12,
            "maxDirectoryReads": 3,
            "maxToolCalls": 25,
            "maxWorkingSetExpansions": 5
        },
        "costClass": "high",
        "defaultModelTier": 2,
        "preferredModels": ["claude-sonnet"],
        "escalationTier": 4,
        "escalateOnlyIf": ["security_critical", "architectural_review"],
        "claudeJustified": True
    },
    "controlled_execution": {
        "owningRoles": ["remote-operator"],
        "secondaryRoles": [],
        "forbiddenRoles": ["product-owner", "analyst", "architect", "pm",
                           "developer", "tester", "reviewer", "manager"],
        "inputArtifacts": [
            {"type": "execution_payload", "contextTier": "D"}
        ],
        "outputArtifact": "execution_result",
        "allowedTools": "all",
        "forbiddenTools": [],
        "budgets": {
            "maxTurns": 15,
            "maxFileReads": 5,
            "maxDirectoryReads": 2,
            "maxToolCalls": 25,
            "maxWorkingSetExpansions": 0
        },
        "costClass": "variable",
        "defaultModelTier": 2,
        "preferredModels": ["gpt-4o"],
        "escalationTier": None,
        "claudeJustified": False
    },
    "summary_compression": {
        "owningRoles": ["manager"],
        "secondaryRoles": ["product-owner", "analyst", "architect",
                           "project-manager", "tester", "reviewer"],
        "forbiddenRoles": [],
        "inputArtifacts": [
            {"type": "any", "contextTier": "D"}
        ],
        "outputArtifact": "artifact_summary",
        "allowedTools": [],
        "forbiddenTools": ["all"],
        "budgets": {
            "maxTurns": 2,
            "maxFileReads": 0,
            "maxDirectoryReads": 0,
            "maxToolCalls": 0,
            "maxWorkingSetExpansions": 0
        },
        "costClass": "minimal",
        "defaultModelTier": 1,
        "preferredModels": ["ollama-local"],
        "escalationTier": 2,
        "escalateOnlyIf": ["summary_rejected_by_consumer"],
        "claudeJustified": False
    },
    "recovery_triage": {
        "owningRoles": ["manager"],
        "secondaryRoles": ["analyst", "remote-operator"],
        "forbiddenRoles": ["product-owner", "pm", "developer", "tester",
                           "reviewer", "architect"],
        "inputArtifacts": [
            {"type": "failed_stage_artifact", "contextTier": "D"},
            {"type": "mission_state", "contextTier": "D"},
            {"type": "error_context", "contextTier": "D"}
        ],
        "outputArtifact": "recovery_decision",
        "allowedTools": ["read_file", "get_system_health", "mcp_status",
                         "list_processes"],
        "forbiddenTools": ["write_file"],
        "budgets": {
            "maxTurns": 5,
            "maxFileReads": 5,
            "maxDirectoryReads": 2,
            "maxToolCalls": 10,
            "maxWorkingSetExpansions": 3
        },
        "costClass": "medium",
        "defaultModelTier": 2,
        "preferredModels": ["claude-sonnet"],
        "escalationTier": 4,
        "escalateOnlyIf": ["complex_cascading_failure"],
        "claudeJustified": True
    }
}


def get_skill_contract(skill_name: str) -> dict | None:
    """Get a skill contract by name."""
    return SKILL_CONTRACTS.get(skill_name)


def validate_role_skill(role: str, skill_name: str) -> tuple[bool, str]:
    """Check if a role may invoke a skill. Returns (allowed, reason)."""
    contract = SKILL_CONTRACTS.get(skill_name)
    if not contract:
        return False, f"Unknown skill: {skill_name}"
    if role in contract.get("forbiddenRoles", []):
        return False, f"Role '{role}' is forbidden from skill '{skill_name}'"
    if role in contract["owningRoles"] or role in contract.get("secondaryRoles", []):
        return True, "allowed"
    return False, f"Role '{role}' is not authorized for skill '{skill_name}'"


def get_allowed_tools(skill_name: str) -> list | None:
    """Get allowed tool names for a skill. None means all tools."""
    contract = SKILL_CONTRACTS.get(skill_name)
    if not contract:
        return []
    tools = contract.get("allowedTools", [])
    if tools == "all":
        return None
    return tools


def get_forbidden_tools(skill_name: str) -> list:
    """Get forbidden tool names for a skill."""
    contract = SKILL_CONTRACTS.get(skill_name)
    if not contract:
        return []
    return contract.get("forbiddenTools", [])


def get_skill_budgets(skill_name: str) -> dict:
    """Get budget limits for a skill."""
    contract = SKILL_CONTRACTS.get(skill_name)
    if not contract:
        return {}
    return contract.get("budgets", {})


def validate_all_contracts() -> list[str]:
    """Startup check: all contracts have required fields."""
    required = ["owningRoles", "outputArtifact", "allowedTools",
                "budgets", "defaultModelTier"]
    errors = []
    for name, contract in SKILL_CONTRACTS.items():
        for field in required:
            if field not in contract:
                errors.append(f"{name}: missing {field}")
    return errors
