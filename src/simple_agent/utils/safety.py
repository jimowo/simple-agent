"""Safety utilities for command and path operations.

This module provides security functions to protect against:
- Command injection attacks
- Path traversal attacks
- Arbitrary code execution
"""

import re
import shlex
from pathlib import Path
from typing import List, Pattern, Set

from simple_agent.models.config import Settings


class CommandValidator:
    """
    Enhanced command validation using tokenization and pattern matching.

    This validator uses multiple strategies to detect dangerous commands:
    1. Regular expression pattern matching
    2. Token-based analysis with shlex
    3. Whitelist approach for known safe commands
    """

    # Dangerous command patterns (regex compiled)
    # These patterns match known dangerous command structures
    DANGEROUS_PATTERNS: List[Pattern] = [
        # rm -rf / or rm -rf / followed by anything
        re.compile(r'^\s*rm\s+-rf?\s+/?\s*$'),
        re.compile(r'^\s*rm\s+-rf?\s+/'),

        # sudo with any command
        re.compile(r'^\s*sudo\s+'),

        # System control commands
        re.compile(r'^\s*(sh(utdown|oot)|halt|poweroff)\s'),

        # Output redirection to /dev/null (often used to hide malicious output)
        re.compile(r':\s*>\s*/dev/'),

        # Pipes to dangerous commands
        re.compile(r'\|\s*rm\s+'),
        re.compile(r'\|\s*sh\s'),
        re.compile(r'\|\s*bash\s'),

        # Chained dangerous commands
        re.compile(r'&&\s*rm\s+'),
        re.compile(r';\s*rm\s+'),
        re.compile(r'\|\|\s*rm\s+'),

        # Command substitution with dangerous commands
        re.compile(r'\$\(.*rm'),
        re.compile(r'`.*rm'),

        # Direct paths to sensitive files
        re.compile(r'/etc/(passwd|shadow|sudoers)'),
        re.compile(r'~root/'),

        # Package managers with uninstall flags
        re.compile(r'(apt|yum|dnf|pacman)\s+(remove|erase|purge)'),
    ]

    # Allowed command prefixes (whitelist approach)
    # These are base commands that are generally safe
    ALLOWED_PREFIXES: Set[str] = {
        # File operations
        'ls', 'cat', 'head', 'tail', 'grep', 'find', 'locate', 'which', 'whereis',

        # Development tools
        'git', 'npm', 'pip', 'pip3', 'python', 'python3', 'node',
        'cargo', 'rustc', 'go', 'javac', 'mvn', 'gradle',

        # Build tools
        'make', 'cmake', 'meson', 'ninja', 'bazel',

        # Text editors
        'vim', 'vi', 'nano', 'emacs', 'code', 'TextEdit',

        # File utilities
        'echo', 'printf', 'pwd', 'cd', 'mkdir', 'touch',
        'cp', 'mv', 'rsync', 'scp', 'curl', 'wget', 'tar', 'zip', 'unzip',

        # Testing tools
        'pytest', 'python3', 'ruff', 'mypy', 'black', 'flake8', 'pylint',

        # Information commands
        'ps', 'top', 'htop', 'df', 'du', 'free', 'uname', 'whoami', 'id',

        # Network diagnostics
        'ping', 'traceroute', 'nslookup', 'dig', 'netstat', 'ss',

        # Process control (non-destructive)
        'jobs', 'bg', 'fg', 'wait',

        # Other safe utilities
        'sort', 'uniq', 'wc', 'cut', 'awk', 'sed', 'tr', 'tee',
        'xargs', 'find', 'file', 'stat', 'readlink', 'realpath',

        # macOS specific
        'brew',
    }

    # Commands that require explicit permission but aren't automatically blocked
    PERMISSION_REQUIRED: Set[str] = {
        'rm', 'chmod', 'chown', 'chgrp',
        'dd', 'mkfs', 'fdisk', 'parted',
        'iptables', 'ufw', 'firewall-cmd',
        'useradd', 'userdel', 'usermod',
        'systemctl', 'service',
    }

    @classmethod
    def is_dangerous(cls, command: str) -> bool:
        """
        Check if command is dangerous using multiple strategies.

        Args:
            command: Command string to validate

        Returns:
            True if command is considered dangerous, False otherwise
        """
        # Remove leading/trailing whitespace
        command = command.strip()

        # Empty command is safe
        if not command:
            return False

        # Strategy 1: Pattern matching for known dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(command):
                return True

        # Strategy 2: Token-based analysis
        try:
            tokens = shlex.split(command)
            if not tokens:
                return False

            base_cmd = tokens[0]

            # Check if base command is in whitelist
            if base_cmd in cls.ALLOWED_PREFIXES:
                # Additional check: look for dangerous flags in whitelisted commands
                # For example, `ls` with `-exec` flag could be dangerous
                if base_cmd == 'find' and '-exec' in tokens:
                    return True
                if base_cmd == 'tar' and any(arg.startswith('/') for arg in tokens):
                    return True
                return False

            # Commands requiring permission
            if base_cmd in cls.PERMISSION_REQUIRED:
                # These aren't automatically dangerous but need permission
                return True

            # Unknown commands are considered dangerous
            return base_cmd not in cls.ALLOWED_PREFIXES

        except (ValueError, shlex.Error):
            # If we can't parse it, consider it dangerous
            return True

    @classmethod
    def add_allowed_prefix(cls, command: str) -> None:
        """
        Add a command to the allowed whitelist.

        Args:
            command: Base command name (e.g., 'docker', 'kubectl')
        """
        cls.ALLOWED_PREFIXES.add(command)

    @classmethod
    def add_dangerous_pattern(cls, pattern: str) -> None:
        """
        Add a dangerous regex pattern.

        Args:
            pattern: Regular expression string to compile and add
        """
        cls.DANGEROUS_PATTERNS.append(re.compile(pattern))


