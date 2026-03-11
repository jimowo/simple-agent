"""Security tests for simple-agent.

This module tests security-critical functionality including:
- Dangerous command detection
- Path traversal prevention
- Command injection prevention
"""

import pytest
from pathlib import Path

from simple_agent.utils.safety import (
    is_dangerous_command,
    safe_path,
    CommandValidator,
)


@pytest.mark.security
class TestDangerousCommandDetection:
    """Test dangerous command detection functionality."""

    def test_obvious_dangerous_commands_blocked(self):
        """Test clearly dangerous commands are blocked."""
        dangerous_commands = [
            "rm -rf /",
            "rm -rf /home",
            "sudo rm -rf /",
            "shutdown -h now",
            "reboot",
            "halt",
            "poweroff",
            "cat /etc/passwd > /dev/null",
        ]

        for cmd in dangerous_commands:
            assert is_dangerous_command(cmd), f"Should block: {cmd}"

    def test_command_injection_attempts_blocked(self):
        """Test various command injection patterns are blocked."""
        injections = [
            "ls; rm -rf /",
            "ls && rm -rf /",
            "ls | rm -rf /",
            "ls || rm -rf /",
            "ls $(rm -rf /)",
            "ls `rm -rf /`",
            "ls; sudo shutdown",
            "cat /etc/passwd; rm -rf /",
        ]

        for cmd in injections:
            assert is_dangerous_command(cmd), f"Should block injection: {cmd}"

    def test_safe_commands_allowed(self):
        """Test safe commands are allowed through."""
        safe_commands = [
            "ls -la",
            "cat file.txt",
            "grep pattern file.txt",
            "git status",
            "git log --oneline",
            "pytest tests/",
            "python script.py",
            "echo hello",
            "pwd",
            "find . -name '*.py'",
        ]

        for cmd in safe_commands:
            assert not is_dangerous_command(cmd), f"Should allow: {cmd}"

    def test_unknown_commands_blocked(self):
        """Test unknown commands are considered dangerous."""
        unknown_commands = [
            "unknown_command args",
            "mysterious_tool --option",
            "obscure_binary input",
        ]

        for cmd in unknown_commands:
            assert is_dangerous_command(cmd), f"Should block unknown: {cmd}"

    def test_permission_required_commands(self):
        """Test commands that require explicit permission."""
        permission_commands = [
            "rm file.txt",
            "chmod 755 script.sh",
            "chown user:group file",
            "dd if=/dev/zero of=file",
        ]

        for cmd in permission_commands:
            assert is_dangerous_command(cmd), f"Should require permission: {cmd}"

    def test_package_manager_remove_blocked(self):
        """Test package manager remove commands are blocked."""
        remove_commands = [
            "apt remove package",
            "apt-get purge package",
            "yum erase package",
            "dnf remove package",
            "pacman -R package",
        ]

        for cmd in remove_commands:
            assert is_dangerous_command(cmd), f"Should block package remove: {cmd}"

    def test_find_with_exec_blocked(self):
        """Test find -exec is considered dangerous."""
        assert is_dangerous_command("find . -exec rm {} \\;")
        assert is_dangerous_command("find /tmp -type f -exec rm {} +")

    def test_whitespace_variations(self):
        """Test command detection works with various whitespace."""
        assert is_dangerous_command("  rm -rf /  ")
        assert is_dangerous_command("\trm -rf /\t")
        assert is_dangerous_command("sudo\tls")

    def test_chained_commands(self):
        """Test chained command detection."""
        assert is_dangerous_command("ls; rm file.txt")
        assert is_dangerous_command("ls && rm file.txt")
        assert is_dangerous_command("ls || rm file.txt")

    def test_sensitive_file_paths(self):
        """Test access to sensitive file paths is blocked."""
        sensitive = [
            "cat /etc/passwd",
            "cat /etc/shadow",
            "cat /etc/sudoers",
            "cat ~root/.ssh/id_rsa",
        ]

        for cmd in sensitive:
            assert is_dangerous_command(cmd), f"Should block sensitive access: {cmd}"


