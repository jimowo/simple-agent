"""Centralized tool definitions for the agent.

This module provides a single source of truth for all tool definitions,
eliminating duplication across the codebase.
"""

from typing import Any, Dict, List

# Basic tools (available to all agent types)
BASIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "bash",
        "description": "Run a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read file contents.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["path"],
        },
    },
    {
        "name": "glob",
        "description": "Find files by pattern matching using glob syntax (e.g., '**/*.py', 'src/**/*.txt').",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "grep",
        "description": "Search for patterns in file contents using regex.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "file_pattern": {"type": "string"},
                "ignore_case": {"type": "boolean"},
            },
            "required": ["pattern"],
        },
    },
]


# Write/edit tools (restricted access)
WRITE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "write_file",
        "description": "Write content to file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace exact text in file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
]


# Task management tools
TASK_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "TodoWrite",
        "description": "Update task tracking list.",
        "input_schema": {
            "type": "object",
            "properties": {
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
            "required": ["items"],
        },
    },
    {
        "name": "task",
        "description": "Spawn a subagent for isolated exploration or work.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "agent_type": {"type": "string", "enum": ["Explore", "general-purpose"]},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "load_skill",
        "description": "Load specialized knowledge by name.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "compress",
        "description": "Manually compress conversation context.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# Background task tools
BACKGROUND_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "background_run",
        "description": "Run command in background thread.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}},
            "required": ["command"],
        },
    },
    {
        "name": "check_background",
        "description": "Check background task status.",
        "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}},
    },
]


# Web tools (network access)
WEB_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "web_fetch",
        "description": "Fetch content from a URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "timeout": {"type": "integer"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web for information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "num_results": {"type": "integer"},
                "timeout": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
]


# Persistent task management tools
PERSISTENT_TASK_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "background_run",
        "description": "Run command in background thread.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}},
            "required": ["command"],
        },
    },
    {
        "name": "check_background",
        "description": "Check background task status.",
        "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}},
    },
]


# Persistent task management tools
PERSISTENT_TASK_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "task_create",
        "description": "Create a persistent file task.",
        "input_schema": {
            "type": "object",
            "properties": {"subject": {"type": "string"}, "description": {"type": "string"}},
            "required": ["subject"],
        },
    },
    {
        "name": "task_get",
        "description": "Get task details by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "task_update",
        "description": "Update task status or dependencies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "deleted"],
                },
                "add_blocked_by": {"type": "array", "items": {"type": "integer"}},
                "add_blocks": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "task_list",
        "description": "List all tasks.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# Collaboration tools
COLLABORATION_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "spawn_teammate",
        "description": "Spawn a persistent autonomous teammate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "role": {"type": "string"},
                "prompt": {"type": "string"},
            },
            "required": ["name", "role", "prompt"],
        },
    },
    {
        "name": "list_teammates",
        "description": "List all teammates.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "send_message",
        "description": "Send a message to a teammate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "content": {"type": "string"},
                "msg_type": {"type": "string"},
            },
            "required": ["to", "content"],
        },
    },
    {
        "name": "read_inbox",
        "description": "Read and drain the lead's inbox.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "broadcast",
        "description": "Send message to all teammates.",
        "input_schema": {
            "type": "object",
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        },
    },
    {
        "name": "shutdown_request",
        "description": "Request a teammate to shut down.",
        "input_schema": {
            "type": "object",
            "properties": {"teammate": {"type": "string"}},
            "required": ["teammate"],
        },
    },
    {
        "name": "plan_approval",
        "description": "Approve or reject a teammate's plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string"},
                "approve": {"type": "boolean"},
                "feedback": {"type": "string"},
            },
            "required": ["request_id", "approve"],
        },
    },
]


# Workflow tools
WORKFLOW_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "idle",
        "description": "Enter idle state.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "claim_task",
        "description": "Claim a task from the board.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
]


# Tool collections for different use cases
def get_all_tools() -> List[Dict[str, Any]]:
    """Get all available tools."""
    return (
        BASIC_TOOLS
        + WRITE_TOOLS
        + TASK_TOOLS
        + BACKGROUND_TOOLS
        + WEB_TOOLS
        + PERSISTENT_TASK_TOOLS
        + COLLABORATION_TOOLS
        + WORKFLOW_TOOLS
    )


def get_subagent_tools(agent_type: str = "Explore") -> List[Dict[str, Any]]:
    """Get tools for subagent based on type.

    Args:
        agent_type: Type of agent ("Explore" or other)

    Returns:
        List of tool definitions
    """
    if agent_type == "Explore":
        return BASIC_TOOLS.copy()
    return BASIC_TOOLS + WRITE_TOOLS


def get_teammate_tools() -> List[Dict[str, Any]]:
    """Get tools for teammate agents."""
    return (
        BASIC_TOOLS
        + WRITE_TOOLS
        + [WORKFLOW_TOOLS[0]]  # idle
        + [WORKFLOW_TOOLS[1]]  # claim_task
        + [
            {
                "name": "send_message",
                "description": "Send message.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["to", "content"],
                },
            }
        ]
    )


# Export the full tool list for backward compatibility
TOOLS = get_all_tools()
