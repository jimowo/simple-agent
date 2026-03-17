"""Memory factory for creating memory instances.

This module provides the MemoryFactory class for creating different
types of memory implementations based on configuration.
"""

from typing import TYPE_CHECKING, Dict, Optional

from loguru import logger

if TYPE_CHECKING:
    from simple_agent.managers.memory.interface import IMemory

from simple_agent.models.config import Settings


class MemoryFactory:
    """Factory for creating memory instances.

    This class follows the Open/Closed Principle (OCP) by allowing
    new memory types to be registered at runtime without modifying
    the source code.

    Usage:
        # Create memory from settings
        memory = MemoryFactory.create(settings)

        # Register custom memory type
        MemoryFactory.register("custom", CustomMemory)
    """

    # Built-in memory types
    _memory_types: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, memory_class: type) -> None:
        """Register a memory class.

        Args:
            name: Memory type name identifier
            memory_class: Memory class to register (must implement IMemory)

        Raises:
            TypeError: If memory_class doesn't implement IMemory

        Example:
            MemoryFactory.register("custom", CustomMemory)
        """
        # Import here to avoid circular import
        from simple_agent.managers.memory.interface import IMemory

        if not issubclass(memory_class, IMemory):
            raise TypeError(
                f"Memory class must implement IMemory interface. "
                f"Got {type(memory_class)}"
            )

        cls._memory_types[name] = memory_class
        logger.logger.info(f"[MemoryFactory] Registered memory type: {name}")

    @classmethod
    def create(cls, settings: Settings, encoder: Optional[object] = None) -> Optional["IMemory"]:
        """Create a memory instance based on settings.

        Args:
            settings: Application settings
            encoder: Optional encoder for embeddings

        Returns:
            Memory instance or None if memory is disabled

        Raises:
            ValueError: If memory type is unknown
        """
        if not settings.memory_enabled:
            logger.logger.info("[MemoryFactory] Memory is disabled")
            return None

        memory_type = settings.memory_backend

        # Built-in memory types
        if memory_type == "chroma":
            from simple_agent.managers.memory.chroma import ChromaMemory
            return ChromaMemory(settings, encoder)
        elif memory_type == "memory" or memory_type == "in_memory":
            from simple_agent.managers.memory.in_memory import InMemoryMemory
            return InMemoryMemory(settings, encoder)

        # Registered memory types
        memory_class = cls._memory_types.get(memory_type)
        if memory_class:
            return memory_class(settings, encoder)

        # Unknown memory type
        available = list(cls._memory_types.keys()) + ["chroma", "memory"]
        raise ValueError(
            f"Unknown memory type: {memory_type}. "
            f"Available types: {', '.join(available)}"
        )

    @classmethod
    def list_types(cls) -> Dict[str, str]:
        """List all available memory types.

        Returns:
            Dictionary mapping memory type names to descriptions
        """
        types = {
            "chroma": "ChromaDB vector database",
            "memory": "In-memory with JSON persistence",
        }

        # Add registered types
        for name, cls_type in cls._memory_types.items():
            types[name] = getattr(cls_type, "description", "Custom memory")

        return types

    @classmethod
    def get_info(cls, memory_type: str) -> Dict[str, str]:
        """Get information about a specific memory type.

        Args:
            memory_type: Memory type name

        Returns:
            Dictionary with type information

        Raises:
            ValueError: If memory type is unknown
        """
        types = cls.list_types()
        if memory_type not in types:
            raise ValueError(f"Unknown memory type: {memory_type}")

        return {
            "type": memory_type,
            "description": types[memory_type],
        }


__all__ = ["MemoryFactory"]
