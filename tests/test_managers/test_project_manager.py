"""Tests for ProjectManager exception handling."""

import pytest

from simple_agent.exceptions import ProjectNotFoundError, ProjectValidationError
from simple_agent.managers.project import ProjectManager


class TestProjectManagerExceptions:
    """Test standardized project exception behavior."""

    def test_get_project_or_raise_raises_not_found(self, mock_settings):
        """Missing projects should raise ProjectNotFoundError."""
        manager = ProjectManager(mock_settings)

        with pytest.raises(ProjectNotFoundError):
            manager.get_project_or_raise("missing-project")

    def test_update_project_metadata_raises_for_unknown_field(self, mock_settings):
        """Unknown metadata fields should raise ProjectValidationError."""
        manager = ProjectManager(mock_settings)
        project = manager.get_or_create_project(mock_settings.workdir)

        with pytest.raises(ProjectValidationError, match="Unknown project metadata field"):
            manager.update_project_metadata(project.project_id, does_not_exist=True)

    def test_update_project_metadata_raises_for_missing_project(self, mock_settings):
        """Updating a missing project should raise ProjectNotFoundError."""
        manager = ProjectManager(mock_settings)

        with pytest.raises(ProjectNotFoundError):
            manager.update_project_metadata("missing-project", session_count=2)
