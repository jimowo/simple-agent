"""Error handling utilities for tool functions.

This module provides decorators and utilities for consistent error handling
in tool functions.
"""

from functools import wraps
from typing import Any, Callable

from simple_agent.exceptions import SimpleAgentError, ToolExecutionError


def format_tool_error(func_name: str, error: Exception) -> str:
    """Format tool exceptions consistently for tool-facing APIs."""
    if isinstance(error, SimpleAgentError):
        return f"Error: {error}"
    return f"Error: {ToolExecutionError(func_name, str(error))}"


def handle_tool_errors(func: Callable) -> Callable:
    """Decorator to handle exceptions in tool functions consistently.

    This decorator catches exceptions and returns them as error messages,
    which is useful for tool functions that are called by AI agents.

    Args:
        func: The function to wrap

    Returns:
        Wrapped function that returns error messages on exceptions

    Example:
        @handle_tool_errors
        def my_tool(path: str) -> str:
            return some_operation(path)
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return format_tool_error(func.__name__, e)

    return wrapper


def handle_unicode_fallback(func: Callable) -> Callable:
    """Decorator to handle Unicode decode errors with fallback.

    This decorator first tries the function (assumed to use UTF-8 encoding),
    and falls back to system encoding if UnicodeDecodeError occurs.

    Args:
        func: The function to wrap (should accept path as first argument)

    Returns:
        Wrapped function with Unicode fallback

    Example:
        @handle_unicode_fallback
        def read_with_utf8(path: str) -> str:
            return safe_path(path).read_text(encoding='utf-8')
    """

    @wraps(func)
    def wrapper(path: str, *args: Any, **kwargs: Any) -> str:
        try:
            return func(path, *args, **kwargs)
        except UnicodeDecodeError:
            # Retry with system encoding
            try:
                # Call the function with encoding='utf-8' replaced by default
                # This assumes the function uses read_text(encoding='utf-8')
                # result = str(func.__wrapped__(path, *args, **kwargs) if hasattr(func, '__wrapped__') else '')
                # For now, re-read with system encoding

                from simple_agent.utils.safety import safe_path

                return safe_path(path).read_text()
            except Exception as e:
                return format_tool_error(func.__name__, e)
        except Exception as e:
            return format_tool_error(func.__name__, e)

    return wrapper
