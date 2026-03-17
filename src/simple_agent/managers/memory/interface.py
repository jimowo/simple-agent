"""Memory interface and base implementation.

This module provides the abstract interface (IMemory) and base implementation
(BaseMemory) for all memory system implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from loguru import logger

from simple_agent.managers.base import BaseManager
from simple_agent.models.config import Settings
from simple_agent.models.memory import (
    ForgettingPolicy,
    MemoryEntry,
    MemoryEntryType,
    MemoryImportance,
    MemoryMetadata,
    MemoryQuery,
    MemoryResult,
)


class IMemory(ABC):
    """Abstract interface for memory management.

    This interface defines the contract for all memory implementations,
    following the Dependency Inversion Principle (DIP).

    Implementations can be:
    - Vector-based (ChromaDB, Qdrant, Weaviate)
    - Keyword-based (Elasticsearch, Meilisearch)
    - Graph-based (Neo4j, NebulaGraph)
    - Hybrid (combination of above)
    """

    @abstractmethod
    def write(
        self,
        content: str,
        entry_type: str,
        **kwargs
    ) -> MemoryEntry:
        """Write a new memory entry.

        Args:
            content: Memory content
            entry_type: Type of memory (episodic, semantic, procedural)
            **kwargs: Additional metadata fields

        Returns:
            Created MemoryEntry
        """
        ...

    @abstractmethod
    def retrieve(self, query: MemoryQuery) -> MemoryResult:
        """Retrieve relevant memories based on query.

        Args:
            query: Memory query with search parameters

        Returns:
            MemoryResult with matching entries
        """
        ...

    @abstractmethod
    def update(
        self,
        entry_id: str,
        content: Optional[str] = None,
        **metadata_updates
    ) -> Optional[MemoryEntry]:
        """Update an existing memory entry.

        Args:
            entry_id: ID of entry to update
            content: New content (if None, keeps existing)
            **metadata_updates: Metadata fields to update

        Returns:
            Updated MemoryEntry or None if not found
        """
        ...

    @abstractmethod
    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: ID of entry to delete

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    def forget(self, policy: Dict[str, Any]) -> int:
        """Apply forgetting policy to clean up old/unimportant memories.

        Args:
            policy: Forgetting policy configuration

        Returns:
            Number of entries deleted
        """
        ...

    @abstractmethod
    def get_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory entry by ID.

        Args:
            entry_id: Entry ID to retrieve

        Returns:
            MemoryEntry if found, None otherwise
        """
        ...

    @abstractmethod
    def list_entries(
        self,
        project_id: Optional[str] = None,
        entry_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[MemoryEntry]:
        """List memory entries with optional filters.

        Args:
            project_id: Filter by project ID
            entry_type: Filter by entry type
            limit: Maximum number of entries to return

        Returns:
            List of MemoryEntry instances
        """
        ...

    @abstractmethod
    def clear(self) -> int:
        """Clear all memory entries.

        Returns:
            Number of entries cleared
        """
        ...

    @abstractmethod
    def count(self) -> int:
        """Get total number of memory entries.

        Returns:
            Total count of entries
        """
        ...

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get memory system information.

        Returns:
            Dictionary with memory system info (type, backend, config, etc.)
        """
        ...


class BaseMemory(BaseManager, IMemory):
    """Base implementation for memory management.

    This class provides common functionality for all memory implementations,
    following the Template Method pattern.

    Subclasses only need to implement the storage-specific methods:
    - _store_entry()
    - _load_entry()
    - _search_entries()
    - _delete_entry()
    - _list_all_entries()
    """

    # Class-level metadata
    memory_type: str = "base"
    description: str = "Base memory implementation"

    def __init__(
        self,
        settings: Optional[Settings] = None,
        encoder: Optional[Any] = None,
    ):
        """Initialize the base memory manager.

        Args:
            settings: Optional settings instance
            encoder: Optional encoder for generating embeddings
        """
        super().__init__(settings)
        self.encoder = encoder

        logger.info(
            f"[{self.__class__.__name__}] Initialized with "
            f"type={self.memory_type}, encoder={'enabled' if encoder else 'disabled'}"
        )

    # ========================================================================
    # Public Interface (from IMemory)
    # ========================================================================

    def write(
        self,
        content: str,
        entry_type: str,
        **kwargs
    ) -> MemoryEntry:
        """Write a new memory entry."""
        import uuid

        entry_id = str(uuid.uuid4())

        # Validate and convert entry type
        try:
            entry_type_enum = MemoryEntryType(entry_type)
        except ValueError:
            logger.warning(f"[{self.__class__.__name__}] Invalid entry_type={entry_type}, using semantic")
            entry_type_enum = MemoryEntryType.SEMANTIC

        # Validate and convert importance
        importance = kwargs.get("importance", MemoryImportance.MEDIUM)
        if isinstance(importance, str):
            try:
                importance = MemoryImportance(importance)
            except ValueError:
                importance = MemoryImportance.MEDIUM

        # Create metadata
        metadata = MemoryMetadata(
            entry_id=entry_id,
            entry_type=entry_type_enum,
            importance=importance,
            confidence=kwargs.get("confidence", 1.0),
            project_id=kwargs.get("project_id"),
            session_id=kwargs.get("session_id"),
            tags=kwargs.get("tags", []),
            source=kwargs.get("source"),
        )

        # Generate embedding if encoder available
        if self.encoder:
            try:
                metadata.embedding = self.encoder.encode(content)
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}] Failed to generate embedding: {e}")

        # Create entry
        entry = MemoryEntry(content=content, metadata=metadata)

        # Store using backend-specific implementation
        if self._store_entry(entry):
            logger.info(
                f"[{self.__class__.__name__}] Wrote entry={entry_id[:8]}..., "
                f"type={entry_type}, importance={importance}"
            )
        else:
            logger.error(f"[{self.__class__.__name__}] Failed to store entry={entry_id[:8]}...")

        return entry

    def retrieve(self, query: MemoryQuery) -> MemoryResult:
        """Retrieve relevant memories based on query."""
        import time

        start_time = time.time()

        # If encoder available, do semantic search
        if self.encoder:
            try:
                query_vector = self.encoder.encode(query.query_text)
                entries = self._search_entries(
                    query_vector,
                    limit=query.limit,
                    threshold=query.threshold
                )

                # Filter by metadata
                filtered_entries = self._filter_by_metadata(entries, query)

                # Update access stats
                for entry in filtered_entries:
                    self._update_access_stats(entry)

                execution_time = int((time.time() - start_time) * 1000)

                logger.info(
                    f"[{self.__class__.__name__}] Retrieved {len(filtered_entries)} entries "
                    f"for query='{query.query_text[:50]}...'"
                )

                return MemoryResult(
                    entries=filtered_entries,
                    total_found=len(filtered_entries),
                    query=query,
                    execution_time_ms=execution_time,
                )
            except Exception as e:
                logger.error(f"[{self.__class__.__name__}] Failed to retrieve: {e}")

        # Fallback: keyword search
        return self._keyword_search(query, start_time)

    def update(
        self,
        entry_id: str,
        content: Optional[str] = None,
        **metadata_updates
    ) -> Optional[MemoryEntry]:
        """Update an existing memory entry."""
        entry = self._load_entry(entry_id)
        if not entry:
            logger.warning(f"[{self.__class__.__name__}] Entry not found: {entry_id[:8]}...")
            return None

        # Update content
        if content is not None:
            entry.content = content

        # Update metadata
        for key, value in metadata_updates.items():
            if hasattr(entry.metadata, key):
                # Handle enum conversions
                if key == "importance" and isinstance(value, str):
                    try:
                        value = MemoryImportance(value)
                    except ValueError:
                        continue
                elif key == "entry_type" and isinstance(value, str):
                    try:
                        value = MemoryEntryType(value)
                    except ValueError:
                        continue
                setattr(entry.metadata, key, value)

        # Increment version
        entry.metadata.version += 1

        # Re-encode if content changed
        if content and self.encoder:
            try:
                entry.metadata.embedding = self.encoder.encode(content)
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}] Failed to re-encode: {e}")

        # Re-store
        if self._store_entry(entry):
            logger.info(
                f"[{self.__class__.__name__}] Updated entry={entry_id[:8]}..., "
                f"version={entry.metadata.version}"
            )
            return entry

        return None

    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        result = self._delete_entry(entry_id)
        if result:
            logger.info(f"[{self.__class__.__name__}] Deleted entry={entry_id[:8]}...")
        return result

    def forget(self, policy: Dict[str, Any]) -> int:
        """Apply forgetting policy to clean up old/unimportant memories."""
        from datetime import timedelta

        forgetting_policy = ForgettingPolicy(**policy)
        entries_to_delete = []

        # Get all entries
        all_entries = self.list_entries()

        for entry in all_entries:
            should_forget = False

            if forgetting_policy.policy_type == "lru":
                if forgetting_policy.max_entries:
                    # Sort by access count and last accessed
                    sorted_entries = sorted(
                        all_entries,
                        key=lambda e: (e.metadata.access_count, e.metadata.last_accessed)
                    )
                    if len(sorted_entries) > forgetting_policy.max_entries:
                        entries_to_delete = [
                            e.metadata.entry_id for e in sorted_entries[:-forgetting_policy.max_entries]
                        ]

            elif forgetting_policy.policy_type == "time_decay":
                if forgetting_policy.max_age_days:
                    cutoff = entry.metadata.created_at.now() - timedelta(days=forgetting_policy.max_age_days)
                    if entry.metadata.created_at < cutoff:
                        should_forget = True

            elif forgetting_policy.policy_type == "importance_based":
                if forgetting_policy.min_importance:
                    importance_order = {
                        MemoryImportance.CRITICAL: 4,
                        MemoryImportance.HIGH: 3,
                        MemoryImportance.MEDIUM: 2,
                        MemoryImportance.LOW: 1,
                    }
                    min_level = importance_order[forgetting_policy.min_importance]
                    entry_level = importance_order.get(entry.metadata.importance, 0)
                    if entry_level < min_level:
                        should_forget = True

            elif forgetting_policy.policy_type == "combined":
                # Combine multiple criteria
                cutoff = entry.metadata.created_at.now() - timedelta(days=forgetting_policy.max_age_days or 30)
                if entry.metadata.created_at < cutoff:
                    if entry.metadata.importance != MemoryImportance.CRITICAL:
                        should_forget = True

            if should_forget and entry.metadata.entry_id not in entries_to_delete:
                entries_to_delete.append(entry.metadata.entry_id)

        # Delete entries
        deleted_count = 0
        for entry_id in entries_to_delete:
            if self.delete(entry_id):
                deleted_count += 1

        logger.info(
            f"[{self.__class__.__name__}] Forgot {deleted_count} entries "
            f"using policy={forgetting_policy.policy_type}"
        )
        return deleted_count

    def get_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory entry by ID."""
        entry = self._load_entry(entry_id)
        if entry:
            self._update_access_stats(entry)
        return entry

    def list_entries(
        self,
        project_id: Optional[str] = None,
        entry_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[MemoryEntry]:
        """List memory entries with optional filters."""
        all_entries = self._list_all_entries()

        # Apply filters
        filtered = all_entries

        if project_id:
            filtered = [e for e in filtered if e.metadata.project_id == project_id]

        if entry_type:
            try:
                entry_type_enum = MemoryEntryType(entry_type)
                filtered = [e for e in filtered if e.metadata.entry_type == entry_type_enum]
            except ValueError:
                pass

        # Sort by created_at descending
        filtered.sort(key=lambda e: e.metadata.created_at, reverse=True)

        if limit:
            return filtered[:limit]

        return filtered

    def clear(self) -> int:
        """Clear all memory entries."""
        all_entries = self._list_all_entries()
        count = 0
        for entry in all_entries:
            if self.delete(entry.metadata.entry_id):
                count += 1
        return count

    def count(self) -> int:
        """Get total number of memory entries."""
        return len(self._list_all_entries())

    def get_info(self) -> Dict[str, Any]:
        """Get memory system information."""
        return {
            "type": self.memory_type,
            "description": self.description,
            "encoder": type(self.encoder).__name__ if self.encoder else None,
            "count": self.count(),
        }

    # ========================================================================
    # Abstract Methods (to be implemented by subclasses)
    # ========================================================================

    @abstractmethod
    def _store_entry(self, entry: MemoryEntry) -> bool:
        """Store an entry (backend-specific).

        Args:
            entry: Entry to store

        Returns:
            True if successful
        """
        ...

    @abstractmethod
    def _load_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Load an entry by ID (backend-specific).

        Args:
            entry_id: Entry ID to load

        Returns:
            MemoryEntry if found, None otherwise
        """
        ...

    @abstractmethod
    def _search_entries(
        self,
        query_vector: List[float],
        limit: int,
        threshold: float
    ) -> List[MemoryEntry]:
        """Search entries by vector (backend-specific).

        Args:
            query_vector: Query embedding
            limit: Maximum results
            threshold: Similarity threshold

        Returns:
            List of matching entries
        """
        ...

    @abstractmethod
    def _delete_entry(self, entry_id: str) -> bool:
        """Delete an entry (backend-specific).

        Args:
            entry_id: Entry ID to delete

        Returns:
            True if deleted
        """
        ...

    @abstractmethod
    def _list_all_entries(self) -> List[MemoryEntry]:
        """List all entries (backend-specific).

        Returns:
            List of all entries
        """
        ...

    # ========================================================================
    # Protected Helper Methods
    # ========================================================================

    def _filter_by_metadata(self, entries: List[MemoryEntry], query: MemoryQuery) -> List[MemoryEntry]:
        """Filter entries by metadata criteria."""
        filtered = entries

        if query.project_id:
            filtered = [e for e in filtered if e.metadata.project_id == query.project_id]

        if query.session_id:
            filtered = [e for e in filtered if e.metadata.session_id == query.session_id]

        if query.entry_types:
            filtered = [e for e in filtered if e.metadata.entry_type in query.entry_types]

        if query.tags:
            filtered = [
                e for e in filtered
                if any(t in e.metadata.tags for t in query.tags)
            ]

        if query.min_importance:
            importance_order = {
                MemoryImportance.CRITICAL: 4,
                MemoryImportance.HIGH: 3,
                MemoryImportance.MEDIUM: 2,
                MemoryImportance.LOW: 1,
            }
            min_level = importance_order[query.min_importance]
            filtered = [
                e for e in filtered
                if importance_order.get(e.metadata.importance, 0) >= min_level
            ]

        filtered = [
            e for e in filtered
            if e.metadata.confidence >= query.min_confidence
        ]

        return filtered

    def _update_access_stats(self, entry: MemoryEntry) -> None:
        """Update access statistics for an entry."""
        entry.metadata.last_accessed = entry.metadata.last_accessed.now()
        entry.metadata.access_count += 1

    def _keyword_search(self, query: MemoryQuery, start_time: float) -> MemoryResult:
        """Fallback keyword-based search."""
        import time

        query_lower = query.query_text.lower()
        all_entries = self._list_all_entries()

        matching = []
        for entry in all_entries:
            if query_lower in entry.content.lower():
                matching.append(entry)
                if len(matching) >= query.limit:
                    break

        execution_time = int((time.time() - start_time) * 1000)

        return MemoryResult(
            entries=matching,
            total_found=len(matching),
            query=query,
            execution_time_ms=execution_time,
        )


__all__ = ["IMemory", "BaseMemory"]
