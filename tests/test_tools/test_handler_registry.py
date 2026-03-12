"""Test ToolHandlerRegistry class."""

from unittest.mock import Mock

import pytest

from simple_agent.agent.context import AgentContext
from simple_agent.tools.handler_registry import ToolHandlerRegistry
from simple_agent.tools.tool_definitions import TOOLS


@pytest.mark.security
class TestToolHandlerRegistry:
    """Test ToolHandlerRegistry class."""

    def test_init_with_context(self, initialized_context):
        """Test initialization with AgentContext."""
        registry = ToolHandlerRegistry(initialized_context)

        assert registry._context is initialized_context
        assert registry._permission_manager is None

    def test_init_with_permission_manager(
        self, initialized_context, mock_permission_manager
    ):
        """Test initialization with permission manager."""
        registry = ToolHandlerRegistry(
            initialized_context, mock_permission_manager
        )

        assert registry._context is initialized_context
        assert registry._permission_manager is mock_permission_manager

    def test_get_handlers_returns_all(self, initialized_context):
        """Test that get_handlers returns all tool handlers."""
        registry = ToolHandlerRegistry(initialized_context)
        handlers = registry.get_handlers()

        # Should return all handlers
        expected_tools = [
            "bash",
            "read_file",
            "write_file",
            "edit_file",
            "TodoWrite",
            "task",
            "load_skill",
            "compress",
        ]
        for tool in expected_tools:
            assert tool in handlers
            assert callable(handlers[tool])

    def test_get_handlers_filters_by_names(self, initialized_context):
        """Test that get_handlers filters tools by name."""
        registry = ToolHandlerRegistry(initialized_context)
        handlers = registry.get_handlers(["bash", "read_file"])

        assert len(handlers) == 2
        assert "bash" in handlers
        assert "read_file" in handlers
        assert "write_file" not in handlers

    def test_handle_bash(self, initialized_context, temp_workspace):
        """Test bash handler."""
        registry = ToolHandlerRegistry(initialized_context)
        result = registry.handle_bash("echo hello")

        assert "hello" in result

    def test_handle_read_file(self, initialized_context, sample_files):
        """Test read_file handler."""
        registry = ToolHandlerRegistry(initialized_context)
        result = registry.handle_read_file(str(sample_files["test.txt"]))

        assert "Hello, World!" in result

    def test_handle_write_file(self, initialized_context, temp_workspace):
        """Test write_file handler."""
        registry = ToolHandlerRegistry(initialized_context)
        test_file = temp_workspace / "test_write.txt"
        result = registry.handle_write_file(str(test_file), "test content")

        assert "success" in result.lower() or "wrote" in result.lower()
        assert test_file.exists()
        assert test_file.read_text() == "test content"

    def test_handle_edit_file(self, initialized_context, sample_files):
        """Test edit_file handler."""
        registry = ToolHandlerRegistry(initialized_context)
        result = registry.handle_edit_file(
            str(sample_files["test.txt"]), "Hello, World!", "Goodbye, World!"
        )

        assert "success" in result.lower() or "edited" in result.lower()
        assert "Goodbye, World!" in sample_files["test.txt"].read_text()

    def test_handle_todo_write(self, initialized_context):
        """Test todo_write handler."""
        registry = ToolHandlerRegistry(initialized_context)
        items = [
            {
                "content": "Task 1",
                "status": "pending",
                "activeForm": "Working on task 1",
            }
        ]
        result = registry.handle_todo_write(items)

        assert isinstance(result, str)

    def test_handle_compress(self, initialized_context):
        """Test compress handler."""
        registry = ToolHandlerRegistry(initialized_context)
        result = registry.handle_compress()

        assert result == "Compressing..."

    def test_handle_task_create(self, initialized_context):
        """Test task_create handler."""
        registry = ToolHandlerRegistry(initialized_context)
        result = registry.handle_task_create("Test task", "Test description")

        assert isinstance(result, str)

    def test_handle_task_get(self, initialized_context):
        """Test task_get handler."""
        registry = ToolHandlerRegistry(initialized_context)
        # First create a task
        create_result = registry.handle_task_create("Test task")
        # The result should contain the task ID
        # Extract task ID from result (format: "Task {id} created...")
        import re

        match = re.search(r"Task (\d+)", create_result)
        if match:
            task_id = int(match.group(1))
            result = registry.handle_task_get(task_id)
            assert isinstance(result, str)

    def test_get_permission_aware_handlers_without_permission_manager(
        self, initialized_context
    ):
        """Test get_permission_aware_handlers without permission manager."""
        registry = ToolHandlerRegistry(initialized_context)
        handlers = registry.get_permission_aware_handlers()

        # Should return the same handlers as get_handlers
        base_handlers = registry.get_handlers()
        assert set(handlers.keys()) == set(base_handlers.keys())

    def test_get_permission_aware_handlers_with_permission_manager(
        self, initialized_context, mock_permission_manager
    ):
        """Test get_permission_aware_handlers with permission manager."""
        registry = ToolHandlerRegistry(
            initialized_context, mock_permission_manager
        )
        handlers = registry.get_permission_aware_handlers()

        # Should return handlers
        assert "bash" in handlers
        assert "write_file" in handlers
        assert "edit_file" in handlers
        assert callable(handlers["bash"])

    def test_get_permission_aware_handlers_filters_tools(
        self, initialized_context, mock_permission_manager
    ):
        """Test that get_permission_aware_handlers filters tools."""
        registry = ToolHandlerRegistry(
            initialized_context, mock_permission_manager
        )
        handlers = registry.get_permission_aware_handlers(["bash", "read_file"])

        assert len(handlers) == 2
        assert "bash" in handlers
        assert "read_file" in handlers
        assert "write_file" not in handlers


@pytest.mark.security
class TestToolHandlerRegistryIntegration:
    """Integration tests for ToolHandlerRegistry."""

    def test_full_workflow(self, initialized_context, temp_workspace):
        """Test a complete workflow of tool operations."""
        registry = ToolHandlerRegistry(initialized_context)

        # Write a file
        test_file = temp_workspace / "workflow_test.txt"
        write_result = registry.handle_write_file(str(test_file), "Initial content")
        assert "wrote" in write_result.lower()

        # Read the file
        read_result = registry.handle_read_file(str(test_file))
        assert "Initial content" in read_result

        # Edit the file
        edit_result = registry.handle_edit_file(
            str(test_file), "Initial content", "Updated content"
        )
        assert "edited" in edit_result.lower()

        # Read again to verify
        read_result2 = registry.handle_read_file(str(test_file))
        assert "Updated content" in read_result2

        # Run bash command
        bash_result = registry.handle_bash(f"cat {test_file}")
        assert "Updated content" in bash_result
