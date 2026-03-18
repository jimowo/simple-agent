"""Project manager for multi-project support.

This module provides the ProjectManager class that handles project
metadata and session organization, following Claude Code's management pattern.
"""

import json
from pathlib import Path
from typing import List, Optional

from simple_agent.managers.base import BaseManager
from simple_agent.models.config import Settings
from simple_agent.models.projects import ProjectMetadata
from simple_agent.utils.path_utils import (
    get_project_dir,
    get_project_metadata_file,
    path_to_project_id,
)


class ProjectManager(BaseManager):
    """Manager for project metadata and organization.

    This class handles:
    - Creating and loading project metadata
    - Tracking project access times
    - Listing all projects
    - Managing the current active project

    Attributes:
        settings: Application settings
        projects_root: Root directory for project data
        _current_project: Currently active project
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the project manager.

        Args:
            settings: Optional settings instance
        """
        super().__init__(settings)
        self.projects_root = self._ensure_dir(self.settings.projects_root)
        self._current_project: Optional[ProjectMetadata] = None

    def get_or_create_project(self, workdir: Path) -> ProjectMetadata:
        """Get an existing project or create a new one.

        This method creates the project directory structure if it doesn't exist,
        including the project.json metadata file.

        Args:
            workdir: Working directory path for the project

        Returns:
            ProjectMetadata instance for the project
        """
        project_id = path_to_project_id(workdir)
        project_dir = self._ensure_dir(get_project_dir(self.projects_root, project_id))
        metadata_file = get_project_metadata_file(self.projects_root, project_id)

        if metadata_file.exists():
            # Load existing project
            try:
                data = json.loads(metadata_file.read_text(encoding="utf-8"))
                project = ProjectMetadata(**data)
                # Update last accessed time
                project.last_accessed = project.last_accessed.now()
            except (json.JSONDecodeError, ValueError):
                # If metadata is corrupted, create new project
                project = ProjectMetadata(
                    project_id=project_id,
                    original_path=str(workdir)
                )
        else:
            # Create new project
            project = ProjectMetadata(
                project_id=project_id,
                original_path=str(workdir)
            )

        # Save metadata (updates last_accessed for existing projects)
        self._save_metadata(project)

        self._current_project = project
        return project

    def get_project(self, project_id: str) -> Optional[ProjectMetadata]:
        """Get a project by ID.

        Args:
            project_id: Project ID to retrieve

        Returns:
            ProjectMetadata if found, None otherwise
        """
        metadata_file = get_project_metadata_file(self.projects_root, project_id)

        if not metadata_file.exists():
            return None

        try:
            data = json.loads(metadata_file.read_text(encoding="utf-8"))
            return ProjectMetadata(**data)
        except (json.JSONDecodeError, ValueError):
            return None

    def list_projects(self, limit: Optional[int] = None) -> List[ProjectMetadata]:
        """List all projects.

        Projects are sorted by last accessed time (most recent first).

        Args:
            limit: Optional maximum number of projects to return

        Returns:
            List of ProjectMetadata instances
        """
        projects = []

        for metadata_file in self.projects_root.glob("*/project.json"):
            try:
                data = json.loads(metadata_file.read_text(encoding="utf-8"))
                projects.append(ProjectMetadata(**data))
            except (json.JSONDecodeError, ValueError):
                # Skip corrupted metadata files
                continue

        # Sort by last_accessed descending
        projects.sort(key=lambda p: p.last_accessed, reverse=True)

        if limit:
            return projects[:limit]

        return projects

    def get_current_project(self) -> Optional[ProjectMetadata]:
        """Get the currently active project.

        Returns:
            Current ProjectMetadata or None if no project is active
        """
        return self._current_project

    def set_current_project(self, project: ProjectMetadata) -> None:
        """Set the currently active project.

        Args:
            project: Project to set as current
        """
        self._current_project = project

    def update_project_metadata(
        self,
        project_id: str,
        **kwargs
    ) -> Optional[ProjectMetadata]:
        """Update project metadata fields.

        Args:
            project_id: Project ID to update
            **kwargs: Fields to update (e.g., session_count=5)

        Returns:
            Updated ProjectMetadata or None if project not found
        """
        project = self.get_project(project_id)
        if not project:
            return None

        # Update specified fields
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)

        # Save updated metadata
        self._save_metadata(project)

        # Update current project if it's the same
        if self._current_project and self._current_project.project_id == project_id:
            self._current_project = project

        return project

    def _save_metadata(self, project: ProjectMetadata) -> None:
        """Save project metadata to file.

        Args:
            project: Project to save
        """
        project_dir = get_project_dir(self.projects_root, project.project_id)
        metadata_file = get_project_metadata_file(self.projects_root, project.project_id)

        metadata_file.write_text(
            project.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8"
        )
