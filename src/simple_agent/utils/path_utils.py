"""Path utilities for project ID conversion.

This module provides functions to convert between file system paths
and project IDs, following Claude Code's naming convention.
"""

import re
from pathlib import Path


def path_to_project_id(path: Path) -> str:
    """Convert a file system path to a project ID.

    This function follows Claude Code's naming convention:
    - Converts to lowercase
    - Replaces path separators with --
    - Removes Windows drive colon

    Examples:
        E:/codehub/simple-agent -> e--codehub-simple-agent
        C:/Users/jimowo/Documents -> c--Users-jimowo-Documents
        /home/user/project -> --home-user-project

    Args:
        path: The file system path to convert

    Returns:
        A project ID string suitable for use as a directory name
    """
    # Convert to string and lowercase
    path_str = str(path).lower()

    # Replace path separators with --
    # Handle both Windows (\) and Unix (/) separators
    path_str = path_str.replace("\\", "--").replace("/", "--")

    # Remove Windows drive colon (e: -> e)
    path_str = path_str.replace(":", "")

    # Remove leading -- if present (from absolute paths)
    if path_str.startswith("--"):
        path_str = path_str[2:]

    # Clean up any empty segments from trailing separators
    path_str = "--".join(segment for segment in path_str.split("--") if segment)

    return path_str


def normalize_project_path(project_id: str) -> str:
    """Normalize a project ID by removing redundant separators.

    Args:
        project_id: The project ID to normalize

    Returns:
        A normalized project ID string
    """
    # Split by -- and filter out empty segments
    segments = [seg for seg in project_id.split("--") if seg]

    # Rejoin with --
    return "--".join(segments)


def is_valid_project_id(project_id: str) -> bool:
    """Check if a project ID is valid.

    A valid project ID:
    - Is not empty
    - Contains only alphanumeric characters and hyphens
    - Does not start or end with --

    Args:
        project_id: The project ID to validate

    Returns:
        True if the project ID is valid, False otherwise
    """
    if not project_id:
        return False

    # Check for valid characters (alphanumeric, hyphen, underscore)
    if not re.match(r"^[a-zA-Z0-9_\-]+$", project_id.replace("--", "-")):
        return False

    # Check for leading/trailing --
    if project_id.startswith("--") or project_id.endswith("--"):
        return False

    return True
