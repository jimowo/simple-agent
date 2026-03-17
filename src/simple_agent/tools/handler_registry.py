"""Context-based tool handler registry.

This module provides a dependency injection-based approach to tool handlers,
eliminating the need for global state.
"""

import functools
from typing import TYPE_CHECKING, Callable, Dict, Optional

from loguru import logger

from simple_agent.tools.bash_tools import run_bash
from simple_agent.tools.file_tools import edit_file, read_file, write_file
from simple_agent.tools.search_tools import glob_files, grep_content
from simple_agent.tools.web_tools import web_fetch, web_search

if TYPE_CHECKING:
    from simple_agent.agent.context import AgentContext
    from simple_agent.permissions.manager import PermissionManager


class ToolHandlerRegistry:
    """Registry for tool handlers that uses dependency injection.

    This class follows the Single Responsibility Principle (SRP) by
    solely being responsible for managing tool handlers and their
    dependencies through the AgentContext.

    Attributes:
        context: AgentContext containing all dependencies
        permission_manager: Optional permission manager for access control
    """

    def __init__(
        self,
        context: "AgentContext",
        permission_manager: Optional["PermissionManager"] = None,
    ):
        """Initialize the handler registry.

        Args:
            context: AgentContext with all manager dependencies
            permission_manager: Optional permission manager for access control
        """
        self._context = context
        self._permission_manager = permission_manager

    def handle_bash(self, command: str) -> str:
        """Handle bash command execution."""
        return run_bash(command, self._context.settings.workdir, self._context.settings.bash_timeout)

    def handle_read_file(self, path: str, limit: int = None) -> str:
        """Handle file reading."""
        return read_file(path, limit)

    def handle_write_file(self, path: str, content: str) -> str:
        """Handle file writing."""
        return write_file(path, content)

    def handle_edit_file(self, path: str, old_text: str, new_text: str) -> str:
        """Handle file editing."""
        return edit_file(path, old_text, new_text)

    def handle_todo_write(self, items: list) -> str:
        """Handle todo list updates."""
        return self._context.todo.update(items)

    def handle_task(self, prompt: str, agent_type: str = "Explore") -> str:
        """Handle subagent task delegation."""
        from simple_agent.agent.subagent import SubAgentRunner

        runner = SubAgentRunner(self._context.provider, tool_registry=self)
        return runner.run(prompt, agent_type)

    def handle_load_skill(self, name: str) -> str:
        """Handle skill loading."""
        return self._context.skill_loader.load(name)

    def handle_compress(self) -> str:
        """Handle context compression."""
        return "Compressing..."

    def handle_background_run(self, command: str, timeout: int = None) -> str:
        """Handle background command execution."""
        if timeout is None:
            timeout = self._context.settings.bash_timeout
        return self._context.bg.run(command, timeout)

    def handle_check_background(self, task_id: str = None) -> str:
        """Handle background task status check."""
        return self._context.bg.check(task_id)

    def handle_task_create(self, subject: str, description: str = "") -> str:
        """Handle task creation."""
        return self._context.task_mgr.create(subject, description)

    def handle_task_get(self, task_id: int) -> str:
        """Handle task retrieval."""
        return self._context.task_mgr.get(task_id)

    def handle_task_update(
        self,
        task_id: int,
        status: str = None,
        add_blocked_by: list = None,
        add_blocks: list = None,
    ) -> str:
        """Handle task updates."""
        return self._context.task_mgr.update(task_id, status, add_blocked_by, add_blocks)

    def handle_task_list(self) -> str:
        """Handle task listing."""
        return self._context.task_mgr.list_all()

    def handle_spawn_teammate(self, name: str, role: str, prompt: str) -> str:
        """Handle teammate spawning."""
        return self._context.teammate.spawn(name, role, prompt)

    def handle_list_teammates(self) -> str:
        """Handle teammate listing."""
        return self._context.teammate.list_all()

    def handle_send_message(self, to: str, content: str, msg_type: str = "message") -> str:
        """Handle message sending."""
        return self._context.bus.send("lead", to, content, msg_type)

    def handle_read_inbox(self) -> str:
        """Handle inbox reading."""
        import json

        return json.dumps(self._context.bus.read_inbox("lead"), indent=2)

    def handle_broadcast(self, content: str) -> str:
        """Handle message broadcasting."""
        return self._context.bus.broadcast("lead", content, self._context.teammate.member_names())

    def handle_shutdown_request(self, teammate: str) -> str:
        """Handle shutdown requests."""
        from simple_agent.agent.base import handle_shutdown_request as _handle_shutdown_request

        return _handle_shutdown_request(self._context.bus, teammate)

    def handle_plan_approval(self, request_id: str, approve: bool, feedback: str = "") -> str:
        """Handle plan approval/rejection."""
        from simple_agent.agent.base import handle_plan_review as _handle_plan_review

        return _handle_plan_review(self._context.bus, request_id, approve, feedback)

    def handle_idle(self) -> str:
        """Handle idle state."""
        return "Lead does not idle."

    def handle_claim_task(self, task_id: int) -> str:
        """Handle task claiming."""
        return self._context.task_mgr.claim(task_id, "lead")

    # Search tools
    def handle_glob(self, pattern: str, path: str = None) -> str:
        """Handle glob file pattern matching."""
        return glob_files(pattern, path)

    def handle_grep(
        self,
        pattern: str,
        path: str = None,
        file_pattern: str = None,
        ignore_case: bool = False,
    ) -> str:
        """Handle grep content search."""
        return grep_content(pattern, path, file_pattern, ignore_case)

    # Web tools
    def handle_web_fetch(self, url: str, timeout: int = 20) -> str:
        """Handle web content fetching."""
        return web_fetch(url, timeout)

    def handle_web_search(
        self,
        query: str,
        num_results: int = 10,
        timeout: int = 10,
    ) -> str:
        """Handle web search."""
        return web_search(query, num_results, timeout, self._context.settings)

    def get_handlers(self, tool_names: list = None) -> Dict[str, Callable]:
        """Get tool handlers as a dictionary.

        Args:
            tool_names: Optional list of tool names to include (returns all if None)

        Returns:
            Dictionary mapping tool names to handler functions
        """
        all_handlers = {
            "bash": self.handle_bash,
            "read_file": self.handle_read_file,
            "write_file": self.handle_write_file,
            "edit_file": self.handle_edit_file,
            "glob": self.handle_glob,
            "grep": self.handle_grep,
            "TodoWrite": self.handle_todo_write,
            "task": self.handle_task,
            "load_skill": self.handle_load_skill,
            "compress": self.handle_compress,
            "background_run": self.handle_background_run,
            "check_background": self.handle_check_background,
            "web_fetch": self.handle_web_fetch,
            "web_search": self.handle_web_search,
            "task_create": self.handle_task_create,
            "task_get": self.handle_task_get,
            "task_update": self.handle_task_update,
            "task_list": self.handle_task_list,
            "spawn_teammate": self.handle_spawn_teammate,
            "list_teammates": self.handle_list_teammates,
            "send_message": self.handle_send_message,
            "read_inbox": self.handle_read_inbox,
            "broadcast": self.handle_broadcast,
            "shutdown_request": self.handle_shutdown_request,
            "plan_approval": self.handle_plan_approval,
            "idle": self.handle_idle,
            "claim_task": self.handle_claim_task,
        }

        if tool_names is None:
            return all_handlers

        # Filter to only requested tools
        return {name: all_handlers[name] for name in tool_names if name in all_handlers}

    def get_permission_aware_handlers(self, tool_names: list = None) -> Dict[str, Callable]:
        """Get tool handlers with permission checking.

        This method wraps handlers that require permission with permission checks.
        It follows the Single Responsibility Principle (SRP) by only handling
        the wrapping logic, delegating permission logic to PermissionManager.

        Args:
            tool_names: Optional list of tool names to include (returns all if None)

        Returns:
            Dictionary of tool names to wrapped handler functions
        """
        handlers = self.get_handlers(tool_names)
        logger.debug(f"[HANDLER_REGISTRY] Getting permission-aware handlers, total handlers: {len(handlers)}")

        # If no permission manager, return original handlers
        if self._permission_manager is None:
            logger.debug("[HANDLER_REGISTRY] No permission manager configured, returning original handlers")
            return handlers

        # Get permission tools from PermissionManager (centralized configuration)
        permission_tools = self._permission_manager.get_permission_required_tools()

        logger.debug(f"[HANDLER_REGISTRY] Permission manager configured, tools requiring permission: {list(permission_tools.keys())}")

        # Wrap handlers that require permission
        result = handlers.copy()
        for tool, risk_level in permission_tools.items():
            if tool in result:
                original_handler = result[tool]
                logger.debug(f"[HANDLER_REGISTRY] Wrapping tool '{tool}' with permission check (risk_level={risk_level})")

                # Use functools.partial to properly bind closure variables
                # This avoids the common closure variable capture issue
                wrapped_handler = functools.partial(
                    self._create_permission_wrapped,
                    tool_name=tool,
                    handler=original_handler,
                    risk_level=risk_level,
                )
                result[tool] = wrapped_handler
            else:
                logger.debug(f"[HANDLER_REGISTRY] Tool '{tool}' not in available handlers, skipping wrap")

        logger.debug(f"[HANDLER_REGISTRY] Permission-aware handlers ready, wrapped tools: {[t for t in permission_tools if t in result]}")
        return result

    def _create_permission_wrapped(
        self,
        tool_name: str,
        handler: Callable,
        risk_level: str,
        **kwargs
    ) -> str:
        """Create a permission-wrapped handler call.

        This method is used with functools.partial to properly bind closure variables
        and avoid the common closure variable capture issue in loops.

        Args:
            tool_name: Name of the tool being wrapped
            handler: Original handler function
            risk_level: Risk level for this tool
            **kwargs: Arguments to pass to the handler

        Returns:
            Handler result or error message

        Raises:
            PermissionDeniedError: If permission is denied for the tool execution
        """
        from simple_agent.permissions.wrapper import wrap_with_permission

        # Wrap and execute the handler with permission checking
        wrapped = wrap_with_permission(
            tool_name, handler, self._permission_manager, risk_level
        )
        return wrapped(**kwargs)
