"""Memory management package.

This package provides the memory interface and implementations for agent
long-term memory storage and retrieval.
"""

# Import the abstract interface and base class
# Import concrete implementations
from simple_agent.managers.memory.chroma import ChromaMemory
from simple_agent.managers.memory.factory import MemoryFactory
from simple_agent.managers.memory.in_memory import InMemoryMemory
from simple_agent.managers.memory.interface import (
    BaseMemory,
    IMemory,
)

__all__ = [
    "IMemory",
    "BaseMemory",
    "ChromaMemory",
    "InMemoryMemory",
    "MemoryFactory",
]
