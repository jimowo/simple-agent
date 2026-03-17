"""Bash command execution tool."""

import subprocess
from pathlib import Path

from simple_agent.utils.constants import MAX_BASH_OUTPUT
from simple_agent.utils.encoding import decode_output, get_system_encoding


def run_bash(command: str, workdir: Path = None, timeout: int = 120) -> str:
    """
    Run a bash command in the workspace.

    Security: Permission checking and dangerous command detection are handled
    by the PermissionManager through the permission-aware wrapper. This function
    only executes the command after all security checks have passed.

    Args:
        command: Command to execute
        workdir: Working directory (uses Settings.workdir if None)
        timeout: Timeout in seconds

    Returns:
        Command output
    """
    if workdir is None:
        workdir = Path.cwd()

    # Use system encoding from utils.encoding
    system_encoding = get_system_encoding()

    # Try with detected/system encoding first
    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=True,
            encoding=system_encoding,
            errors="replace",  # Replace characters that can't be decoded
            timeout=timeout,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:MAX_BASH_OUTPUT] if out else "(no output)"
    except (LookupError, UnicodeDecodeError):
        # Fallback to UTF-8 if system encoding fails
        try:
            r = subprocess.run(
                command,
                shell=True,
                cwd=workdir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            out = (r.stdout + r.stderr).strip()
            return out[:MAX_BASH_OUTPUT] if out else "(no output)"
        except Exception:
            # Last resort: try without encoding specification
            try:
                r = subprocess.run(
                    command,
                    shell=True,
                    cwd=workdir,
                    capture_output=True,
                    timeout=timeout,
                )
                # Use decode_output utility for multiple encoding fallbacks
                output = r.stdout + r.stderr
                out = decode_output(output)
                return out.strip()[:MAX_BASH_OUTPUT] if out.strip() else "(no output)"
            except Exception as e:
                return f"Error: {e}"
    except subprocess.TimeoutExpired:
        return f"Error: Timeout ({timeout}s)"
    except Exception as e:
        return f"Error: {e}"
