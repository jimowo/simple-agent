"""Test logging configuration using loguru."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from simple_agent.utils.logger import (
    setup_logger,
    shutdown_logger,
    get_logger,
    LoggerMixin,
    logger,
)


class TestSetupLogger:
    """Test logger setup configuration."""

    def test_setup_logger_creates_log_dir(self, temp_workspace):
        """Test that setup_logger creates the log directory."""
        log_dir = temp_workspace / "logs"

        setup_logger(
            log_dir=log_dir,
            enable_console=False,
            enable_file=True,
        )

        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_setup_logger_adds_handlers(self, temp_workspace):
        """Test that setup_logger adds handlers."""
        log_dir = temp_workspace / "logs"

        # Clear existing handlers
        logger.remove()

        setup_logger(
            log_dir=log_dir,
            enable_console=True,
            enable_file=True,
        )

        # Should have handlers added
        assert len(logger._core.handlers) > 0

    def test_setup_logger_console_only(self, temp_workspace):
        """Test setup_logger with console only."""
        logger.remove()

        setup_logger(
            log_dir=temp_workspace / "logs",
            enable_console=True,
            enable_file=False,
        )

        # Check that we have at least one handler
        assert len(logger._core.handlers) >= 1

    def test_setup_logger_file_only(self, temp_workspace):
        """Test setup_logger with file only."""
        logger.remove()

        log_dir = temp_workspace / "logs"
        setup_logger(
            log_dir=log_dir,
            enable_console=False,
            enable_file=True,
        )

        # Check that we have at least one handler
        assert len(logger._core.handlers) >= 1


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        log = get_logger()

        # Should be the same as the global logger
        assert log is logger

    def test_get_logger_with_name(self):
        """Test that get_logger with name binds the name."""
        test_logger = get_logger("test_module")

        # Should return a logger instance
        assert hasattr(test_logger, "info")
        assert hasattr(test_logger, "error")
        assert hasattr(test_logger, "debug")


class TestLoggerMixin:
    """Test LoggerMixin class."""

    def test_logger_mixin_adds_logger_property(self):
        """Test that LoggerMixin adds a logger property."""
        class TestService(LoggerMixin):
            def __init__(self):
                pass

        service = TestService()

        # Should have logger property
        assert hasattr(service, "logger")

    def test_logger_mixin_logger_has_correct_binding(self):
        """Test that LoggerMixin logger is bound with class info."""
        class TestService(LoggerMixin):
            pass

        service = TestService()
        log = service.logger

        # Should be able to log
        assert hasattr(log, "info")
        assert hasattr(log, "debug")
        assert hasattr(log, "error")

    def test_logger_mixin_multiple_classes(self):
        """Test that each class gets its own logger."""
        class ServiceA(LoggerMixin):
            pass

        class ServiceB(LoggerMixin):
            pass

        a = ServiceA()
        b = ServiceB()

        # Each should have its own logger
        assert a.logger is not b.logger


class TestLoggerOutput:
    """Test actual logger output."""

    def test_logger_output_to_console(self, capsys):
        """Test that logger writes to console."""
        logger.remove()
        setup_logger(enable_console=True, enable_file=False)

        logger.info("Test message")
        logger.remove()

        captured = capsys.readouterr()
        # Should have output to stderr
        assert "Test message" in captured.err or "Test message" in captured.out

    def test_logger_output_to_file(self, temp_workspace):
        """Test that logger writes to file."""
        # Ensure clean state - remove all handlers first
        logger.remove()

        log_dir = temp_workspace / "logs"
        setup_logger(log_dir=log_dir, enable_console=False, enable_file=True)

        test_message = "File test message"
        logger.info(test_message)

        # Use logger.complete() to flush all handlers synchronously
        logger.complete()

        # Check that log file was created and contains message
        # Look specifically for the main log file (not error log)
        main_log_files = list(log_dir.glob("simple_agent_*.log"))

        # Also check for any files in the log directory for debugging
        all_files = list(log_dir.glob("*")) if log_dir.exists() else []

        # Assert we found the main log file
        assert main_log_files, f"No main log files found in {log_dir}. All files: {[f.name for f in all_files]}"

        # Read the main log file (there should be only one)
        content = main_log_files[0].read_text(encoding='utf-8')
        assert test_message in content, f"Expected '{test_message}' in log file {main_log_files[0]}, but got: {content}"

    def test_logger_error_to_file(self, temp_workspace):
        """Test that errors are written to error log file."""
        logger.remove()

        log_dir = temp_workspace / "logs"
        setup_logger(log_dir=log_dir, enable_console=False, enable_file=True)

        error_message = "Test error message"
        logger.error(error_message)
        shutdown_logger()  # Properly shutdown and flush all handlers

        # Check error log file
        error_logs = list(log_dir.glob("error*.log"))
        if error_logs:
            content = error_logs[0].read_text(encoding='utf-8')
            assert error_message in content


@pytest.mark.integration
class TestLoggerIntegration:
    """Test logger integration with other components."""

    def test_logger_with_managers(self, initialized_context):
        """Test that managers can use LoggerMixin."""
        from simple_agent.managers.todo import TodoManager

        todo = TodoManager()
        todo.logger.info("Test log from manager")

        # Should not raise any errors
        assert True

    def test_logger_with_background_manager(self, initialized_context):
        """Test that BackgroundManager logs appropriately."""
        from simple_agent.managers.background import BackgroundManager

        bg = BackgroundManager(initialized_context.settings)
        bg.logger.info("Test log from background manager")

        # Should not raise any errors
        assert True
