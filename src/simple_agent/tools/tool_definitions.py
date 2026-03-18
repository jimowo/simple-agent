"""Centralized tool definitions for the agent runtime."""

from typing import Any, Dict, Iterable, List


def _tool(name: str, description: str, properties: Dict[str, Any], required: List[str] | None = None) -> Dict[str, Any]:
    """Create a normalized tool definition."""
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    }


TOOL_SPECS: Dict[str, Dict[str, Any]] = {
    "bash": _tool(
        "bash",
        "Run a shell command.",
        {"command": {"type": "string"}},
        ["command"],
    ),
    "read_file": _tool(
        "read_file",
        "Read file contents.",
        {"path": {"type": "string"}, "limit": {"type": "integer"}},
        ["path"],
    ),
    "write_file": _tool(
        "write_file",
        "Write content to file.",
        {"path": {"type": "string"}, "content": {"type": "string"}},
        ["path", "content"],
    ),
    "edit_file": _tool(
        "edit_file",
        "Replace exact text in file.",
        {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
        },
        ["path", "old_text", "new_text"],
    ),
    "glob": _tool(
        "glob",
        "Find files by glob pattern.",
        {"pattern": {"type": "string"}, "path": {"type": "string"}},
        ["pattern"],
    ),
    "grep": _tool(
        "grep",
        "Search for patterns in file contents using regex.",
        {
            "pattern": {"type": "string"},
            "path": {"type": "string"},
            "file_pattern": {"type": "string"},
            "ignore_case": {"type": "boolean"},
        },
        ["pattern"],
    ),
    "TodoWrite": _tool(
        "TodoWrite",
        "Update task tracking list.",
        {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                        },
                        "activeForm": {"type": "string"},
                    },
                    "required": ["content", "status", "activeForm"],
                },
            }
        },
        ["items"],
    ),
    "task": _tool(
        "task",
        "Spawn a subagent for isolated exploration or work.",
        {
            "prompt": {"type": "string"},
            "agent_type": {"type": "string", "enum": ["Explore", "general-purpose"]},
        },
        ["prompt"],
    ),
    "load_skill": _tool(
        "load_skill",
        "Load specialized knowledge by name.",
        {"name": {"type": "string"}},
        ["name"],
    ),
    "compress": _tool(
        "compress",
        "Manually compress conversation context.",
        {},
    ),
    "background_run": _tool(
        "background_run",
        "Run command in background thread.",
        {"command": {"type": "string"}, "timeout": {"type": "integer"}},
        ["command"],
    ),
    "check_background": _tool(
        "check_background",
        "Check background task status.",
        {"task_id": {"type": "string"}},
    ),
    "web_fetch": _tool(
        "web_fetch",
        "Fetch content from a URL.",
        {"url": {"type": "string"}, "timeout": {"type": "integer"}},
        ["url"],
    ),
    "web_search": _tool(
        "web_search",
        "Search the web for information.",
        {
            "query": {"type": "string"},
            "num_results": {"type": "integer"},
            "timeout": {"type": "integer"},
        },
        ["query"],
    ),
    "task_create": _tool(
        "task_create",
        "Create a persistent file task.",
        {"subject": {"type": "string"}, "description": {"type": "string"}},
        ["subject"],
    ),
    "task_get": _tool(
        "task_get",
        "Get task details by ID.",
        {"task_id": {"type": "integer"}},
        ["task_id"],
    ),
    "task_update": _tool(
        "task_update",
        "Update task status or dependencies.",
        {
            "task_id": {"type": "integer"},
            "status": {
                "type": "string",
                "enum": ["pending", "in_progress", "completed", "deleted"],
            },
            "add_blocked_by": {"type": "array", "items": {"type": "integer"}},
            "add_blocks": {"type": "array", "items": {"type": "integer"}},
        },
        ["task_id"],
    ),
    "task_list": _tool(
        "task_list",
        "List all tasks.",
        {},
    ),
    "spawn_teammate": _tool(
        "spawn_teammate",
        "Spawn a persistent autonomous teammate.",
        {
            "name": {"type": "string"},
            "role": {"type": "string"},
            "prompt": {"type": "string"},
        },
        ["name", "role", "prompt"],
    ),
    "list_teammates": _tool(
        "list_teammates",
        "List all teammates.",
        {},
    ),
    "send_message": _tool(
        "send_message",
        "Send a message to a teammate.",
        {
            "to": {"type": "string"},
            "content": {"type": "string"},
            "msg_type": {"type": "string"},
        },
        ["to", "content"],
    ),
    "read_inbox": _tool(
        "read_inbox",
        "Read and drain the lead's inbox.",
        {},
    ),
    "broadcast": _tool(
        "broadcast",
        "Send message to all teammates.",
        {"content": {"type": "string"}},
        ["content"],
    ),
    "shutdown_request": _tool(
        "shutdown_request",
        "Request a teammate to shut down.",
        {"teammate": {"type": "string"}},
        ["teammate"],
    ),
    "plan_approval": _tool(
        "plan_approval",
        "Approve or reject a teammate's plan.",
        {
            "request_id": {"type": "string"},
            "approve": {"type": "boolean"},
            "feedback": {"type": "string"},
        },
        ["request_id", "approve"],
    ),
    "idle": _tool(
        "idle",
        "Enter idle state.",
        {},
    ),
    "claim_task": _tool(
        "claim_task",
        "Claim a task from the board.",
        {"task_id": {"type": "integer"}},
        ["task_id"],
    ),
}


