"""Test tool handlers and tool registry."""

import pytest
from unittest.mock import Mock, MagicMock

from simple_agent.tools import tool_handlers
from simple_agent.tools.tool_handlers import (
    initialize_handlers,
    TOOL_HANDLERS,
    TOOLS,
    get_permission_aware_handlers,
)


@pytest.mark.security
class TestToolHandlers:
    """Test tool handlers module."""

    def test_tool_handlers_dict_exists(self):
        """Test that TOOL_HANDLERS dictionary is defined."""
        assert isinstance(TOOL_HANDLERS, dict)
        assert len(TOOL_HANDLERS) > 0

    def test_tool_handlers_has_required_tools(self):
        """Test that required tools are registered."""
        required_tools = [
            "bash",
            "read_file",
            "write_file",
            "edit_file",
            "TodoWrite",
            "task",
            "load_skill",
            "compress",
        ]

        for tool in required_tools:
            assert tool in TOOL_HANDLERS, f"Tool '{tool}' not found in TOOL_HANDLERS"

    def test_tool_handlers_are_callables(self):
        """Test that all tool handlers are callable."""
        for name, handler in TOOL_HANDLERS.items():
            assert callable(handler), f"Handler for '{name}' is not callable"

    def test_tools_list_exists(self):
        """Test that TOOLS list is defined."""
        assert isinstance(TOOLS, list)
        assert len(TOOLS) > 0

    def test_tools_have_required_fields(self):
        """Test that all tool definitions have required fields."""
        for tool in TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool

    def test_tools_input_schema_valid(self):
        """Test that tool input schemas are valid."""
        for tool in TOOLS:
            schema = tool["input_schema"]
            assert "type" in schema
            assert schema["type"] == "object"


@pytest.mark.security
class TestInitializeHandlers:
    """Test handler initialization."""

    def test_initialize_handlers_sets_globals(self, temp_workspace):
        """Test that initialize_handlers sets global managers."""
        from simple_agent.models.config import Settings
        from simple_agent.managers.todo import TodoManager
        from simple_agent.managers.task import TaskManager
        from simple_agent.managers.background import BackgroundManager
        from simple_agent.managers.message import MessageBus
        from simple_agent.managers.teammate import TeammateManager
        from simple_agent.managers.skill import SkillLoader
        from unittest.mock import Mock

        settings = Settings(
            workdir=temp_workspace,
            tasks_dir=temp_workspace / "tasks",
            inbox_dir=temp_workspace / "inbox",
            skills_dir=temp_workspace / "skills",
            team_dir=temp_workspace / "team",
            transcript_dir=temp_workspace / "transcripts",
        )

        todo = TodoManager()
        task = TaskManager(settings)
        bg = BackgroundManager(settings)
        bus = MessageBus(settings)
        skill = SkillLoader(settings=settings)
        teammate = TeammateManager(bus, task, settings)
        provider = Mock()

        initialize_handlers(
            todo, task, bg, bus, teammate, skill,
            provider, settings,
            permission_manager=None,
        )

        # Verify globals were set (by checking handlers work)
        assert tool_handlers._todo_manager is not None
        assert tool_handlers._task_manager is not None
        assert tool_handlers._background_manager is not None
        assert tool_handlers._message_bus is not None
        assert tool_handlers._teammate_manager is not None
        assert tool_handlers._skill_loader is not None
        assert tool_handlers._provider is not None
        assert tool_handlers._settings is not None


@pytest.mark.security
class TestHandleBash:
    """Test bash handler."""

    def test_handle_bash_requires_initialization(self):
        """Test that handle_bash requires initialization."""
        # Reset globals to None
        tool_handlers._settings = None

        with pytest.raises(AttributeError):
            tool_handlers.handle_bash("ls")


@pytest.mark.security
class TestHandleFileTools:
    """Test file tool handlers."""

    def test_handle_read_file(self, sample_files):
        """Test handle_read_file function."""
        result = tool_handlers.handle_read_file(str(sample_files["test.txt"]))
        assert "Hello, World!" in result

    def test_handle_write_file(self, temp_workspace):
        """Test handle_write_file function."""
        path = temp_workspace / "new.txt"
        result = tool_handlers.handle_write_file(str(path), "New content")

        assert "success" in result.lower() or "wrote" in result.lower()
        assert path.exists()

    def test_handle_edit_file(self, sample_files):
        """Test handle_edit_file function."""
        path = sample_files["test.txt"]
        result = tool_handlers.handle_edit_file(str(path), "Hello, World!", "Goodbye, World!")

        assert "success" in result.lower() or "edited" in result.lower()


@pytest.mark.security
class TestHandleTodo:
    """Test todo handler."""

    def test_handle_todo_write(self, initialized_context):
        """Test handle_todo_write function."""
        items = [
            {"content": "Task 1", "status": "pending", "activeForm": "Working on task 1"},
            {"content": "Task 2", "status": "completed", "activeForm": "Working on task 2"},
        ]

        result = tool_handlers.handle_todo_write(items)
        # Should return a string
        assert isinstance(result, str)


@pytest.mark.security
class TestGetPermissionAwareHandlers:
    """Test permission-aware handler wrapping."""

    def test_returns_original_when_no_permission_manager(self):
        """Test that original handlers are returned when no permission manager."""
        tool_handlers._permission_manager = None

        result = get_permission_aware_handlers()

        assert result is TOOL_HANDLERS or result == TOOL_HANDLERS

    def test_wraps_permission_tools(self, mock_permission_manager):
        """Test that permission-required tools are wrapped."""
        tool_handlers._permission_manager = mock_permission_manager

        result = get_permission_aware_handlers()

        # Should still have the same keys
        assert set(result.keys()) == set(TOOL_HANDLERS.keys())

    def test_wrapped_tools_check_permission(self, initialized_context):
        """Test that wrapped tools check permissions."""
        from simple_agent.tools.tool_handlers import get_permission_aware_handlers

        # Get handlers with permission manager
        handlers = get_permission_aware_handlers()

        # write_file should be wrapped
        assert "write_file" in handlers
        assert callable(handlers["write_file"])
