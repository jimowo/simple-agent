"""Tool handlers and tool definitions for the agent.

This module provides backward compatibility functions while recommending
the use of ToolHandlerRegistry for new code.

DEPRECATED: The global state pattern in this module is deprecated.
New code should use ToolHandlerRegistry from handler_registry.py instead.
"""

from typing import Callable, Dict, Optional

from simple_agent.models.config import Settings
from simple_agent.tools.handler_registry import ToolHandlerRegistry
from simple_agent.tools.tool_definitions import TOOLS

# Placeholder for managers (will be set during initialization)
# DEPRECATED: These global variables are maintained for backward compatibility only
_todo_manager = None
_task_manager = None
_background_manager = None
_message_bus = None
_teammate_manager = None
_skill_loader = None
_provider = None
_settings: Settings = None
_permission_manager = None
# ToolHandlerRegistry instance (created during initialization)
_tool_handler_registry: Optional[ToolHandlerRegistry] = None


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
    """Initialize handlers with manager instances.

    DEPRECATED: This function initializes global state for backward compatibility.
    New code should use ToolHandlerRegistry directly via dependency injection.

    This function creates a ToolHandlerRegistry instance and initializes
    the legacy global variables for backward compatibility.
    """
    global _todo_manager, _task_manager, _background_manager
    global _message_bus, _teammate_manager, _skill_loader
    global _provider, _settings, _permission_manager, _tool_handler_registry

    _todo_manager = todo_manager
    _task_manager = task_manager
    _background_manager = background_manager
    _message_bus = message_bus
    _teammate_manager = teammate_manager
    _skill_loader = skill_loader
    _provider = provider
    _settings = settings
    _permission_manager = permission_manager

    # Create ToolHandlerRegistry for use in this module
    if _tool_handler_registry is None:
        from simple_agent.agent.context import AgentContext

        # Build a minimal context for the registry
        context = AgentContext(
            settings=settings,
            todo=todo_manager,
            task_mgr=task_manager,
            bg=background_manager,
            bus=message_bus,
            skill_loader=skill_loader,
            teammate=teammate_manager,
            project_mgr=None,  # Not needed for legacy handlers
            session_mgr=None,  # Not needed for legacy handlers
            provider=provider,
        )
        _tool_handler_registry = ToolHandlerRegistry(context, permission_manager)


# Tool handler functions (delegates to ToolHandlerRegistry)
def _ensure_registry() -> ToolHandlerRegistry:
    """Ensure that the tool handler registry is initialized.

    Returns:
        ToolHandlerRegistry instance

    Raises:
        RuntimeError: If handlers have not been initialized
    """
    if _tool_handler_registry is None:
        raise RuntimeError(
            "Tool handlers not initialized. Call initialize_handlers() first."
        )
    return _tool_handler_registry


def handle_bash(command: str) -> str:
    """Handle bash command execution."""
    return _ensure_registry().handle_bash(command)


def handle_read_file(path: str, limit: int = None) -> str:
    """Handle file reading."""
    return _ensure_registry().handle_read_file(path, limit)


def handle_write_file(path: str, content: str) -> str:
    """Handle file writing."""
    return _ensure_registry().handle_write_file(path, content)


def handle_edit_file(path: str, old_text: str, new_text: str) -> str:
    """Handle file editing."""
    return _ensure_registry().handle_edit_file(path, old_text, new_text)


def handle_glob(pattern: str, path: str = None) -> str:
    """Handle glob file pattern matching."""
    return _ensure_registry().handle_glob(pattern, path)


def handle_grep(
    pattern: str,
    path: str = None,
    file_pattern: str = None,
    ignore_case: bool = False,
) -> str:
    """Handle grep content search."""
    return _ensure_registry().handle_grep(pattern, path, file_pattern, ignore_case)


def handle_todo_write(items: list) -> str:
    """Handle todo list updates."""
    return _ensure_registry().handle_todo_write(items)


