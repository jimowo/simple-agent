"""Permission wrapper for tool handlers.

This module provides wrapper functions to add permission checking to tool handlers,
following SOLID principles for clean separation of concerns.
"""

from typing import Any, Callable, Dict

from simple_agent.permissions.manager import PermissionManager
from simple_agent.permissions.models import PermissionResponse


class PermissionDeniedError(Exception):
    """Raised when permission is denied for a tool call."""

    def __init__(self, tool: str, reason: str = ""):
        self.tool = tool
        self.reason = reason
        super().__init__(f"Permission denied for tool '{tool}'{': ' + reason if reason else ''}")


def wrap_with_permission(
    tool_name: str,
    handler: Callable,
    permission_manager: PermissionManager,
    risk_level: str = "medium",
) -> Callable:
    """Wrap a tool handler with permission checking.

    This function follows the Single Responsibility Principle (SRP) by
    solely being responsible for adding permission checking to handlers.

    Args:
        tool_name: Name of the tool
        handler: Original handler function
        permission_manager: Permission manager instance
        risk_level: Risk level for this tool

    Returns:
        Wrapped handler function

    Example:
        wrapped_handler = wrap_with_permission(
            "write_file",
            original_write_file_handler,
            permission_manager,
            risk_level="high"
        )
    """

    def wrapped(**kwargs) -> str:
        # Check permission before executing
        response = permission_manager.check_permission(
            tool=tool_name, params=kwargs, risk_level_override=risk_level
        )

        if not response.allowed:
            raise PermissionDeniedError(
                tool_name,
                reason="Permission denied by user or policy",
            )

        # Execute original handler
        return handler(**kwargs)

    return wrapped


def create_permission_wrapper(
    permission_manager: PermissionManager,
) -> Callable[[str, str, Callable], Callable]:
    """Create a permission wrapper factory function.

    This is a convenience function for creating wrapped handlers
    with consistent configuration.

    Args:
        permission_manager: Permission manager to use

    Returns:
        Function that wraps handlers with permission checking

    Example:
        wrapper = create_permission_wrapper(permission_manager)
        wrapped_write = wrapper("write_file", "high", write_file_handler)
    """

    def wrapper(tool_name: str, risk_level: str, handler: Callable) -> Callable:
        return wrap_with_permission(tool_name, handler, permission_manager, risk_level)

    return wrapper
