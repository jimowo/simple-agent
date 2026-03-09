"""Task and Todo models."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class TodoItem(BaseModel):
    """Todo item for tracking multi-step work."""

    content: str = Field(..., min_length=1, description="Task description")
    status: str = Field(default="pending", description="Task status")
    active_form: str = Field(..., min_length=1, alias="activeForm", description="Active form description")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is one of the allowed values."""
        valid_statuses = {"pending", "in_progress", "completed"}
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got '{v}'")
        return v

    @field_validator("content", "active_form")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()


class Task(BaseModel):
    """Persistent file-based task."""

    id: int
    subject: str
    description: str = ""
    status: str = "pending"
    owner: Optional[str] = None
    blocked_by: List[int] = Field(default_factory=list, alias="blockedBy")
    blocks: List[int] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class InboxMessage(BaseModel):
    """Message in teammate inbox."""

    type: str
    from_: str = Field(..., alias="from")
    content: str
    timestamp: float
    extra: Optional[dict] = None

    class Config:
        populate_by_name = True
