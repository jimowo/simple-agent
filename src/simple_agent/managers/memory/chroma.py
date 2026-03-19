"""ChromaDB memory implementation.

This module provides the ChromaDB-based memory implementation that stores
and retrieves memory entries using ChromaDB's vector database.
"""

from typing import List, Optional

from loguru import logger

from simple_agent.managers.memory.interface import BaseMemory
from simple_agent.models.config import Settings
from simple_agent.models.memory import MemoryEntry, MemoryMetadata


class ChromaMemory(BaseMemory):
    """ChromaDB memory implementation.

    This implementation uses ChromaDB to store memory entries with their
    embeddings for efficient semantic search.

    Attributes:
        client: ChromaDB client instance
        collection: ChromaDB collection for memory entries
    """

    memory_type = "chroma"
    description = "ChromaDB vector database memory"

    def __init__(self, settings: Optional[Settings] = None, encoder: Optional[object] = None):
        """Initialize the ChromaDB memory.

        Args:
            settings: Application settings
            encoder: Optional encoder for generating embeddings
        """
        super().__init__(settings, encoder)

        # Import ChromaDB here to avoid hard dependency
        try:
            import chromadb
        except ImportError:
            raise ImportError(
                "ChromaDB is not installed. "
                "Install it with: pip install chromadb"
            )

        # Create ChromaDB client

        chroma_path = self.settings.memory_dir / "chroma"
        chroma_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(chroma_path))

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="memory",
            metadata={"hnsw:space": "cosine"}
        )

        logger.info(
            f"[ChromaMemory] Initialized with path={chroma_path}, "
            f"collection={self.collection.name}"
        )

    # ========================================================================
    # Abstract Method Implementations
    # ========================================================================

    def _store_entry(self, entry: MemoryEntry) -> bool:
        """Store a memory entry in ChromaDB."""
        try:
            # Prepare metadata for ChromaDB (must be flat dict)
            metadata_dict = self._prepare_metadata(entry.metadata)

            self.collection.add(
                ids=[entry.metadata.entry_id],
                embeddings=[entry.metadata.embedding] if entry.metadata.embedding else None,
                documents=[entry.content],
                metadatas=[metadata_dict]
            )

            logger.debug(
                f"[ChromaMemory] Stored entry={entry.metadata.entry_id[:8]}..., "
                f"type={entry.metadata.entry_type}"
            )
            return True
        except Exception as e:
            logger.error(f"[ChromaMemory] Failed to store entry: {e}")
            return False

    def _load_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Load a memory entry by ID from ChromaDB."""
        try:
            results = self.collection.get(
                ids=[entry_id],
                include=["embeddings", "documents", "metadatas"]
            )

            if not results["ids"]:
                return None

            return self._result_to_entry(results, 0)
        except Exception as e:
            logger.error(f"[ChromaMemory] Failed to load entry {entry_id}: {e}")
            return None

    def _search_entries(
        self,
        query_vector: List[float],
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[MemoryEntry]:
        """Search for similar entries by vector in ChromaDB."""
        try:
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=limit
            )

            entries = []
            for i, entry_id in enumerate(results.get("ids", [])[0]):
                # Calculate similarity (ChromaDB uses cosine similarity)
                distance = results.get("distances", [[0]])[0][i]
                similarity = 1 - distance  # Convert distance to similarity

                if similarity >= threshold:
                    entry = self._query_result_to_entry(results, i)
                    entries.append(entry)

            logger.debug(
                f"[ChromaMemory] Search returned {len(entries)} entries "
                f"(threshold={threshold})"
            )
            return entries
        except Exception as e:
            logger.error(f"[ChromaMemory] Failed to search: {e}")
            return []

    def _delete_entry(self, entry_id: str) -> bool:
        """Delete a memory entry from ChromaDB."""
        try:
            self.collection.delete(ids=[entry_id])
            logger.debug(f"[ChromaMemory] Deleted entry={entry_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"[ChromaMemory] Failed to delete entry {entry_id}: {e}")
            return False

    def _list_all_entries(self) -> List[MemoryEntry]:
        """List all memory entries from ChromaDB."""
        try:
            # Get all entries (limit to a reasonable number)
            results = self.collection.get(
                include=["embeddings", "documents", "metadatas"],
                limit=10000  # ChromaDB default limit
            )

            entries = []
            for i in range(len(results.get("ids", []))):
                entry = self._result_to_entry(results, i)
                entries.append(entry)

            return entries
        except Exception as e:
            logger.error(f"[ChromaMemory] Failed to list entries: {e}")
            return []

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _prepare_metadata(self, metadata: MemoryMetadata) -> dict:
        """Prepare metadata for ChromaDB storage.

        ChromaDB requires metadata to be a flat dict with string/number/bool values.
        """
        return {
            "entry_type": metadata.entry_type.value,
            "importance": metadata.importance.value,
            "created_at": metadata.created_at.isoformat(),
            "last_accessed": metadata.last_accessed.isoformat(),
            "access_count": metadata.access_count,
            "confidence": metadata.confidence,
            "project_id": metadata.project_id or "",
            "session_id": metadata.session_id or "",
            "tags": ",".join(metadata.tags) if metadata.tags else "",
            "source": metadata.source or "",
            "version": metadata.version,
        }

    def _result_to_entry(self, results: dict, index: int) -> MemoryEntry:
        """Convert ChromaDB get result to MemoryEntry."""
        metadata_dict = results["metadatas"][index]

        # Reconstruct metadata
        metadata = MemoryMetadata(
            entry_id=results["ids"][index],
            entry_type=metadata_dict.get("entry_type", "semantic"),
            importance=metadata_dict.get("importance", "medium"),
            created_at=metadata_dict.get("created_at", ""),
            last_accessed=metadata_dict.get("last_accessed", ""),
            access_count=metadata_dict.get("access_count", 0),
            confidence=metadata_dict.get("confidence", 1.0),
            project_id=metadata_dict.get("project_id") or None,
            session_id=metadata_dict.get("session_id") or None,
            tags=metadata_dict.get("tags", "").split(",") if metadata_dict.get("tags") else [],
            embedding=results.get("embeddings", [None])[index],
            source=metadata_dict.get("source") or None,
            version=metadata_dict.get("version", 1),
        )

        return MemoryEntry(
            content=results["documents"][index],
            metadata=metadata
        )

    def _query_result_to_entry(self, results: dict, index: int) -> MemoryEntry:
        """Convert ChromaDB query result to MemoryEntry."""
        # Query results have nested structure
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        embeddings = results.get("embeddings", [None])[0]

        metadata_dict = metadatas[index] if metadatas else {}

        metadata = MemoryMetadata(
            entry_id=ids[index],
            entry_type=metadata_dict.get("entry_type", "semantic"),
            importance=metadata_dict.get("importance", "medium"),
            created_at=metadata_dict.get("created_at", ""),
            last_accessed=metadata_dict.get("last_accessed", ""),
            access_count=metadata_dict.get("access_count", 0),
            confidence=metadata_dict.get("confidence", 1.0),
            project_id=metadata_dict.get("project_id") or None,
            session_id=metadata_dict.get("session_id") or None,
            tags=metadata_dict.get("tags", "").split(",") if metadata_dict.get("tags") else [],
            embedding=embeddings[index] if embeddings else None,
            source=metadata_dict.get("source") or None,
            version=metadata_dict.get("version", 1),
        )

        return MemoryEntry(
            content=documents[index] if documents else "",
            metadata=metadata
        )


__all__ = ["ChromaMemory"]
