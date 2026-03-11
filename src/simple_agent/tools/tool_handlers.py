"""Tool handlers and tool definitions for the agent."""

from typing import Callable, Dict

from simple_agent.models.config import Settings
from simple_agent.tools.base import ToolRegistry
from simple_agent.tools.bash_tools import run_bash
from simple_agent.tools.file_tools import edit_file, read_file, write_file

# Initialize global registry
_tool_registry = ToolRegistry()

# Placeholder for managers (will be set during initialization)
_todo_manager = None
_task_manager = None
_background_manager = None
_message_bus = None
_teammate_manager = None
_skill_loader = None
_provider = None
_settings: Settings = None
_permission_manager = None


def initialize_handlers(
    todo_manager,
    task_manager,
    background_manager,
    message_bus,
    teammate_manager,
    skill_loader,
    provider,
    settings,
    permission_manager=None,
):
    """Initialize handlers with manager instances."""
    global _todo_manager, _task_manager, _background_manager
    global _message_bus, _teammate_manager, _skill_loader
    global _provider, _settings, _permission_manager

    _todo_manager = todo_manager
    _task_manager = task_manager
    _background_manager = background_manager
    _message_bus = message_bus
    _teammate_manager = teammate_manager
    _skill_loader = skill_loader
    _provider = provider
    _settings = settings
    _permission_manager = permission_manager


# Tool handler functions
def handle_bash(command: str) -> str:
    return run_bash(command, _settings.workdir, _settings.bash_timeout)


def handle_read_file(path: str, limit: int = None) -> str:
    return read_file(path, limit)


def handle_write_file(path: str, content: str) -> str:
    return write_file(path, content)


def handle_edit_file(path: str, old_text: str, new_text: str) -> str:
    return edit_file(path, old_text, new_text)


def handle_todo_write(items: list) -> str:
    return _todo_manager.update(items)


def handle_task(prompt: str, agent_type: str = "Explore") -> str:
    from simple_agent.agent.base import run_subagent

    return run_subagent(_provider, prompt, agent_type)


def handle_load_skill(name: str) -> str:
    return _skill_loader.load(name)


def handle_compress() -> str:
    return "Compressing..."


def handle_background_run(command: str, timeout: int = None) -> str:
    if timeout is None:
        timeout = _settings.bash_timeout
    return _background_manager.run(command, timeout)


def handle_check_background(task_id: str = None) -> str:
    return _background_manager.check(task_id)


def handle_task_create(subject: str, description: str = "") -> str:
    return _task_manager.create(subject, description)


def handle_task_get(task_id: int) -> str:
    return _task_manager.get(task_id)


def handle_task_update(
    task_id: int, status: str = None, add_blocked_by: list = None, add_blocks: list = None
) -> str:
    return _task_manager.update(task_id, status, add_blocked_by, add_blocks)


def handle_task_list() -> str:
    return _task_manager.list_all()


def handle_spawn_teammate(name: str, role: str, prompt: str) -> str:
    return _teammate_manager.spawn(name, role, prompt)


def handle_list_teammates() -> str:
    return _teammate_manager.list_all()


def handle_send_message(to: str, content: str, msg_type: str = "message") -> str:
    return _message_bus.send("lead", to, content, msg_type)


def handle_read_inbox() -> str:
    import json

    return json.dumps(_message_bus.read_inbox("lead"), indent=2)


def handle_broadcast(content: str) -> str:
    return _message_bus.broadcast("lead", content, _teammate_manager.member_names())


def handle_shutdown_request(teammate: str) -> str:
    from simple_agent.agent.base import handle_shutdown_request

    return handle_shutdown_request(_message_bus, teammate)


def handle_plan_approval(request_id: str, approve: bool, feedback: str = "") -> str:
    from simple_agent.agent.base import handle_plan_review

    return handle_plan_review(_message_bus, request_id, approve, feedback)


def handle_idle() -> str:
    return "Lead does not idle."


def handle_claim_task(task_id: int) -> str:
    return _task_manager.claim(task_id, "lead")


# Tool handlers dictionary
TOOL_HANDLERS: Dict[str, Callable] = {
    "bash": handle_bash,
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "edit_file": handle_edit_file,
    "TodoWrite": handle_todo_write,
    "task": handle_task,
    "load_skill": handle_load_skill,
    "compress": handle_compress,
    "background_run": handle_background_run,
    "check_background": handle_check_background,
    "task_create": handle_task_create,
    "task_get": handle_task_get,
    "task_update": handle_task_update,
    "task_list": handle_task_list,
    "spawn_teammate": handle_spawn_teammate,
    "list_teammates": handle_list_teammates,
    "send_message": handle_send_message,
    "read_inbox": handle_read_inbox,
    "broadcast": handle_broadcast,
    "shutdown_request": handle_shutdown_request,
    "plan_approval": handle_plan_approval,
    "idle": handle_idle,
    "claim_task": handle_claim_task,
}


# Tool definitions for Anthropic API
TOOLS = [
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


# Permission-aware tool handlers
def get_permission_aware_handlers(handlers: Dict[str, Callable] = None) -> Dict[str, Callable]:
    """Get tool handlers with permission checking.

    This function wraps handlers that require permission with permission checks.
    It follows the Single Responsibility Principle (SRP) by only handling
    the wrapping logic, delegating permission logic to PermissionManager.

    Args:
        handlers: Optional base handlers dict (defaults to TOOL_HANDLERS)

    Returns:
        Dictionary of tool names to wrapped handler functions
    """
    if handlers is None:
        handlers = TOOL_HANDLERS.copy()

    # If no permission manager, return original handlers
    if _permission_manager is None:
        return handlers

    # Import permission wrapper
    from simple_agent.permissions.wrapper import PermissionDeniedError, wrap_with_permission

    # Tools that require permission checking
    permission_tools = {
        "write_file": "high",
        "bash": "medium",
        "edit_file": "medium",
    }

    # Wrap handlers that require permission
    result = handlers.copy()
    for tool, risk_level in permission_tools.items():
        if tool in result:
            original_handler = result[tool]

            def create_wrapped(handler, tool_name=tool, risk=risk_level):
                def wrapped(**kwargs):
                    try:
                        return wrap_with_permission(
                            tool_name, handler, _permission_manager, risk
                        )(**kwargs)
                    except PermissionDeniedError as e:
                        return f"Permission denied: {e.reason}"

                return wrapped

            result[tool] = create_wrapped(original_handler)

    return result
