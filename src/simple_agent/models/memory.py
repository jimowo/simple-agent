"""Memory data models for agent long-term memory management.

This module defines Pydantic models for memory entries, queries, and results,
following the existing architecture patterns in simple_agent.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class MemoryEntryType(str, Enum):
    """Types of memory entries.

    EPISODIC: Specific events/experiences (conversations, actions)
    SEMANTIC: General knowledge/facts (user preferences, project info)
    PROCEDURAL: Skills and how-to knowledge (workflows, patterns)
    """
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryImportance(str, Enum):
    """Importance levels for memory entries.

    CRITICAL: Essential information that should rarely be forgotten
    HIGH: Important information for long-term retention
    MEDIUM: Standard importance (default)
    LOW: Less important information that can be forgotten first
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MemoryMetadata(BaseModel):
    """Metadata for a memory entry.

    This follows the pattern from SessionMetadata and ProjectMetadata.
    """
    entry_id: str = Field(..., description="Unique memory entry ID")
    entry_type: MemoryEntryType = Field(..., description="Type of memory")
    importance: MemoryImportance = Field(
        default=MemoryImportance.MEDIUM,
        description="Importance level"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp"
    )
    last_accessed: datetime = Field(
        default_factory=datetime.now,
        description="Last access timestamp"
    )
    access_count: int = Field(
        default=0,
        ge=0,
        description="Number of times accessed"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score"
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Associated project ID"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Associated session ID"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Searchable tags"
    )
    embedding: Optional[List[float]] = Field(
        default=None,
        description="Vector embedding"
    )
    source: Optional[str] = Field(
        default=None,
        description="Source of the memory"
    )
    version: int = Field(
        default=1,
        ge=1,
        description="Version for conflict resolution"
    )

    @field_validator("entry_id")
    @classmethod
    def validate_entry_id(cls, v: str) -> str:
        """Validate entry ID format."""
        if not v:
            raise ValueError("entry_id cannot be empty")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence score."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class MemoryEntry(BaseModel):
    """A single memory entry.

    This represents a piece of information stored in the agent's long-term memory,
    following the pattern from SessionMessage.
    """
    content: str = Field(..., description="Memory content/text")
    metadata: MemoryMetadata = Field(..., description="Memory metadata")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is not empty."""
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v.strip()


class MemoryQuery(BaseModel):
    """Query for searching memory.

    This defines the parameters for memory retrieval.
    """
    query_text: str = Field(..., description="Query text for semantic search")
    project_id: Optional[str] = Field(
        default=None,
        description="Filter by project ID"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Filter by session ID"
    )
    entry_types: Optional[List[MemoryEntryType]] = Field(
        default=None,
        description="Filter by entry types"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Filter by tags"
    )
    min_importance: Optional[MemoryImportance] = Field(
        default=None,
        description="Minimum importance level"
    )
    min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum results to return"
    )
    threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Similarity threshold"
    )

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, v: str) -> str:
        """Validate query text is not empty."""
        if not v or not v.strip():
            raise ValueError("query_text cannot be empty")
        return v.strip()


class MemoryResult(BaseModel):
    """Result from a memory query.

    This follows the pattern from ProviderResponse.
    """
    entries: List[MemoryEntry] = Field(
        default_factory=list,
        description="Retrieved memory entries"
    )
    total_found: int = Field(
        default=0,
        ge=0,
        description="Total number of matching entries"
    )
    query: MemoryQuery = Field(..., description="Original query")
    execution_time_ms: Optional[int] = Field(
        default=None,
        description="Query execution time in milliseconds"
    )


class ForgettingPolicy(BaseModel):
    """Policy for memory forgetting/cleanup.

    This defines how and when memories should be forgotten.
    """
    policy_type: str = Field(
        ...,
        description="Policy type: lru, time_decay, importance_based, combined"
    )
    max_entries: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of entries"
    )
    max_age_days: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum age in days"
    )
    min_importance: Optional[MemoryImportance] = Field(
        default=None,
        description="Minimum importance to keep"
    )
    access_threshold: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum access count"
    )

    @field_validator("policy_type")
    @classmethod
    def validate_policy_type(cls, v: str) -> str:
        """Validate policy type."""
        valid_policies = {"lru", "time_decay", "importance_based", "combined"}
        if v not in valid_policies:
            raise ValueError(f"policy_type must be one of {valid_policies}")
        return v
