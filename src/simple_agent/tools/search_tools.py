"""Search tools for file and content searching.

This module provides glob and grep tools similar to Claude Code's capabilities.
"""

import re
from pathlib import Path

from simple_agent.utils.constants import MAX_SEARCH_RESULTS
from simple_agent.utils.error_handling import handle_tool_errors
from simple_agent.utils.safety import safe_path


@handle_tool_errors
def glob_files(pattern: str, path: str = None) -> str:
    """
    Find files by pattern matching.

    Args:
        pattern: Glob pattern (e.g., "**/*.py", "src/**/*.txt")
        path: Base path to search (uses workdir if None)

    Returns:
        List of matching file paths
    """
    if path is None:
        from simple_agent.models.config import Settings

        search_path = Settings().workdir
    else:
        search_path = safe_path(path)

    # Convert to Path object
    search_path = Path(search_path)

    # Use glob to find matching files
    matches = list(search_path.glob(pattern))

    # Filter to files only (not directories)
    files = [str(f.relative_to(search_path)) for f in matches if f.is_file()]

    # Limit results
    if len(files) > MAX_SEARCH_RESULTS:
        files = files[:MAX_SEARCH_RESULTS]
        return f"Found {len(matches)} matches (showing first {MAX_SEARCH_RESULTS}):\n" + "\n".join(files)

    if not files:
        return f"No files found matching pattern: {pattern}"

    return "\n".join(files)


@handle_tool_errors
def grep_content(
    pattern: str,
    path: str = None,
    file_pattern: str = None,
    ignore_case: bool = False,
    max_results: int = MAX_SEARCH_RESULTS,
) -> str:
    """
    Search for patterns in file contents.

    Args:
        pattern: Regular expression pattern to search for
        path: Base path to search (uses workdir if None)
        file_pattern: Glob pattern to filter files (e.g., "*.py")
        ignore_case: Whether to ignore case when matching
        max_results: Maximum number of results to return

    Returns:
        Search results with file paths and matching lines
    """
    if path is None:
        from simple_agent.models.config import Settings

        search_path = Settings().workdir
    else:
        search_path = safe_path(path)

    search_path = Path(search_path)

    # Compile the regex pattern
    flags = re.IGNORECASE if ignore_case else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"Invalid regex pattern: {e}"

    results = []
    total_matches = 0

    # Determine which files to search
    if file_pattern:
        files = list(search_path.glob(file_pattern))
        files = [f for f in files if f.is_file()]
    else:
        # Search all files recursively
        files = [f for f in search_path.rglob("*") if f.is_file()]

    # Search each file
    for file_path in files:
        if len(results) >= max_results:
            break

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()

            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    rel_path = str(file_path.relative_to(search_path))
                    # Truncate long lines
                    display_line = line[:200]
                    if len(line) > 200:
                        display_line += "..."
                    results.append(f"{rel_path}:{line_num}: {display_line}")
                    total_matches += 1

                    if len(results) >= max_results:
                        break

        except (UnicodeDecodeError, PermissionError, OSError):
            # Skip files that can't be read
            continue

    if not results:
        return f"No matches found for pattern: {pattern}"

    output = "\n".join(results)
    if total_matches > max_results:
        output = f"Found {total_matches} matches (showing first {max_results}):\n{output}"

    return output
