"""Message models for agent communication."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class Message(BaseModel):
    """Base message model."""

    role: str
    content: Union[str, List[Dict[str, Any]]]


class ToolCall(BaseModel):
    """Tool call representation."""

    id: str
    name: str
    input: Dict[str, Any]


class ToolResult(BaseModel):
    """Tool result representation."""

    type: str = "tool_result"
    tool_use_id: str
    content: str


class ContentBlock(BaseModel):
    """Content block from Anthropic API."""

    type: str
    text: Optional[str] = None


class TextContent(BaseModel):
    """Text content block."""

    type: str = "text"
    text: str


class ToolUseContent(BaseModel):
    """Tool use content block."""

    type: str = "tool_use"
    id: str
    name: str
    input: Dict[str, Any]


class ResponseContent(BaseModel):
    """Response content wrapper."""

    content: List[Union[TextContent, ToolUseContent]]
    stop_reason: Optional[str] = None


# Valid message types for messaging system
VALID_MSG_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_response",
}
