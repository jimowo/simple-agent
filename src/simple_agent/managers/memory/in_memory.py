"""In-memory memory implementation.

This module provides the in-memory memory implementation that stores
and retrieves memory entries using Python dictionaries.
"""

import json
import math
from typing import Dict, List, Optional

from loguru import logger

from simple_agent.managers.memory.interface import BaseMemory
from simple_agent.models.config import Settings
from simple_agent.models.memory import MemoryEntry


class InMemoryMemory(BaseMemory):
    """In-memory memory implementation.

    This implementation stores all memories in memory and persists them to JSON files.
    It's suitable for development and small-scale deployments.

    Attributes:
        memory_dir: Directory for memory persistence
        _entries: In-memory entry cache (entry_id -> MemoryEntry)
    """

    memory_type = "memory"
    description = "In-memory with JSON file persistence"

    def __init__(self, settings: Optional[Settings] = None, encoder: Optional[object] = None):
        """Initialize the in-memory backend.

        Args:
            settings: Application settings
            encoder: Optional encoder for generating embeddings
        """
        super().__init__(settings, encoder)

        self.memory_dir = self.settings.workdir / ".simple" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self._entries: Dict[str, MemoryEntry] = {}

        # Load existing memories
        self._load_memories()

        logger.info(f"[InMemoryMemory] Initialized with dir={self.memory_dir}")

    # ========================================================================
    # Abstract Method Implementations
    # ========================================================================

    def _store_entry(self, entry: MemoryEntry) -> bool:
        """Store a memory entry in memory and persist to disk."""
        try:
            # Store in memory
            self._entries[entry.metadata.entry_id] = entry

            # Persist to disk
            self._persist_entry(entry)

            logger.debug(
                f"[InMemoryMemory] Stored entry={entry.metadata.entry_id[:8]}..., "
                f"type={entry.metadata.entry_type}"
            )
            return True
        except Exception as e:
            logger.error(f"[InMemoryMemory] Failed to store entry: {e}")
            return False

    def _load_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Load a memory entry by ID from memory cache."""
        return self._entries.get(entry_id)

    def _search_entries(
        self,
        query_vector: List[float],
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[MemoryEntry]:
        """Search for similar entries by vector using cosine similarity."""
        scored_entries = []

        for entry in self._entries.values():
            if entry.metadata.embedding:
                similarity = self._cosine_similarity(query_vector, entry.metadata.embedding)
                if similarity >= threshold:
                    scored_entries.append((entry, similarity))

        # Sort by similarity
        scored_entries.sort(key=lambda x: x[1], reverse=True)

        # Return top results
        results = [entry for entry, _ in scored_entries[:limit]]

        logger.debug(
            f"[InMemoryMemory] Search returned {len(results)} entries "
            f"(threshold={threshold})"
        )
        return results

    def _delete_entry(self, entry_id: str) -> bool:
        """Delete a memory entry from memory and disk."""
        if entry_id not in self._entries:
            return False

        del self._entries[entry_id]

        # Delete from disk
        entry_file = self.memory_dir / f"{entry_id}.json"
        if entry_file.exists():
            entry_file.unlink()

        logger.debug(f"[InMemoryMemory] Deleted entry={entry_id[:8]}...")
        return True

    def _list_all_entries(self) -> List[MemoryEntry]:
        """List all memory entries from memory cache."""
        return list(self._entries.values())

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _load_memories(self) -> None:
        """Load memories from disk on initialization."""
        if not self.memory_dir.exists():
            return

        for entry_file in self.memory_dir.glob("*.json"):
            try:
                data = json.loads(entry_file.read_text(encoding="utf-8"))
                entry = MemoryEntry(**data)
                self._entries[entry.metadata.entry_id] = entry
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"[InMemoryMemory] Failed to load {entry_file}: {e}")
                continue

        logger.info(f"[InMemoryMemory] Loaded {len(self._entries)} entries from disk")

    def _persist_entry(self, entry: MemoryEntry) -> None:
        """Persist an entry to disk."""
        entry_file = self.memory_dir / f"{entry.metadata.entry_id}.json"
        entry_file.write_text(
            entry.model_dump_json(exclude_none=True, indent=2),
            encoding="utf-8"
        )

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)


__all__ = ["InMemoryMemory"]
