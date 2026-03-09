"""Base tool definitions and registry."""

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolInputSchema(BaseModel):
    """Tool input schema definition."""

    type: str = "object"
    properties: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    """Tool definition for API."""

    name: str
    description: str
    input_schema: ToolInputSchema


class Tool:
    """Base class for tools."""

    name: str = ""
    description: str = ""
    input_schema: ToolInputSchema = ToolInputSchema()

    def __call__(self, **kwargs) -> str:
        """Execute the tool."""
        raise NotImplementedError


class ToolRegistry:
    """Registry for tool handlers."""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register(self, name: str, handler: Callable) -> None:
        """Register a tool handler."""
        self._handlers[name] = handler

    def get(self, name: str) -> Optional[Callable]:
        """Get a tool handler by name."""
        return self._handlers.get(name)

    def execute(self, name: str, **kwargs) -> str:
        """Execute a tool by name."""
        handler = self.get(name)
        if handler is None:
            return f"Unknown tool: {name}"
        try:
            return handler(**kwargs)
        except Exception as e:
            return f"Error: {e}"