def handle_task(prompt: str, agent_type: str = "Explore") -> str:
    """Handle subagent task delegation."""
    return _ensure_registry().handle_task(prompt, agent_type)


def handle_load_skill(name: str) -> str:
    """Handle skill loading."""
    return _ensure_registry().handle_load_skill(name)


def handle_compress() -> str:
    """Handle context compression."""
    return _ensure_registry().handle_compress()


def handle_background_run(command: str, timeout: int = None) -> str:
    """Handle background command execution."""
    return _ensure_registry().handle_background_run(command, timeout)


def handle_check_background(task_id: str = None) -> str:
    """Handle background task status check."""
    return _ensure_registry().handle_check_background(task_id)


def handle_web_fetch(url: str, timeout: int = 20) -> str:
    """Handle web content fetching."""
    return _ensure_registry().handle_web_fetch(url, timeout)


def handle_web_search(query: str, num_results: int = 10, timeout: int = 10) -> str:
    """Handle web search."""
    return _ensure_registry().handle_web_search(query, num_results, timeout)


def handle_task_create(subject: str, description: str = "") -> str:
    """Handle task creation."""
    return _ensure_registry().handle_task_create(subject, description)


def handle_task_get(task_id: int) -> str:
    """Handle task retrieval."""
    return _ensure_registry().handle_task_get(task_id)


def handle_task_update(
    task_id: int, status: str = None, add_blocked_by: list = None, add_blocks: list = None
) -> str:
    """Handle task updates."""
    return _ensure_registry().handle_task_update(task_id, status, add_blocked_by, add_blocks)


def handle_task_list() -> str:
    """Handle task listing."""
    return _ensure_registry().handle_task_list()


def handle_spawn_teammate(name: str, role: str, prompt: str) -> str:
    """Handle teammate spawning."""
    return _ensure_registry().handle_spawn_teammate(name, role, prompt)


def handle_list_teammates() -> str:
    """Handle teammate listing."""
    return _ensure_registry().handle_list_teammates()


def handle_send_message(to: str, content: str, msg_type: str = "message") -> str:
    """Handle message sending."""
    return _ensure_registry().handle_send_message(to, content, msg_type)


def handle_read_inbox() -> str:
    """Handle inbox reading."""
    return _ensure_registry().handle_read_inbox()


def handle_broadcast(content: str) -> str:
    """Handle message broadcasting."""
    return _ensure_registry().handle_broadcast(content)


def handle_shutdown_request(teammate: str) -> str:
    """Handle shutdown requests."""
    return _ensure_registry().handle_shutdown_request(teammate)


def handle_plan_approval(request_id: str, approve: bool, feedback: str = "") -> str:
    """Handle plan approval/rejection."""
    return _ensure_registry().handle_plan_approval(request_id, approve, feedback)


def handle_idle() -> str:
    """Handle idle state."""
    return _ensure_registry().handle_idle()


def handle_claim_task(task_id: int) -> str:
    """Handle task claiming."""
    return _ensure_registry().handle_claim_task(task_id)


# Tool handlers dictionary
TOOL_HANDLERS: Dict[str, Callable] = {
    "bash": handle_bash,
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "edit_file": handle_edit_file,
    "glob": handle_glob,
    "grep": handle_grep,
    "TodoWrite": handle_todo_write,
    "task": handle_task,
    "load_skill": handle_load_skill,
    "compress": handle_compress,
    "background_run": handle_background_run,
    "check_background": handle_check_background,
    "web_fetch": handle_web_fetch,
    "web_search": handle_web_search,
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

    DEPRECATED: This function is maintained for backward compatibility.
    New code should use ToolHandlerRegistry.get_permission_aware_handlers() instead.

    Args:
        handlers: Optional base handlers dict (defaults to TOOL_HANDLERS)

    Returns:
        Dictionary of tool names to wrapped handler functions
    """
    if handlers is None:
        handlers = TOOL_HANDLERS.copy()

    # Delegate to ToolHandlerRegistry
    registry = _ensure_registry()
    return registry.get_permission_aware_handlers()


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
