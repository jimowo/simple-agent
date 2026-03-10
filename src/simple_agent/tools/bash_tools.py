"""Bash command execution tool."""

import subprocess
from pathlib import Path

from simple_agent.utils.safety import is_dangerous_command


def run_bash(command: str, workdir: Path = None, timeout: int = 120) -> str:
    """
    Run a bash command in the workspace.

    Args:
        command: Command to execute
        workdir: Working directory (uses Settings.workdir if None)
        timeout: Timeout in seconds

    Returns:
        Command output
    """
    if workdir is None:
        workdir = Path.cwd()

    if is_dangerous_command(command):
        return "Error: Dangerous command blocked"

    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Replace characters that can't be decoded
            timeout=timeout,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: Timeout ({timeout}s)"
    except UnicodeDecodeError:
        # Fallback to system default encoding if UTF-8 fails
        try:
            r = subprocess.run(
                command,
                shell=True,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            out = (r.stdout + r.stderr).strip()
            return out[:50000] if out else "(no output)"
        except Exception as e:
            return f"Error: {e}"
