"""Tests for Agent initialization behavior."""

from unittest.mock import Mock, patch

from simple_agent.agent.base import Agent
from simple_agent.agent.context import AgentContext
from simple_agent.tools.handler_registry import ToolHandlerRegistry


class TestAgentInitialization:
    """Test Agent initialization paths and compatibility behavior."""

    def test_context_argument_takes_priority(self, initialized_context):
        """Test that a provided context bypasses container and legacy resolution."""
        permission_manager = Mock()

        with patch("simple_agent.agent.base.AgentContext.from_container") as mock_from_container:
            agent = Agent(context=initialized_context, permission_manager=permission_manager)

        assert agent._ctx is initialized_context
        assert agent.permission_manager is permission_manager
        assert isinstance(agent._tool_registry, ToolHandlerRegistry)
        mock_from_container.assert_not_called()

    def test_modern_initialization_uses_container(self, mock_settings):
        """Test that the default initialization path resolves context from the container."""
        mock_context = Mock(spec=AgentContext)
        mock_context.settings = mock_settings
        permission_manager = Mock()

        with patch("simple_agent.agent.base.AgentContext.from_container", return_value=mock_context) as mock_from_container:
            agent = Agent(settings=mock_settings, permission_manager=permission_manager)

        mock_from_container.assert_called_once_with(mock_settings)
        assert agent._ctx is mock_context
        assert agent.permission_manager is permission_manager

    def test_legacy_manager_arguments_use_legacy_context(self, mock_settings):
        """Test that legacy manager injection uses the legacy compatibility path."""
        permission_manager = Mock()
        mock_context = Mock(spec=AgentContext)
        mock_context.settings = mock_settings
        todo_manager = Mock()

        with patch.object(Agent, "_create_legacy_context", return_value=mock_context) as mock_create_legacy:
            with patch("simple_agent.agent.base.AgentContext.from_container") as mock_from_container:
                agent = Agent(
                    settings=mock_settings,
                    todo_manager=todo_manager,
                    permission_manager=permission_manager,
                )

        mock_create_legacy.assert_called_once()
        mock_from_container.assert_not_called()
        assert agent._ctx is mock_context
        assert agent.permission_manager is permission_manager

    def test_default_permission_manager_is_created(self, initialized_context):
        """Test that Agent creates a default permission manager when none is provided."""
        mock_permission_manager = Mock()

        with patch("simple_agent.permissions.PermissionManager", return_value=mock_permission_manager):
            agent = Agent(context=initialized_context)

        assert agent.permission_manager is mock_permission_manager
