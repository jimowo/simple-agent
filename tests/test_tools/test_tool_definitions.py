"""Tests for centralized tool definitions."""

from simple_agent.tools.handler_registry import ToolHandlerRegistry
from simple_agent.tools.tool_definitions import (
    TOOL_SPECS,
    TOOLS,
    get_subagent_tool_names,
    get_subagent_tools,
)


class TestToolDefinitions:
    """Verify tool definition consistency."""

    def test_tool_names_are_unique(self):
        """No tool name should be defined twice."""
        names = [tool["name"] for tool in TOOLS]
        assert len(names) == len(set(names))

    def test_subagent_tools_match_declared_names(self):
        """Subagent tool definitions should mirror the named subsets."""
        explore_names = [tool["name"] for tool in get_subagent_tools("Explore")]
        general_names = [tool["name"] for tool in get_subagent_tools("general-purpose")]

        assert explore_names == get_subagent_tool_names("Explore")
        assert general_names == get_subagent_tool_names("general-purpose")

    def test_handler_registry_covers_all_declared_subagent_tools(self, initialized_context):
        """The handler registry should resolve every declared subagent tool."""
        registry = ToolHandlerRegistry(initialized_context)

        for agent_type in ("Explore", "general-purpose"):
            tool_names = get_subagent_tool_names(agent_type)
            handlers = registry.get_handlers(tool_names)
            assert set(handlers) == set(tool_names)

    def test_tool_specs_are_complete(self):
        """Every exported tool should come from the canonical spec table."""
        assert set(tool["name"] for tool in TOOLS) == set(TOOL_SPECS)
