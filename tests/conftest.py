"""Pytest configuration and shared fixtures for simple-agent tests."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simple_agent.core.container import reset_container
from simple_agent.models.config import Settings


@pytest.fixture(autouse=True)
def reset_global_state():
    """
    Reset global state before and after each test.

    This is crucial because the codebase uses global singletons.
    Without this, tests can interfere with each other.
    """
    # Reset service container
    reset_container()

    # Reset logger state (loguru has global handlers)
    from loguru import logger as global_logger
    global_logger.remove()

    # Reset teammate manager globals
    from simple_agent.managers import teammate
    if hasattr(teammate, 'shutdown_requests'):
        teammate.shutdown_requests.clear()
    if hasattr(teammate, 'plan_requests'):
        teammate.plan_requests.clear()

    yield

    # Cleanup after test
    reset_container()

    # Reset logger state after test
    from loguru import logger as global_logger
    global_logger.remove()


@pytest.fixture(autouse=True)
def use_temp_workspace(temp_workspace):
    """
    Temporarily change the global Settings workdir to temp_workspace.

    This is needed because file_tools and bash_tools use Settings().workdir.
    This fixture is autouse so all tests automatically use temp workspace.
    """
    def get_temp_settings():
        return Settings(
            workdir=temp_workspace,
            tasks_dir=temp_workspace / "tasks",
            inbox_dir=temp_workspace / "inbox",
            skills_dir=temp_workspace / "skills",
            team_dir=temp_workspace / "team",
            transcript_dir=temp_workspace / "transcripts",
            logs_dir=temp_workspace / "logs",
        )

    # Patch Settings() to return temp workspace settings
    with patch('simple_agent.utils.safety.Settings', side_effect=get_temp_settings):
        yield


@pytest.fixture
def temp_workspace(tmp_path):
    """
    Create a temporary workspace directory for testing.

    This fixture provides a clean temporary directory for each test,
    automatically cleaned up by pytest.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Returns:
        Path to temporary workspace directory
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def mock_settings(temp_workspace):
    """
    Create mock Settings with temporary workspace directories.

    This prevents tests from affecting the actual project directories.

    Args:
        temp_workspace: Temporary workspace fixture

    Returns:
        Settings instance configured for testing
    """
    settings = Settings(
        workdir=temp_workspace,
        tasks_dir=temp_workspace / "tasks",
        inbox_dir=temp_workspace / "inbox",
        skills_dir=temp_workspace / "skills",
        team_dir=temp_workspace / "team",
        transcript_dir=temp_workspace / "transcripts",
    )
    return settings


@pytest.fixture
def mock_provider():
    """
    Create a mock AI provider for testing.

    This avoids making actual API calls during tests.

    Returns:
        Mock provider with predefined responses
    """
    from simple_agent.providers.base import BaseProvider, ProviderResponse, ToolCall

    provider = Mock(spec=BaseProvider)
    provider.model = "test-model"
    provider.api_key = "test-key"

    # Default response
    provider.create_message.return_value = ProviderResponse(
        content=[{"type": "text", "text": "Test response"}],
        tool_calls=[],
        stop_reason="stop",
        usage={"input_tokens": 10, "output_tokens": 20},
    )

    return provider


@pytest.fixture
def mock_permission_manager():
    """
    Create a mock permission manager that auto-approves.

    For testing, we often want to bypass actual permission prompts.

    Returns:
        Mock permission manager
    """
    from simple_agent.permissions.manager import PermissionManager
    from simple_agent.permissions.models import PermissionResponse

    manager = Mock(spec=PermissionManager)
    manager.check_permission.return_value = PermissionResponse(allowed=True)
    manager.get_session_policy.return_value = None
    # Mock get_permission_required_tools to return a dict
    manager.get_permission_required_tools.return_value = {
        "write_file": "high",
        "bash": "medium",
        "edit_file": "medium",
    }
    return manager


@pytest.fixture
def initialized_context(mock_settings, mock_provider, mock_permission_manager):
    """
    Create an initialized AgentContext with all dependencies.

    This is the most commonly used fixture for integration tests.

    Args:
        mock_settings: Mock settings fixture
        mock_provider: Mock provider fixture
        mock_permission_manager: Mock permission manager fixture

    Returns:
        Fully initialized AgentContext
    """
    from simple_agent.agent.context import AgentContext
    from simple_agent.managers.todo import TodoManager
    from simple_agent.managers.task import TaskManager
    from simple_agent.managers.background import BackgroundManager
    from simple_agent.managers.message import MessageBus
    from simple_agent.managers.teammate import TeammateManager
    from simple_agent.managers.skill import SkillLoader
    from simple_agent.managers.project import ProjectManager
    from simple_agent.managers.session import SessionManager
    # Create real manager instances with test settings
    todo = TodoManager()
    task = TaskManager(mock_settings)
    bg = BackgroundManager(mock_settings)
    bus = MessageBus(mock_settings)
    skill = SkillLoader(settings=mock_settings)
    teammate = TeammateManager(bus, task, mock_settings)
    project = ProjectManager(mock_settings)
    session = SessionManager(mock_settings)

    # Create context
    context = AgentContext(
        settings=mock_settings,
        todo=todo,
        task_mgr=task,
        bg=bg,
        bus=bus,
        skill_loader=skill,
        teammate=teammate,
        project_mgr=project,
        session_mgr=session,
        memory_mgr=None,
        provider=mock_provider,
    )

    return context


@pytest.fixture
def sample_files(temp_workspace):
    """
    Create sample files for testing file operations.

    Args:
        temp_workspace: Temporary workspace fixture

    Returns:
        Dictionary mapping filenames to their Path objects
    """
    files = {
        "test.txt": "Hello, World!",
        "test.py": "print('Hello')\n",
        "multiline.txt": "Line 1\nLine 2\nLine 3\n",
        "empty.txt": "",
        "chinese.txt": "你好，世界！\n",
    }

    created = {}
    for filename, content in files.items():
        path = temp_workspace / filename
        path.write_text(content, encoding='utf-8')
        created[filename] = path

    return created


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security test"
    )
