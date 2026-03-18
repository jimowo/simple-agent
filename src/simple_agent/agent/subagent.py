"""Sub-agent runner for isolated task execution.

This module implements the SubAgentRunner class which follows the
Single Responsibility Principle (SRP) by solely being responsible for
running sub-agents with isolated tool access.
"""

from typing import Any, Callable, Dict, List, Optional

from simple_agent.providers.base import BaseProvider
from simple_agent.tools.handler_registry import ToolHandlerRegistry
from simple_agent.tools.search_tools import glob_files, grep_content
from simple_agent.utils.constants import MAX_TOOL_OUTPUT, LoopIterations


class SubAgentRunner:
    """Runner for sub-agent execution.

    This class has a single responsibility: running sub-agents with
    appropriate tool access based on the agent type. It follows the
    Single Responsibility Principle (SRP).

    Attributes:
        provider: AI provider to use for sub-agent
        tool_registry: Tool handler registry (optional, creates minimal handlers if None)
    """

    def __init__(
        self,
        provider: BaseProvider,
        tool_registry: Optional[ToolHandlerRegistry] = None,
    ) -> None:
        """Initialize the sub-agent runner.

        Args:
            provider: AI provider instance
            tool_registry: Optional tool handler registry (creates minimal handlers if None)
        """
        self._provider = provider
        self._tool_registry = tool_registry

    def run(self, prompt: str, agent_type: str = "Explore") -> str:
        """Run a sub-agent with the given prompt.

        The sub-agent has limited tool access based on the agent_type:
        - "Explore": Only read_file and bash tools
        - Other types: All tools including write_file and edit_file

        Args:
            prompt: Prompt for the sub-agent
            agent_type: Type of agent ("Explore" or "general-purpose")

        Returns:
            Summary of sub-agent work
        """
        tools = self._build_tools(agent_type)
        handlers = self._build_handlers(agent_type)
        messages = [{"role": "user", "content": prompt}]

        for _ in range(LoopIterations.MAX_SUBAGENT_ITERATIONS):
            resp = self._provider.create_message(
                messages=messages, tools=tools, max_tokens=8000
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": resp.content,
                    "tool_calls": resp.tool_calls,
                }
            )

            if resp.stop_reason != "tool_use":
                break

            results = self._execute_tools(resp, handlers)
            messages.append({"role": "user", "content": results})

        return self._extract_summary(resp)

    def _build_tools(self, agent_type: str) -> List[Dict[str, Any]]:
        """Build tool list for sub-agent.

        Args:
            agent_type: Type of agent

        Returns:
            List of tool definitions
        """
        from simple_agent.tools.tool_definitions import get_subagent_tools

        return get_subagent_tools(agent_type)

    def _build_handlers(self, agent_type: str) -> Dict[str, Callable]:
        """Build tool handlers for sub-agent.

        Args:
            agent_type: Type of agent to determine available tools

        Returns:
            Dictionary mapping tool names to handler functions
        """
        from simple_agent.tools.tool_definitions import get_subagent_tool_names

        tool_names = get_subagent_tool_names(agent_type)

        # Use ToolHandlerRegistry if available
        if self._tool_registry is not None:
            return self._tool_registry.get_handlers(tool_names)

        # Fallback to minimal handlers when no registry was supplied.
        from simple_agent.tools.bash_tools import run_bash
        from simple_agent.tools.file_tools import edit_file, read_file, write_file

        handlers = {
            "bash": lambda **kw: run_bash(kw["command"]),
            "read_file": lambda **kw: read_file(kw["path"]),
            "glob": lambda **kw: glob_files(kw["pattern"], kw.get("path")),
            "grep": lambda **kw: grep_content(
                kw["pattern"],
                kw.get("path"),
                kw.get("file_pattern"),
                kw.get("ignore_case", False),
            ),
        }

        # Add write/edit tools for non-Explore agents
        if agent_type != "Explore":
            handlers.update({
                "write_file": lambda **kw: write_file(kw["path"], kw["content"]),
                "edit_file": lambda **kw: edit_file(kw["path"], kw["old_text"], kw["new_text"]),
            })

        return handlers

    def _execute_tools(
        self, response: Any, handlers: Dict[str, Callable]
    ) -> List[Dict[str, Any]]:
        """Execute tool calls from response.

        Args:
            response: Provider response with tool calls
            handlers: Tool handler functions

        Returns:
            List of tool results
        """
        results = []
        for tc in response.tool_calls:
            h = handlers.get(tc.name, lambda **kw: "Unknown tool")
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "tool_name": tc.name,
                    "content": str(h(**tc.input))[:MAX_TOOL_OUTPUT],
                }
            )
        return results

    def _extract_summary(self, response: Any) -> str:
        """Extract text summary from response.

        Args:
            response: Provider response

        Returns:
            Extracted text or placeholder
        """
        if not response:
            return "(subagent failed)"

        text_parts = []
        for c in response.content:
            if isinstance(c, dict) and c.get("type") == "text":
                text_parts.append(c.get("text", ""))
        return "".join(text_parts) or "(no summary)"