@pytest.mark.security
class TestSafePath:
    """Test safe path resolution functionality."""

    def test_normal_paths_allowed(self, temp_workspace):
        """Test normal path operations work correctly."""
        result = safe_path("file.txt", temp_workspace)
        assert result == temp_workspace / "file.txt"

        result = safe_path("subdir/file.txt", temp_workspace)
        assert result == temp_workspace / "subdir" / "file.txt"

    def test_absolute_path_within_workspace(self, temp_workspace):
        """Test absolute paths within workspace are allowed."""
        abs_path = temp_workspace / "file.txt"
        result = safe_path(str(abs_path), temp_workspace)
        assert result == abs_path

    def test_path_traversal_blocked(self, temp_workspace):
        """Test path traversal attempts are blocked."""
        traversal_attempts = [
            "../../etc/passwd",
            "../../../etc/passwd",
            "../..",
            "subdir/../../../etc/passwd",
        ]

        for attempt in traversal_attempts:
            with pytest.raises(ValueError, match="escapes workspace"):
                safe_path(attempt, temp_workspace)

    def test_tilde_expansion(self, temp_workspace):
        """Test tilde expansion is handled."""
        # Tilde expansion resolves to home directory
        # which is outside the temporary workspace
        # Note: This test assumes the home directory is different from temp_workspace
        from pathlib import Path
        home = Path.home()
        # Only test if home is actually different from temp workspace
        if home != temp_workspace and not str(temp_workspace).startswith(str(home)):
            with pytest.raises(ValueError, match="escapes workspace"):
                safe_path("~/.bashrc", temp_workspace)

    def test_nested_directory_creation(self, temp_workspace):
        """Test nested directory paths work correctly."""
        result = safe_path("a/b/c/d/file.txt", temp_workspace)
        assert result == temp_workspace / "a" / "b" / "c" / "d" / "file.txt"

    def test_current_directory_references(self, temp_workspace):
        """Test ./ references work correctly."""
        result = safe_path("./file.txt", temp_workspace)
        assert result == temp_workspace / "file.txt"

        result = safe_path("./subdir/../file.txt", temp_workspace)
        assert result == temp_workspace / "file.txt"

    def test_empty_path(self, temp_workspace):
        """Test empty path resolves to workspace."""
        result = safe_path("", temp_workspace)
        assert result == temp_workspace

    def test_unicode_paths(self, temp_workspace):
        """Test unicode characters in paths."""
        result = safe_path("测试文件.txt", temp_workspace)
        assert result == temp_workspace / "测试文件.txt"


@pytest.mark.security
class TestCommandValidator:
    """Test CommandValidator class directly."""

    def test_add_allowed_prefix(self):
        """Test adding custom allowed commands."""
        # Initially, docker is not in the default list
        # So it should be considered dangerous
        assert CommandValidator.is_dangerous("docker ps")

        # Add it to allowed list
        CommandValidator.add_allowed_prefix("docker")

        # Now it should be allowed
        # Note: This affects global state, so other tests might be affected
        assert not CommandValidator.is_dangerous("docker ps")

        # Reset for other tests
        CommandValidator.ALLOWED_PREFIXES.discard("docker")

    def test_add_dangerous_pattern(self):
        """Test adding custom dangerous patterns."""
        # This command is not initially dangerous
        test_cmd = "custom_tool --dangerous"

        # Add pattern to make it dangerous
        CommandValidator.add_dangerous_pattern(r'custom_tool.*dangerous')

        assert CommandValidator.is_dangerous(test_cmd)

        # Clean up
        CommandValidator.DANGEROUS_PATTERNS.pop()


@pytest.mark.security
class TestEdgeCases:
    """Test edge cases in security functions."""

    def test_empty_command(self):
        """Test empty command handling."""
        assert not is_dangerous_command("")
        assert not is_dangerous_command("   ")
        assert not is_dangerous_command("\t")

    def test_very_long_command(self):
        """Test very long command strings don't cause issues."""
        long_cmd = "ls " + "a" * 10000
        # Should not crash
        result = is_dangerous_command(long_cmd)
        assert isinstance(result, bool)

    def test_special_characters(self):
        """Test special characters are handled."""
        special_chars = [
            "echo $HOME",
            "echo $((1+1))",
            "echo 'test'",
            'echo "test"',
            "echo `echo test`",
        ]

        for cmd in special_chars:
            # Should not crash
            result = is_dangerous_command(cmd)
            assert isinstance(result, bool)

    def test_invalid_escape_sequences(self, temp_workspace):
        """Test invalid escape sequences don't crash safe_path."""
        # These should not crash, even if invalid
        invalid_paths = [
            "file\x00.txt",
            "dir\x01\x02/file.txt",
        ]

        for path in invalid_paths:
            try:
                result = safe_path(path, temp_workspace)
                # If it succeeds, check it's a Path object
                assert isinstance(result, Path)
            except (ValueError, RuntimeError):
                # Also acceptable to raise an error
                pass
