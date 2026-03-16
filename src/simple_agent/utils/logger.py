"""Logging configuration using loguru.

This module provides a centralized logging configuration for the application.
It follows the Single Responsibility Principle (SRP) by only handling
logging setup and configuration.

Loguru features:
- Simple, intuitive API
- Colorized console output
- Automatic rotation and retention
- Exception tracing with locals() display
- Lazy formatting (evaluating expensive operations only if needed)
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def setup_logger(
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    log_rotation: str = "10 MB",
    log_retention: str = "7 days",
    enable_console: bool = True,
    enable_file: bool = True,
) -> None:
    """Configure loguru logger for the application.

    This function removes the default handler and adds custom handlers
    for console and file output with appropriate formatting.

    Args:
        log_dir: Directory for log files (created if doesn't exist)
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_rotation: When to rotate log files (e.g., "10 MB", "1 day")
        log_retention: How long to keep logs (e.g., "7 days", "1 month")
        enable_console: Whether to enable console output
        enable_file: Whether to enable file output

    Example:
        >>> from pathlib import Path
        >>> setup_logger(
        ...     log_dir=Path("logs"),
        ...     log_level="DEBUG",
        ...     log_rotation="5 MB",
        ...     log_retention="3 days"
        ... )
    """
    # Remove default handler
    logger.remove()

    # Console handler with color and formatting
    if enable_console:
        logger.add(
            sys.stderr,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # File handler for all logs with rotation
    if enable_file and log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

        # Main log file - INFO and above
        logger.add(
            log_dir / "simple_agent_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            level="INFO",
            rotation=log_rotation,
            retention=log_retention,
            compression="zip",
            backtrace=True,
            diagnose=True,
            encoding="utf-8",
        )

        # Error log file - ERROR and CRITICAL only
        logger.add(
            log_dir / "errors_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            level="ERROR",
            rotation=log_rotation,
            retention=log_retention,  # Keep errors longer
            compression="zip",
            backtrace=True,
            diagnose=True,
            encoding="utf-8",
        )


def shutdown_logger() -> None:
    """Properly shutdown the logger by completing all pending writes.

    This function ensures all handlers are flushed and closed properly.
    It should be called before application exit or when switching
    logger configurations.

    Example:
        >>> from simple_agent.utils.logger import shutdown_logger
        >>> logger.info("Final message")
        >>> shutdown_logger()
    """
    logger.complete()


def get_logger(name: str = None):
    """Get a logger instance with the specified name.

    This provides a convenient way to get module-specific loggers
    that include the module name in log output.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Logger instance

    Example:
        >>> from simple_agent.utils.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing file: {}", filename)
    """
    if name:
        return logger.bind(name=name)
    return logger


class LoggerMixin:
    """Mixin class to add logging capabilities to any class.

    This provides a convenient way to add logging to classes without
    needing to explicitly create logger instances.

    Example:
        >>> class MyService(LoggerMixin):
        ...     def do_work(self):
        ...         self.logger.info("Starting work")
        ...         try:
        ...             # ... do work ...
        ...             self.logger.success("Work completed")
        ...         except Exception as e:
        ...             self.logger.error("Work failed: {}", str(e))
        ...             raise
    """

    @property
    def logger(self):
        """Get a logger instance for this class.

        The logger is bound with the class name and module for easy identification.
        """
        if not hasattr(self, "_logger"):
            class_name = self.__class__.__name__
            module = self.__class__.__module__
            self._logger = logger.bind(cls=f"{module}.{class_name}")
        return self._logger


# Convenience exports
__all__ = [
    "logger",
    "setup_logger",
    "shutdown_logger",
    "get_logger",
    "LoggerMixin",
]
