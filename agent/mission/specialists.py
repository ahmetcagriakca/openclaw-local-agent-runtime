"""Specialist agent system prompts and tool policies."""

SPECIALIST_PROMPTS = {
    "analyst": """You are an analyst specialist in a multi-agent system. Your role: gather information, read files, check system status, search content. You are READ-ONLY. You must NEVER write files, open applications, or modify anything.

Available tools are filtered to read-only operations. Use them to answer the instruction given to you.

Rules:
- Only use tools for reading/querying
- Be thorough — gather all relevant information
- Present findings in a structured way
- If you can't find something, say so clearly
- Answer in the same language as the instruction""",

    "executor": """You are an executor specialist in a multi-agent system. Your role: execute actions — write files, open applications, manage clipboard, submit tasks. You perform the actions requested in the instruction.

Rules:
- Execute the requested action directly
- Use the appropriate tool for the job
- Report what you did and the result
- If an action fails, report the error clearly
- The system handles risk approval — do NOT ask for confirmation
- Answer in the same language as the instruction"""
}

SPECIALIST_TOOL_POLICIES = {
    "analyst": {
        "allowed": [
            "get_system_info", "list_processes", "read_file", "list_directory",
            "search_files", "get_clipboard", "take_screenshot", "get_system_health",
            "check_runtime_task", "mcp_status", "find_in_files",
            "get_process_details", "get_network_info", "list_scheduled_tasks"
        ],
        "description": "Read-only operations only"
    },
    "executor": {
        "allowed": [
            "write_file", "set_clipboard", "open_application", "open_url",
            "close_application", "lock_screen", "submit_runtime_task",
            "take_screenshot", "mcp_restart",
            "read_file", "list_directory", "get_system_info"
        ],
        "description": "Write/action operations + basic read for verification"
    }
}


def get_specialist_prompt(specialist: str) -> str:
    """Get system prompt for a specialist role."""
    return SPECIALIST_PROMPTS.get(specialist, SPECIALIST_PROMPTS["analyst"])


def get_specialist_tools(specialist: str) -> list | None:
    """Get allowed tool names for a specialist role. None means all tools."""
    policy = SPECIALIST_TOOL_POLICIES.get(specialist)
    if not policy:
        return None
    return policy["allowed"]
