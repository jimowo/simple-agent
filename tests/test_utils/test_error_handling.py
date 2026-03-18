"""Tests for tool error formatting utilities."""

from simple_agent.exceptions import PathTraversalError
from simple_agent.utils.error_handling import format_tool_error


class TestErrorHandling:
    """Test standardized tool error formatting."""

    def test_format_tool_error_preserves_project_exception_message(self):
        """Project exceptions should keep their original message text."""
        err = PathTraversalError("../secret", "/workspace")

        result = format_tool_error("read_file", err)

        assert result.startswith("Error: ")
        assert "Path escapes workspace" in result
