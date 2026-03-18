"""Tests for TaskManager exception handling."""

import pytest

from simple_agent.exceptions import TaskNotFoundError
from simple_agent.managers.task import TaskManager


class TestTaskManagerExceptions:
    """Test standardized task exception behavior."""

    def test_get_missing_task_raises_task_not_found(self, mock_settings):
        """Missing tasks should raise TaskNotFoundError."""
        manager = TaskManager(mock_settings)

        with pytest.raises(TaskNotFoundError):
            manager.get(999)
