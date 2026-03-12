"""Project and session data models.

This module defines Pydantic models for project and session management,
following the existing architecture patterns in simple_agent.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class ProjectMetadata(BaseModel):
    """Metadata for a project.

    A project represents a working directory and its associated sessions.
    """

    project_id: str = Field(..., description="Project ID (path-converted format)")
    original_path: str = Field(..., description="Original working directory path")
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    session_count: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        """Validate project ID format."""
        if not v:
            raise ValueError("project_id cannot be empty")
        # Remove leading/trailing separators
        return v.strip("--")


class SessionMessage(BaseModel):
    """A single message in a session.

    This represents either a user message or an assistant response.
    """

    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    timestamp: float = Field(..., description="Unix timestamp")
    message_id: Optional[str] = Field(default=None, description="Optional message ID")
    extra: Optional[Dict[str, Any]] = Field(default=None, description="Optional extra data")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate message role."""
        valid_roles = {"user", "assistant", "system"}
        if v not in valid_roles:
            raise ValueError(f"role must be one of {valid_roles}")
        return v


class SessionMetadata(BaseModel):
    """Metadata for a session.

    A session represents a conversation with the agent.
    """

    session_id: str = Field(..., description="Session UUID")
    project_id: str = Field(..., description="Parent project ID")
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    message_count: int = Field(default=0, ge=0)
    status: str = Field(default="active", description="Session status: active or archived")
    parent_session_id: Optional[str] = Field(default=None, description="Parent session ID for branching")
    title: Optional[str] = Field(default=None, description="Optional session title")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate session status."""
        valid_statuses = {"active", "archived"}
        if v not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}")
        return v


class SubagentMetadata(BaseModel):
    """Metadata for a subagent.

    Subagents are spawned for specific tasks (e.g., Explore, Plan agents).
    """

    agent_id: str = Field(..., description="Subagent unique ID")
    session_id: str = Field(..., description="Parent session ID")
    agent_type: str = Field(default="Subagent", description="Agent type: Subagent, Plan, Explore, etc.")
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
