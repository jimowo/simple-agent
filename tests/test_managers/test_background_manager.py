"""Tests for BackgroundManager exception handling."""

import pytest

from simple_agent.exceptions import BackgroundTaskError
from simple_agent.managers.background import BackgroundManager


class TestBackgroundManagerExceptions:
    """Test standardized background task exceptions."""

    def test_empty_command_raises_background_task_error(self, mock_settings):
        """Empty commands should be rejected."""
        manager = BackgroundManager(mock_settings)

        with pytest.raises(BackgroundTaskError):
            manager.run("   ")

    def test_check_unknown_task_raises_background_task_error(self, mock_settings):
        """Unknown task IDs should raise BackgroundTaskError."""
        manager = BackgroundManager(mock_settings)

        with pytest.raises(BackgroundTaskError):
            manager.check("missing-task")
