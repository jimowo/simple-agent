"""Tool handlers and tool definitions for the agent.

This module provides backward compatibility functions while recommending
the use of ToolHandlerRegistry for new code.

DEPRECATED: The global state pattern in this module is deprecated.
New code should use ToolHandlerRegistry from handler_registry.py instead.
"""

from typing import Callable, Dict

from simple_agent.models.config import Settings
from simple_agent.tools.base import ToolRegistry
from simple_agent.tools.bash_tools import run_bash
from simple_agent.tools.file_tools import edit_file, read_file, write_file
from simple_agent.tools.handler_registry import ToolHandlerRegistry
from simple_agent.tools.tool_definitions import TOOLS

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


# Re-export for backward compatibility
# Note: ToolHandlerRegistry is the recommended approach for new code
__all__ = [
    "TOOLS",
    "TOOL_HANDLERS",
    "get_permission_aware_handlers",
    "initialize_handlers",
    # New dependency-injection based approach
    "ToolHandlerRegistry",
]