TOOL_GROUPS: Dict[str, List[str]] = {
    "basic": ["bash", "read_file", "glob", "grep"],
    "write": ["write_file", "edit_file"],
    "tasking": ["TodoWrite", "task", "load_skill", "compress"],
    "background": ["background_run", "check_background"],
    "web": ["web_fetch", "web_search"],
    "persistent_tasks": ["task_create", "task_get", "task_update", "task_list"],
    "collaboration": [
        "spawn_teammate",
        "list_teammates",
        "send_message",
        "read_inbox",
        "broadcast",
        "shutdown_request",
        "plan_approval",
    ],
    "workflow": ["idle", "claim_task"],
}

SUBAGENT_TOOL_NAMES: Dict[str, List[str]] = {
    "Explore": ["bash", "read_file", "glob", "grep"],
    "general-purpose": ["bash", "read_file", "glob", "grep", "write_file", "edit_file"],
}

TEAMMATE_TOOL_NAMES: List[str] = [
    "bash",
    "read_file",
    "glob",
    "grep",
    "write_file",
    "edit_file",
    "idle",
    "claim_task",
    "send_message",
]

TOOL_RISK_LEVELS: Dict[str, str] = {
    "write_file": "high",
    "edit_file": "medium",
    "bash": "medium",
}


def get_tools_by_names(names: Iterable[str]) -> List[Dict[str, Any]]:
    """Return tool definitions for the provided ordered names."""
    return [TOOL_SPECS[name] for name in names]


def get_all_tools() -> List[Dict[str, Any]]:
    """Get all available tools."""
    ordered_names: List[str] = []
    for group in TOOL_GROUPS.values():
        ordered_names.extend(group)
    return get_tools_by_names(ordered_names)


def get_subagent_tools(agent_type: str = "Explore") -> List[Dict[str, Any]]:
    """Get tools for subagents based on type."""
    tool_names = SUBAGENT_TOOL_NAMES.get(agent_type, SUBAGENT_TOOL_NAMES["general-purpose"])
    return get_tools_by_names(tool_names)


def get_subagent_tool_names(agent_type: str = "Explore") -> List[str]:
    """Get ordered tool names for a subagent type."""
    return list(SUBAGENT_TOOL_NAMES.get(agent_type, SUBAGENT_TOOL_NAMES["general-purpose"]))


def get_teammate_tools() -> List[Dict[str, Any]]:
    """Get tools for teammate agents."""
    return get_tools_by_names(TEAMMATE_TOOL_NAMES)


TOOLS = get_all_tools()
