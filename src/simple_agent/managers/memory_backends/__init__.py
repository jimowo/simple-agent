"""Memory backend factory and implementations.

This module provides the backend factory for creating memory storage
backends that persist and retrieve memory entries.

.. deprecated::
    This module is deprecated in favor of the new memory architecture.
    Use simple_agent.managers.memory instead.
"""

import warnings
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from typing import Any

from simple_agent.models.config import Settings


class MemoryBackendFactory:
    """Factory for creating memory backend instances.

    .. deprecated::
        Use MemoryFactory from simple_agent.managers.memory instead.
    """

    _backends: dict = {}

    def __init__(self) -> None:
        warnings.warn(
            "MemoryBackendFactory is deprecated. Use MemoryFactory from simple_agent.managers.memory instead.",
            DeprecationWarning,
            stacklevel=2
        )

    @classmethod
    def register(cls, name: str, backend_class: type) -> None:
        """Register a backend class."""
        warnings.warn(
            "MemoryBackendFactory is deprecated. Use MemoryFactory from simple_agent.managers.memory instead.",
            DeprecationWarning,
            stacklevel=2
        )
        cls._backends[name] = backend_class

    @classmethod
    def create(cls, settings: Settings, encoder: Optional[Any] = None):
        """Create a backend instance based on settings."""
        warnings.warn(
            "MemoryBackendFactory is deprecated. Use MemoryFactory from simple_agent.managers.memory instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # Delegate to new MemoryFactory
        from simple_agent.managers.memory import MemoryFactory
        return MemoryFactory.create(settings, encoder)


# Type alias for the backend interface
MemoryBackend = object


__all__ = ["MemoryBackendFactory", "MemoryBackend"]
