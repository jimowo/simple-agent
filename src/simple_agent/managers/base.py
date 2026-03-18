"""Base manager class with common initialization logic.

This module provides a base class for managers that handles the common
pattern of Settings initialization and directory creation.
"""

from pathlib import Path
from typing import Optional

from simple_agent.exceptions import ProjectNotFoundError, ProjectValidationError
from simple_agent.models.config import Settings


class BaseManager:
    """Base class for manager classes.

    This class provides common initialization logic for managers that:
    - Accept optional Settings parameter
    - Create and ensure directories exist
    - Access settings properties

    Attributes:
        settings: Application settings instance
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the base manager.

        Args:
            settings: Optional Settings instance (creates default if None)
        """
        self.settings = settings or Settings()

    def _ensure_dir(self, directory: Path) -> Path:
        """Ensure a directory exists, creating it if necessary.

        Args:
            directory: Path to directory

        Returns:
            The directory path (for convenience)
        """
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _raise_project_not_found(self, project_id: str) -> None:
        """Raise the standardized project-not-found exception."""
        raise ProjectNotFoundError(project_id)

    def _raise_project_validation_error(
        self, reason: str, project_id: Optional[str] = None
    ) -> None:
        """Raise the standardized project-validation exception."""
        raise ProjectValidationError(reason, project_id=project_id)
