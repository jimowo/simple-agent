"""Base tool definitions and registry.

This module provides the tool infrastructure following SOLID principles:
- Open/Closed Principle (OCP): Tools can be added without modifying existing code
- Single Responsibility Principle (SRP): Registry only manages tool registration
- Dependency Inversion Principle (DIP): Uses Protocol for tool interfaces
"""

from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field


class ToolInputSchema(BaseModel):
    """Tool input schema definition.

    This class defines the structure for tool input validation,
    following OpenAPI-style JSON schema format.
    """

    type: str = "object"
    properties: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    """Tool definition for API.

    This class represents a tool's API contract, including its name,
    description, and input schema.
    """

    name: str
    description: str
    input_schema: ToolInputSchema


class ToolHandler(Protocol):
    """Tool handler interface.

    A tool handler is a callable that executes tool logic.
    This Protocol follows the Dependency Inversion Principle (DIP).
    """

    def __call__(self, **kwargs) -> str:
        """Execute the tool.

        Args:
            **kwargs: Tool input parameters

        Returns:
            Tool result as string
        """
        ...


class Tool(Protocol):
    """Tool interface.

    This Protocol defines the contract for tools, following the
    Dependency Inversion Principle (DIP). Tools can be registered
    and discovered dynamically.
    """

    @property
    def name(self) -> str:
        """Get tool name.

        Returns:
            Tool name (used for registration and invocation)
        """
        ...

    @property
    def description(self) -> str:
        """Get tool description.

        Returns:
            Human-readable description of what the tool does
        """
        ...

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get tool input schema.

        Returns:
            JSON schema for tool input validation
        """
        ...

    @property
    def handler(self) -> ToolHandler:
        """Get tool handler function.

        Returns:
            Callable that executes the tool
        """
        ...


class ToolRegistry:
    """Registry for tool handlers.

    This class follows the Single Responsibility Principle (SRP) by
    solely being responsible for registering and managing tools.
    It supports dynamic registration following the Open/Closed Principle (OCP).

    The registry maintains tools and provides convenient methods for
    converting to different formats (API schema, handlers dict, etc.).
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool.

        If a tool with the same name already exists, it will be replaced.

        Args:
            tool: Tool instance to register

        Example:
            registry.register(ReadFileTool())
        """
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """Unregister a tool by name.

        Args:
            name: Tool name to unregister

        Returns:
            True if tool was found and removed, False otherwise
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: Tool name

        Returns:
            True if tool is registered, False otherwise
        """
        return name in self._tools

    def list_all(self) -> List[Tool]:
        """List all registered tools.

        Returns:
            List of all registered tools
        """
        return list(self._tools.values())

    def to_api_schema(self) -> List[Dict[str, Any]]:
        """Convert tools to API schema format.

        This method converts all registered tools to the format
        expected by the Anthropic API (and similar providers).

        Returns:
            List of tool definitions in API schema format
        """
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    def get_handlers_dict(self) -> Dict[str, ToolHandler]:
        """Get tool handlers as a dictionary.

        This method is provided for backward compatibility with
        the existing tool_handlers module.

        Returns:
            Dictionary mapping tool names to handler callables
        """
        return {name: tool.handler for name, tool in self._tools.items()}

    def clear(self) -> None:
        """Clear all registered tools.

        This is primarily useful for testing.
        """
        self._tools.clear()

    def __len__(self) -> int:
        """Get the number of registered tools.

        Returns:
            Number of tools
        """
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered using 'in' operator.

        Args:
            name: Tool name

        Returns:
            True if tool is registered
        """
        return name in self._tools

    def __iter__(self):
        """Iterate over registered tools.

        Returns:
            Iterator over tools
        """
        return iter(self._tools.values())


# Backward compatibility: keep old Tool class as a base
class ToolBase:
    """Base class for tools (backward compatibility).

    New code should use the Tool Protocol instead.
    """

    name: str = ""
    description: str = ""
    input_schema: ToolInputSchema = ToolInputSchema()

    def __call__(self, **kwargs) -> str:
        """Execute the tool."""
        raise NotImplementedError


# Global tool registry instance
_global_registry: Optional[ToolRegistry] = None


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    The registry is lazily initialized on first access.

    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_global_registry() -> None:
    """Reset the global tool registry.

    This is primarily useful for testing.
    """
    global _global_registry
    _global_registry = None
