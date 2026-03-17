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

from simple_agent.exceptions import PathTraversalError
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
        # === File deletion attacks ===
        # rm -rf / or rm -rf / followed by anything
        re.compile(r'^\s*rm\s+-rf?\s+/?\s*$'),
        re.compile(r'^\s*rm\s+-rf?\s+/'),
        # Recursive deletion in home directory
        re.compile(r'rm\s+-rf\s+~?/'),
        # Force deletion of system files
        re.compile(r'rm\s+-f\s+/etc/'),
        re.compile(r'rm\s+-f\s+/bin/'),
        re.compile(r'rm\s+-f\s+/usr/'),
        re.compile(r'rm\s+-f\s+/var/'),

        # === Privilege escalation ===
        # sudo with any command
        re.compile(r'^\s*sudo\s+'),
        # su command
        re.compile(r'^\s*su\s+'),
        # pkexec
        re.compile(r'^\s*pkexec'),

        # === System control commands ===
        re.compile(r'^\s*(sh(utdown|oot)|halt|poweroff)\s'),
        re.compile(r'^\s*reboot\s'),
        re.compile(r'^\s*init\s+\d'),
        re.compile(r'^\s*systemctl\s+(poweroff|reboot|halt)'),

        # === Data exfiltration hiding ===
        # Output redirection to /dev/null (often used to hide malicious output)
        re.compile(r':\s*>\s*/dev/'),
        re.compile(r'>\s*/dev/null'),
        # Redirection to network sockets
        re.compile(r'>\s*/dev/tcp/'),
        re.compile(r'>\s*/dev/udp/'),

        # === Command chaining attacks ===
        # Pipes to dangerous commands
        re.compile(r'\|\s*rm\s+'),
        re.compile(r'\|\s*sh\s*$'),
        re.compile(r'\|\s*sh\s+'),
        re.compile(r'\|\s*bash\s'),
        re.compile(r'\|\s*python[23]?\s+.*os\.'),
        re.compile(r'\|\s*perl\s+.*system'),
        re.compile(r'\|\s*ruby\s+.*system'),

        # Chained dangerous commands
        re.compile(r'&&\s*rm\s+'),
        re.compile(r';\s*rm\s+'),
        re.compile(r'\|\|\s*rm\s+'),
        re.compile(r'\n\s*rm\s+'),  # Newline followed by rm

        # === Command substitution attacks ===
        # Command substitution with dangerous commands
        re.compile(r'\$\(.*rm'),
        re.compile(r'`.*rm'),
        re.compile(r'\$\{.*:'),
        re.compile(r'\$\[.*\]'),  # Arithmetic expansion with potential exploits

        # === Sensitive file access ===
        # Direct paths to sensitive files
        re.compile(r'/etc/(passwd|shadow|sudoers|gshadow|hosts)'),
        re.compile(r'~root/'),
        re.compile(r'/root/'),
        re.compile(r'/home/.*?/\.ssh/'),
        re.compile(r'/home/.*?/\.gnupg/'),
        re.compile(r'\.ssh/id_rsa'),
        re.compile(r'\.ssh/id_ed25519'),
        re.compile(r'\.gnupg/.*private'),
        re.compile(r'\.gnupg/secring'),
        re.compile(r'\.gnupg/.*\.gpg'),

        # === Package management ===
        # Package managers with uninstall flags
        re.compile(r'(apt|yum|dnf|pacman)\s+(remove|erase|purge|autoremove)'),
        re.compile(r'pip[23]?\s+uninstall'),
        re.compile(r'npm\s+uninstall\s+-g'),

        # === Network-related dangerous commands ===
        # iptables flush (could disable firewall)
        re.compile(r'iptables\s+-F'),
        re.compile(r'iptables\s+--flush'),
        # Downloading and executing scripts
        re.compile(r'curl\s+\S+\s*\|\s*sh'),
        re.compile(r'wget\s+\S+\s*\|\s*sh'),
        re.compile(r'curl\s+\S+\s*&&.*sh'),
        re.compile(r'wget\s+\S+\s*&&.*sh'),

        # === Process manipulation ===
        # Killing critical processes
        re.compile(r'kill\s+-9\s+1'),
        re.compile(r'killall\s+'),
        re.compile(r'pkill\s+'),
        # ptrace attacks (potential code injection)
        re.compile(r'ptrace'),

        # === Disk and filesystem operations ===
        # Disk formatting/wiping
        re.compile(r'mkfs'),
        re.compile(r'fdisk'),
        re.compile(r'parted'),
        # dd with dangerous patterns (disk wiping)
        re.compile(r'dd\s+.*of=/dev/(sd|hd|nvme)'),
        re.compile(r'dd\s+.*if=/dev/zero'),
        re.compile(r'dd\s+.*if=/dev/random'),

        # === Configuration modification ===
        # Modifying system configuration
        re.compile(r'echo.*>>\s*/etc/'),
        re.compile(r'printf.*>>\s*/etc/'),
        # Crontab modification
        re.compile(r'crontab\s+-'),
        # systemd service modification and symlink attacks
        re.compile(r'ln\s+-s.*\.service'),
        re.compile(r'ln\s+-s.*\.(bashrc|zshrc|profile)'),
        re.compile(r'ln\s+-s\s*/dev/null'),

        # === Encoding/decoding attacks ===
        # Base64 decoding with execution
        re.compile(r'base64\s+-d.*\|\s*(sh|bash)'),
        re.compile(r'base64\s+-d.*&&(sh|bash)'),
        re.compile(r'base64\s+-d.*;\s*(sh|bash)'),

        # === History hiding ===
        # Commands to clear history (often used before malicious commands)
        re.compile(r'history\s+-c'),
        re.compile(r'unset\s+HISTFILE'),
        re.compile(r'export\s+HISTSIZE=0'),
    ]

    # Allowed command prefixes (whitelist approach)
    # These are base commands that are generally safe
    ALLOWED_PREFIXES: Set[str] = {
        # File operations
        'ls', 'cat', 'head', 'tail', 'grep', 'find', 'locate', 'which', 'whereis',
        'less', 'more', 'tree', 'bat',

        # Development tools
        'git', 'npm', 'pip', 'pip3', 'python', 'python3', 'node',
        'cargo', 'rustc', 'go', 'javac', 'mvn', 'gradle',
        'poetry', 'pnpm', 'yarn', 'bun',

        # Build tools
        'make', 'cmake', 'meson', 'ninja', 'bazel', 'scons',

        # Text editors
        'vim', 'vi', 'nano', 'emacs', 'code', 'TextEdit',
        'subl', 'atom', 'hx',

        # File utilities
        'echo', 'printf', 'pwd', 'cd', 'mkdir', 'touch',
        'cp', 'mv', 'rsync', 'scp', 'curl', 'wget', 'tar', 'zip', 'unzip',
        'ln', 'basename', 'dirname', 'realpath',

        # Testing tools
        'pytest', 'python3', 'ruff', 'mypy', 'black', 'flake8', 'pylint',
        'coverage', 'tox', 'nox',

        # Information commands
        'ps', 'top', 'htop', 'df', 'du', 'free', 'uname', 'whoami', 'id',
        'env', 'printenv', 'uptime', 'date', 'cal', 'type',

        # Network diagnostics
        'ping', 'traceroute', 'nslookup', 'dig', 'netstat', 'ss',
        'lsof', 'ncat', 'nc',

        # Process control (non-destructive)
        'jobs', 'bg', 'fg', 'wait', 'disown',

        # Other safe utilities
        'sort', 'uniq', 'wc', 'cut', 'awk', 'sed', 'tr', 'tee',
        'xargs', 'file', 'stat', 'readlink', 'realpath',
        'diff', 'cmp', 'comm', 'join', 'paste',
        'base64', 'md5sum', 'sha1sum', 'sha256sum',

        # Compression
        'gzip', 'gunzip', 'bzip2', 'bunzip2', 'xz', 'unxz',
        '7z', 'uncompress', 'zcat',

        # macOS specific
        'brew', 'open',

        # Windows (WSL/Git Bash) safe commands
        'explorer.exe', 'cmd.exe', 'powershell.exe',
    }

    # Commands that require explicit permission but aren't automatically blocked
    PERMISSION_REQUIRED: Set[str] = {
        'rm', 'chmod', 'chown', 'chgrp',
        'dd', 'mkfs', 'fdisk', 'parted',
        'iptables', 'ufw', 'firewall-cmd',
        'useradd', 'userdel', 'usermod',
        'systemctl', 'service',
        'crontab',
        'mount', 'umount',
        'sysctl',
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

                # find -exec with dangerous commands
                if base_cmd == 'find':
                    exec_idx = -1
                    for i, token in enumerate(tokens):
                        if token == '-exec' or token == '-execdir':
                            exec_idx = i
                            break
                    if exec_idx != -1 and exec_idx + 1 < len(tokens):
                        next_token = tokens[exec_idx + 1]
                        # Check if -exec is followed by a dangerous command
                        dangerous_after_exec = {'rm', 'sh', 'bash', 'python', 'python3', 'perl', 'ruby'}
                        if any(next_token.startswith(d) for d in dangerous_after_exec):
                            return True
                    # Check for find with -delete flag
                    if '-delete' in tokens:
                        return True

                # tar with absolute paths or dangerous options
                if base_cmd == 'tar':
                    # Check for absolute path extraction
                    if any(arg.startswith('/') for arg in tokens):
                        return True
                    # Check for dangerous flags
                    dangerous_tar_flags = {'--overwrite', '--overwrite-dir', '--recursive-unlink'}
                    if any(arg in dangerous_tar_flags or arg.startswith('--overwrite=') for arg in tokens):
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
            raise PathTraversalError(str(p), str(workdir_resolved))

        # Additional safety check: detect parent directory references in original path
        path_obj = Path(p)
        if '..' in path_obj.parts or str(path_obj).startswith('..'):
            # This might be legitimate, but warn about it
            # The resolve() above should have handled it safely
            pass

        return path

    except (ValueError, RuntimeError) as e:
        raise PathTraversalError(str(p), f"Invalid path: {e}") from e


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
