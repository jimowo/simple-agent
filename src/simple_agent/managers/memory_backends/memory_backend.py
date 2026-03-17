"""In-memory backend for memory system.

This module provides the in-memory backend that stores and
retrieves memory entries using Python dictionaries.
"""

import json
import math
from typing import Dict, List, Optional

from loguru import logger

from simple_agent.managers.base import BaseManager
from simple_agent.models.config import Settings
from simple_agent.models.memory import MemoryEntry


class InMemoryBackend(BaseManager):
    """In-memory backend for memory storage.

    This backend stores all memories in memory and persists them to JSON files.
    It's suitable for development and small-scale deployments.

    Attributes:
        settings: Application settings
        memory_dir: Directory for memory persistence
        _entries: In-memory entry cache (entry_id -> MemoryEntry)
        encoder: Optional encoder for generating embeddings
    """

    def __init__(self, settings: Settings, encoder: Optional[object] = None):
        """Initialize the in-memory backend.

        Args:
            settings: Application settings
            encoder: Optional encoder for generating embeddings
        """
        super().__init__(settings)
        self.memory_dir = self._ensure_dir(
            self.settings.workdir / ".simple" / "memory"
        )
        self._entries: Dict[str, MemoryEntry] = {}
        self.encoder = encoder

        # Load existing memories
        self._load_memories()

        logger.info(f"[InMemoryBackend] Initialized with dir={self.memory_dir}")

    def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry.

        Args:
            entry: MemoryEntry to store

        Returns:
            True if successful
        """
        try:
            # Generate embedding if not present
            if not entry.metadata.embedding and self.encoder:
                entry.metadata.embedding = self.encoder.encode(entry.content)

            # Store in memory
            self._entries[entry.metadata.entry_id] = entry

            # Persist to disk
            self._persist_entry(entry)

            logger.debug(
                f"[InMemoryBackend] Stored entry={entry.metadata.entry_id[:8]}..., "
                f"type={entry.metadata.entry_type}"
            )
            return True
        except Exception as e:
            logger.error(f"[InMemoryBackend] Failed to store entry: {e}")
            return False

    def load(self, entry_id: str) -> Optional[MemoryEntry]:
        """Load a memory entry by ID.

        Args:
            entry_id: Entry ID to load

        Returns:
            MemoryEntry if found, None otherwise
        """
        return self._entries.get(entry_id)

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[MemoryEntry]:
        """Search for similar entries by vector.

        Args:
            query_vector: Query embedding vector
            limit: Maximum results
            threshold: Minimum similarity threshold

        Returns:
            List of similar MemoryEntry instances
        """
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
            f"[InMemoryBackend] Search returned {len(results)} entries "
            f"(threshold={threshold})"
        )
        return results

    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: Entry ID to delete

        Returns:
            True if deleted, False if not found
        """
        if entry_id not in self._entries:
            return False

        del self._entries[entry_id]

        # Delete from disk
        entry_file = self.memory_dir / f"{entry_id}.json"
        if entry_file.exists():
            entry_file.unlink()

        logger.debug(f"[InMemoryBackend] Deleted entry={entry_id[:8]}...")
        return True

    def _load_memories(self) -> None:
        """Load memories from disk."""
        if not self.memory_dir.exists():
            return

        for entry_file in self.memory_dir.glob("*.json"):
            try:
                data = json.loads(entry_file.read_text(encoding="utf-8"))
                entry = MemoryEntry(**data)
                self._entries[entry.metadata.entry_id] = entry
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"[InMemoryBackend] Failed to load {entry_file}: {e}")
                continue

        logger.info(f"[InMemoryBackend] Loaded {len(self._entries)} entries from disk")

    def _persist_entry(self, entry: MemoryEntry) -> None:
        """Persist an entry to disk.

        Args:
            entry: Entry to persist
        """
        entry_file = self.memory_dir / f"{entry.metadata.entry_id}.json"
        entry_file.write_text(
            entry.model_dump_json(exclude_none=True, indent=2),
            encoding="utf-8"
        )

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score between 0 and 1
        """
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)


__all__ = ["InMemoryBackend"]