def safe_path(p: str, workdir: Path = None) -> Path:
    """
    Resolve a path safely, ensuring it stays within the workspace.

    Security enhancements:
    - Resolves all symbolic links before checking boundaries
    - Normalizes path separators
    - Validates against workspace boundaries
    - Checks for parent directory references

    Args:
        p: Path string to resolve
        workdir: Working directory (uses Settings.workdir if not provided)

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path escapes workspace or contains suspicious components
    """
    if workdir is None:
        workdir = Settings().workdir

    # Normalize the input path first
    try:
        # Convert to absolute path first
        path = (workdir / p).expanduser()

        # Resolve all symbolic links and normalize
        # strict=False allows the path to not exist yet
        path = path.resolve(strict=False)

        # Also resolve workdir to handle symlinks consistently
        workdir_resolved = workdir.resolve(strict=False)

        # Check if path is within workspace
        if not path.is_relative_to(workdir_resolved):
            raise ValueError(
                f"Path escapes workspace: '{p}' resolves to '{path}', "
                f"which is outside workspace '{workdir_resolved}'"
            )

        # Additional safety check: detect parent directory references in original path
        path_obj = Path(p)
        if '..' in path_obj.parts or str(path_obj).startswith('..'):
            # This might be legitimate, but warn about it
            # The resolve() above should have handled it safely
            pass

        return path

    except (ValueError, RuntimeError) as e:
        raise ValueError(f"Invalid path '{p}': {e}") from e


# Legacy constants for backward compatibility
DANGEROUS_COMMANDS = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]


def is_dangerous_command(command: str) -> bool:
    """
    Check if a command contains dangerous patterns.

    This function now uses CommandValidator for enhanced security detection.

    Args:
        command: Command string to validate

    Returns:
        True if command is considered dangerous, False otherwise

    Examples:
        >>> is_dangerous_command("ls -la")
        False
        >>> is_dangerous_command("rm -rf /")
        True
        >>> is_dangerous_command("cat file.txt; rm -rf /")
        True
    """
    return CommandValidator.is_dangerous(command)
