"""Safety utilities for path operations."""

from pathlib import Path

from simple_agent.models.config import Settings


def safe_path(p: str, workdir: Path = None) -> Path:
    """
    Resolve a path safely, ensuring it stays within the workspace.

    Args:
        p: Path string to resolve
        workdir: Working directory (uses Settings.workdir if not provided)

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path escapes workspace
    """
    if workdir is None:
        workdir = Settings().workdir
    path = (workdir / p).resolve()
    if not path.is_relative_to(workdir):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


DANGEROUS_COMMANDS = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]


def is_dangerous_command(command: str) -> bool:
    """Check if a command contains dangerous patterns."""
    return any(d in command for d in DANGEROUS_COMMANDS)
