"""Test bash command execution tools."""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from simple_agent.tools.bash_tools import run_bash


@pytest.mark.security
class TestRunBash:
    """Test bash command execution functionality."""

    def test_simple_command(self, temp_workspace):
        """Test simple command execution."""
        # Create a test file first
        test_file = temp_workspace / "test.txt"
        test_file.write_text("test content")

        result = run_bash("ls", temp_workspace, timeout=5)
        assert "test.txt" in result

    def test_echo_command(self):
        """Test echo command."""
        result = run_bash("echo hello", Path.cwd(), timeout=5)
        assert "hello" in result.lower()

    def test_dangerous_command_blocked(self):
        """Test that dangerous commands are blocked."""
        dangerous_commands = [
            "rm -rf /",
            "sudo rm -rf /home",
        ]

        for cmd in dangerous_commands:
            result = run_bash(cmd, Path.cwd(), timeout=5)
            assert "blocked" in result.lower() or "error" in result.lower()

    def test_timeout(self):
        """Test command timeout functionality."""
        # Use a safe command that will timeout
        # Note: sleep is not in whitelist, so we use a different approach
        # We'll use mock to test timeout behavior
        import subprocess
        with patch('simple_agent.tools.bash_tools.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("python", 1)
            result = run_bash("python script.py", Path.cwd(), timeout=1)
            assert "timeout" in result.lower()

    def test_working_directory(self, temp_workspace):
        """Test command execution in specific directory."""
        # Create a file in temp workspace
        (temp_workspace / "marker.txt").write_text("marker")

        # Run command from temp workspace
        result = run_bash("ls", temp_workspace, timeout=5)
        assert "marker.txt" in result

    def test_nonexistent_command(self):
        """Test handling of nonexistent command."""
        result = run_bash("nonexistent_command_xyz", Path.cwd(), timeout=5)
        assert "error" in result.lower() or "not found" in result.lower()

    def test_command_with_arguments(self):
        """Test command with multiple arguments."""
        result = run_bash("echo -n 'no newline'", Path.cwd(), timeout=5)
        assert "no newline" in result.lower()

    def test_piped_command_blocked(self):
        """Test that piped dangerous commands are blocked."""
        dangerous_pipes = [
            "ls | rm -rf /",
            "cat /etc/passwd | sh",
        ]

        for cmd in dangerous_pipes:
            result = run_bash(cmd, Path.cwd(), timeout=5)
            # Should be blocked by safety check
            assert "blocked" in result.lower() or "error" in result.lower()

    def test_chained_command_blocked(self):
        """Test that chained dangerous commands are blocked."""
        dangerous_chains = [
            "ls; rm -rf /",
            "ls && rm -rf /",
            "ls || rm -rf /",
        ]

        for cmd in dangerous_chains:
            result = run_bash(cmd, Path.cwd(), timeout=5)
            assert "blocked" in result.lower() or "error" in result.lower()

    def test_command_substitution_blocked(self):
        """Test that command substitution with dangerous commands is blocked."""
        dangerous_subst = [
            "echo $(rm -rf /)",
            "echo `rm -rf /`",
        ]

        for cmd in dangerous_subst:
            result = run_bash(cmd, Path.cwd(), timeout=5)
            assert "blocked" in result.lower() or "error" in result.lower()

    @patch('simple_agent.tools.bash_tools.subprocess.run')
    def test_encoding_fallback(self, mock_run):
        """Test encoding fallback behavior."""
        # Simulate encoding error on first attempt, success on second
        mock_run.side_effect = [
            Mock(side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, '')),
            Mock(stdout=b'output', stderr=b'', returncode=0)
        ]

        result = run_bash("echo test", Path.cwd(), timeout=5)
        # Should fallback and not crash
        assert isinstance(result, str)

    @patch('simple_agent.tools.bash_tools.subprocess.run')
    def test_subprocess_exception_handling(self, mock_run):
        """Test subprocess exception handling."""
        mock_run.side_effect = Exception("Subprocess error")

        result = run_bash("python -c \"print('test')\"", Path.cwd(), timeout=5)
        assert "error" in result.lower()

    def test_empty_command(self):
        """Test empty command handling."""
        result = run_bash("", Path.cwd(), timeout=5)
        assert isinstance(result, str)

    def test_whitespace_command(self):
        """Test whitespace-only command."""
        result = run_bash("   ", Path.cwd(), timeout=5)
        assert isinstance(result, str)

    def test_output_truncation(self):
        """Test that large output is truncated."""
        # Create a command that produces lots of output
        result = run_bash("python3 -c \"print('x' * 60000)\"", Path.cwd(), timeout=5)
        # Should be truncated to 50000 characters
        assert len(result) <= 50000

    def test_command_with_newlines(self):
        """Test command that contains newlines."""
        # Use echo with -e flag for newlines
        result = run_bash('echo -e "line1\\nline2"', Path.cwd(), timeout=5)
        # On Windows, echo might behave differently, so we just check it doesn't crash
        assert isinstance(result, str)

    @patch('simple_agent.tools.bash_tools.subprocess.run')
    def test_timeout_exception(self, mock_run):
        """Test timeout exception handling."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("echo", 1)

        result = run_bash("python -c \"print('test')\"", Path.cwd(), timeout=1)
        assert "timeout" in result.lower()


@pytest.mark.security
class TestBashToolsSecurity:
    """Test security aspects of bash tools."""

    def test_sudo_command_blocked(self):
        """Test that sudo commands are blocked."""
        sudo_commands = [
            "sudo ls",
            "sudo -i",
            "sudo su",
        ]

        for cmd in sudo_commands:
            result = run_bash(cmd, Path.cwd(), timeout=5)
            assert "blocked" in result.lower() or "error" in result.lower()

    def test_sensitive_file_access_blocked(self):
        """Test that sensitive file access is blocked."""
        sensitive = [
            "cat /etc/passwd",
            "cat /etc/shadow",
            "cat /etc/sudoers",
        ]

        for cmd in sensitive:
            result = run_bash(cmd, Path.cwd(), timeout=5)
            assert "blocked" in result.lower() or "error" in result.lower()

    def test_package_remove_blocked(self):
        """Test that package removal commands are blocked."""
        remove_commands = [
            "apt remove package",
            "yum erase package",
            "dnf remove package",
        ]

        for cmd in remove_commands:
            result = run_bash(cmd, Path.cwd(), timeout=5)
            assert "blocked" in result.lower() or "error" in result.lower()
