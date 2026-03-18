"""CLI integration tests for simple-agent."""
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from simple_agent.cli.main import app
from simple_agent.models.config import initialize_config


@pytest.fixture(autouse=True)
def init_config():
    """Initialize configuration before each CLI test."""
    initialize_config()


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestCLICommands:
    """Test basic CLI commands."""

    def test_version_command(self, runner):
        """Test the version command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "version" in result.stdout.lower()

    def test_providers_command(self, runner):
        """Test the providers list command."""
        result = runner.invoke(app, ["providers"])
        assert result.exit_code == 0
        assert "Available AI Providers" in result.stdout
        # Check that some expected providers are listed
        assert "anthropic" in result.stdout
        assert "openai" in result.stdout

    def test_help_command(self, runner):
        """Test the help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "simple-agent" in result.stdout


class TestTaskCommands:
    """Test task management commands."""

    def test_task_list_empty(self, runner, temp_workspace):
        """Test task list with no tasks."""
        result = runner.invoke(app, ["task-list"])
        assert result.exit_code == 0
        # Should show something even with no tasks

    def test_task_create(self, runner, temp_workspace):
        """Test creating a new task."""
        result = runner.invoke(
            app,
            ["task-create", "Test task", "--description", "Test description"]
        )
        assert result.exit_code == 0
        assert "Created task" in result.stdout


class TestProjectCommands:
    """Test project management commands."""

    def test_project_list(self, runner):
        """Test listing projects."""
        result = runner.invoke(app, ["project-list"])
        assert result.exit_code == 0
        # Should show projects or empty message


class TestSessionCommands:
    """Test session management commands."""

    def test_session_list(self, runner):
        """Test listing sessions."""
        result = runner.invoke(app, ["session-list"])
        assert result.exit_code == 0
        # Should handle no current project gracefully


class TestCLIOptions:
    """Test CLI global options."""

    def test_provider_option(self, runner):
        """Test --provider option."""
        result = runner.invoke(app, ["--provider", "openai", "providers"])
        assert result.exit_code == 0

    def test_model_option(self, runner):
        """Test --model option."""
        result = runner.invoke(app, ["--model", "gpt-4o", "version"])
        assert result.exit_code == 0

    def test_workdir_option(self, runner, temp_workspace):
        """Test --workdir option."""
        result = runner.invoke(
            app,
            ["--workdir", str(temp_workspace), "version"]
        )
        assert result.exit_code == 0


class TestCLIIntegration:
    """Integration tests for CLI with actual agent."""

    def test_run_command_basic(self, runner, mock_provider, temp_workspace):
        """Test the run command with a simple prompt."""
        with patch('simple_agent.cli.main._get_agent') as mock_get_agent, patch(
            'simple_agent.agent.loop.AgentLoop.run'
        ) as mock_run:
            mock_agent = Mock()
            mock_agent._ctx = Mock()
            mock_agent._tool_registry = Mock()
            mock_agent.permission_manager = Mock()
            mock_get_agent.return_value = mock_agent

            def populate_history(history):
                history.append(
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Test response"}],
                    }
                )

            mock_run.side_effect = populate_history
            result = runner.invoke(app, ["run", "Hello"])
            assert result.exit_code == 0
            assert "Test response" in result.stdout

    def test_chat_command_requires_interactive(self, runner):
        """Test that chat command would require interactive mode."""
        # Chat command can't be tested in non-interactive mode
        # This is just to verify the command exists
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "Start interactive chat mode" in result.stdout


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_invalid_command(self, runner):
        """Test that invalid commands show help."""
        result = runner.invoke(app, ["nonexistent-command"])
        assert result.exit_code != 0

    def test_task_get_nonexistent(self, runner):
        """Test getting a non-existent task."""
        result = runner.invoke(app, ["task-get", "99999"])
        assert result.exit_code != 0
