"""File operation tools."""

from simple_agent.utils.constants import MAX_FILE_EDIT, MAX_FILE_READ, MAX_FILE_WRITE
from simple_agent.utils.error_handling import handle_tool_errors
from simple_agent.utils.safety import safe_path


@handle_tool_errors
def read_file(path: str, limit: int = None) -> str:
    """
    Read file contents with optional line limit.

    Args:
        path: Path to file (relative to workspace)
        limit: Maximum number of lines to read

    Returns:
        File contents as string
    """
    # Try UTF-8 encoding first
    try:
        lines = safe_path(path).read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        # Fallback to system encoding
        lines = safe_path(path).read_text().splitlines()

    if limit and limit < len(lines):
        lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
    return "\n".join(lines)[:MAX_FILE_READ]


@handle_tool_errors
def write_file(path: str, content: str) -> str:
    """
    Write content to file.

    Args:
        path: Path to file (relative to workspace)
        content: Content to write

    Returns:
        Success message

    Raises:
        ValueError: If content exceeds maximum write size
    """
    # Validate content size before writing
    if len(content) > MAX_FILE_WRITE:
        raise ValueError(
            f"Content exceeds maximum write size of {MAX_FILE_WRITE} characters "
            f"(got {len(content)} characters)"
        )

    fp = safe_path(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    # Explicitly use UTF-8 encoding to support Chinese and other Unicode characters
    fp.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {path}"


@handle_tool_errors
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """
    Replace exact text in file.

    Args:
        path: Path to file (relative to workspace)
        old_text: Text to replace
        new_text: Replacement text

    Returns:
        Success message

    Raises:
        ValueError: If new_text exceeds maximum edit size
    """
    # Validate new_text size before editing
    if len(new_text) > MAX_FILE_EDIT:
        raise ValueError(
            f"New text exceeds maximum edit size of {MAX_FILE_EDIT} characters "
            f"(got {len(new_text)} characters)"
        )

    fp = safe_path(path)
    # Read with UTF-8 encoding
    c = fp.read_text(encoding="utf-8")
    if old_text not in c:
        return f"Error: Text not found in {path}"
    # Write with UTF-8 encoding
    fp.write_text(c.replace(old_text, new_text, 1), encoding="utf-8")
    return f"Edited {path}"
