"""Bash command execution tool."""

import shlex
import subprocess
import sys
from pathlib import Path

from simple_agent.utils.constants import MAX_BASH_OUTPUT
from simple_agent.utils.encoding import decode_output, get_system_encoding
from simple_agent.utils.safety import CommandValidator


def _truncate_output(output: str) -> str:
    """Truncate output to the configured maximum length."""
    return output[:MAX_BASH_OUTPUT] if output else "(no output)"


def _should_block_direct_execution(command: str) -> bool:
    """Block obviously dangerous commands for direct run_bash() calls.

    This is intentionally narrower than PermissionManager's policy:
    unknown commands should still be allowed to execute and fail naturally.
    """
    command = command.strip()
    if not command:
        return False

    for pattern in CommandValidator.DANGEROUS_PATTERNS:
        if pattern.search(command):
            return True

    try:
        tokens = shlex.split(command)
    except ValueError:
        return True

    if not tokens:
        return False

    base_cmd = tokens[0]
    if base_cmd in CommandValidator.PERMISSION_REQUIRED:
        return True

    if base_cmd in CommandValidator.ALLOWED_PREFIXES:
        if base_cmd == "find":
            if "-delete" in tokens:
                return True
            for i, token in enumerate(tokens):
                if token in {"-exec", "-execdir"} and i + 1 < len(tokens):
                    next_token = tokens[i + 1]
                    if any(
                        next_token.startswith(dangerous)
                        for dangerous in ("rm", "sh", "bash", "python", "python3", "perl", "ruby")
                    ):
                        return True
        if base_cmd == "tar":
            dangerous_tar_flags = {"--overwrite", "--overwrite-dir", "--recursive-unlink"}
            if any(arg in dangerous_tar_flags or arg.startswith("--overwrite=") for arg in tokens):
                return True
            if any(arg.startswith("/") for arg in tokens[1:]):
                return True

    return False


def _resolve_command_path(raw_path: str, workdir: Path) -> Path:
    """Resolve a command argument to a filesystem path."""
    path = Path(raw_path)
    return path if path.is_absolute() else workdir / path


def _execute_builtin_command(command: str, workdir: Path) -> str | None:
    """Execute a small set of safe, portable built-in commands."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None

    if not tokens:
        return "(no output)"

    base_cmd = tokens[0]

    if base_cmd == "ls":
        targets = [arg for arg in tokens[1:] if not arg.startswith("-")]
        target = _resolve_command_path(targets[0], workdir) if targets else workdir
        if not target.exists():
            return f"Error: Path not found: {target}"
        if target.is_file():
            return _truncate_output(target.name)
        items = sorted(child.name for child in target.iterdir())
        return _truncate_output("\n".join(items))

    if base_cmd == "cat":
        raw_args = command[len("cat"):].strip()
        if raw_args and len(tokens) <= 2 and not tokens[1].startswith("-"):
            file_args = [raw_args.strip("\"'")]
        else:
            file_args = [arg for arg in tokens[1:] if not arg.startswith("-")]
        if not file_args:
            return "Error: Missing file path"

        contents = []
        for file_arg in file_args:
            path = _resolve_command_path(file_arg, workdir)
            if not path.exists():
                return f"Error: File not found: {path}"
            try:
                contents.append(path.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                contents.append(path.read_text())
        return _truncate_output("\n".join(contents).rstrip())

    if base_cmd == "pwd":
        return _truncate_output(str(workdir))

    if base_cmd == "echo":
        interpret_escapes = False
        append_newline = True
        payload = []

        for token in tokens[1:]:
            if token == "-n":
                append_newline = False
            elif token == "-e":
                interpret_escapes = True
            else:
                payload.append(token)

        text = " ".join(payload)
        if interpret_escapes:
            text = text.encode("utf-8").decode("unicode_escape")
        if append_newline:
            text = f"{text}\n"
        return _truncate_output(text.rstrip("\n") if not append_newline else text.strip())

    return None


def _normalize_command(command: str) -> str:
    """Normalize a small set of cross-platform command aliases."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return command

    if not tokens:
        return command

    if tokens[0] == "python3":
        tokens[0] = sys.executable
        return subprocess.list2cmdline(tokens)

    return command


def _run_subprocess(command: str, workdir: Path, timeout: int, encoding: str | None) -> subprocess.CompletedProcess:
    """Run a subprocess with a normalized command string."""
    kwargs = {
        "args": command,
        "shell": True,
        "cwd": workdir,
        "capture_output": True,
        "timeout": timeout,
    }
    if encoding is not None:
        kwargs.update(
            {
                "text": True,
                "encoding": encoding,
                "errors": "replace",
            }
        )
    return subprocess.run(**kwargs)


def _format_subprocess_output(result: subprocess.CompletedProcess) -> str:
    """Format subprocess output with stable success/error prefixes."""
    out = (result.stdout + result.stderr).strip() if isinstance(result.stdout, str) else ""
    if result.returncode != 0:
        message = out or f"Command failed with exit code {result.returncode}"
        return _truncate_output(f"Error: {message}")
    return _truncate_output(out)


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
    else:
        workdir = Path(workdir)

    command = command.strip()
    if not command:
        return "(no output)"

    if _should_block_direct_execution(command):
        return "Blocked: command requires explicit permission"

    builtin_result = _execute_builtin_command(command, workdir)
    if builtin_result is not None:
        return builtin_result

    # Use system encoding from utils.encoding
    system_encoding = get_system_encoding()
    command = _normalize_command(command)

    # Try with detected/system encoding first
    try:
        r = _run_subprocess(command, workdir, timeout, system_encoding)
        return _format_subprocess_output(r)
    except (LookupError, UnicodeDecodeError):
        # Fallback to UTF-8 if system encoding fails
        try:
            r = _run_subprocess(command, workdir, timeout, "utf-8")
            return _format_subprocess_output(r)
        except Exception:
            # Last resort: try without encoding specification
            try:
                r = _run_subprocess(command, workdir, timeout, None)
                # Use decode_output utility for multiple encoding fallbacks
                output = r.stdout + r.stderr
                out = decode_output(output)
                message = out.strip()
                if r.returncode != 0:
                    return _truncate_output(f"Error: {message or f'Command failed with exit code {r.returncode}'}")
                return _truncate_output(message)
            except Exception as e:
                return f"Error: {e}"
    except subprocess.TimeoutExpired:
        return f"Error: Timeout ({timeout}s)"
    except Exception as e:
        return f"Error: {e}"
