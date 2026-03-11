"""Bash command execution tool."""

import locale
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

    # Detect system encoding for better output handling
    try:
        system_encoding = locale.getpreferredencoding(False) or 'utf-8'
    except Exception:
        system_encoding = 'utf-8'

    # Try with detected/system encoding first
    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=True,
            encoding=system_encoding,
            errors='replace',  # Replace characters that can't be decoded
            timeout=timeout,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except (LookupError, UnicodeDecodeError):
        # Fallback to UTF-8 if system encoding fails
        try:
            r = subprocess.run(
                command,
                shell=True,
                cwd=workdir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
            )
            out = (r.stdout + r.stderr).strip()
            return out[:50000] if out else "(no output)"
        except Exception as e:
            # Last resort: try without encoding specification
            try:
                r = subprocess.run(
                    command,
                    shell=True,
                    cwd=workdir,
                    capture_output=True,
                    timeout=timeout,
                )
                # Decode with multiple fallback encodings
                output = r.stdout + r.stderr
                for encoding in ['utf-8', 'gbk', 'cp936', 'latin1']:
                    try:
                        out = output.decode(encoding)
                        return out.strip()[:50000] if out.strip() else "(no output)"
                    except (UnicodeDecodeError, LookupError):
                        continue
                # If all encodings fail, return raw bytes hint
                return f"Error: Unable to decode command output ({len(output)} bytes)"
            except Exception as e2:
                return f"Error: {e2}"
    except subprocess.TimeoutExpired:
        return f"Error: Timeout ({timeout}s)"
    except Exception as e:
        return f"Error: {e}"
