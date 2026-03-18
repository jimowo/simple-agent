"""Backward-compatible Chroma memory backend alias."""

from simple_agent.managers.memory.chroma import ChromaMemory


class ChromaMemoryBackend(ChromaMemory):
    """Deprecated alias for the unified Chroma memory implementation."""


__all__ = ["ChromaMemoryBackend"]
