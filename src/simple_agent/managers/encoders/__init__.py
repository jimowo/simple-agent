"""Memory encoder factory and implementations.

This module provides the encoder factory for creating memory encoders
that convert text to vector embeddings for semantic search.
"""

from typing import Dict, Optional, type

from simple_agent.models.config import Settings


class MemoryEncoderFactory:
    """Factory for creating memory encoder instances.

    This class follows the Open/Closed Principle (OCP) by allowing
    new encoders to be registered at runtime without modifying
    the source code.
    """

    _encoders: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, encoder_class: type) -> None:
        """Register an encoder class.

        Args:
            name: Encoder name identifier
            encoder_class: Encoder class to register

        Example:
            MemoryEncoderFactory.register("custom", CustomEncoder)
        """
        cls._encoders[name] = encoder_class

    @classmethod
    def create(cls, settings: Settings) -> Optional["MemoryEncoder"]:
        """Create an encoder instance based on settings.

        Args:
            settings: Application settings

        Returns:
            Encoder instance or None if memory is disabled
        """
        if not settings.memory_enabled:
            return None

        encoder_name = settings.memory_encoder

        # Built-in encoders
        if encoder_name == "openai":
            from simple_agent.managers.encoders.openai import OpenAIEmbeddingEncoder
            return OpenAIEmbeddingEncoder(
                api_key=settings.memory_openai_api_key or settings.openai_api_key,
                base_url=settings.memory_openai_base_url,
                model=settings.memory_openai_model
            )

        # Registered encoders
        encoder_class = cls._encoders.get(encoder_name)
        if encoder_class:
            return encoder_class(settings)

        # Unknown encoder
        raise ValueError(f"Unknown memory encoder: {encoder_name}")


# Type alias for the encoder interface
MemoryEncoder = object


__all__ = ["MemoryEncoderFactory", "MemoryEncoder"]
