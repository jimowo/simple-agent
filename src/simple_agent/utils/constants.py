"""Constants for the simple-agent application.

This module defines constants used across the application to avoid
magic numbers and improve maintainability.
"""


class OutputLimits:
    """Output size limits for tools and commands."""

    MAX_BASH_OUTPUT = 50000  # Maximum characters for bash command output
    MAX_FILE_READ = 50000  # Maximum characters for file read output
    MAX_TOOL_OUTPUT = 50000  # Maximum characters for tool output
    MAX_SEARCH_RESULTS = 100  # Maximum number of search results to return
    MAX_WEB_CONTENT_LENGTH = 50000  # Maximum characters for web content


class LoopIterations:
    """Iteration limits for loops."""

    MAX_WORK_ITERATIONS = 50  # Maximum iterations in work phase
    MAX_SUBAGENT_ITERATIONS = 30  # Maximum iterations for subagent


class Encoding:
    """Encoding related constants."""

    DEFAULT_ENCODING = "utf-8"
    ENCODING_FALLBACK_ORDER = ["utf-8", "gbk", "cp936", "cp1252", "latin1", "ascii"]


# Export constants for easier access
MAX_BASH_OUTPUT = OutputLimits.MAX_BASH_OUTPUT
MAX_FILE_READ = OutputLimits.MAX_FILE_READ
MAX_TOOL_OUTPUT = OutputLimits.MAX_TOOL_OUTPUT
MAX_SEARCH_RESULTS = OutputLimits.MAX_SEARCH_RESULTS
MAX_WEB_CONTENT_LENGTH = OutputLimits.MAX_WEB_CONTENT_LENGTH
