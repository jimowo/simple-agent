"""Agent loop utilities.

This module implements the AgentLoop class following SOLID principles:
- Single Responsibility Principle (SRP): Focused solely on conversation loop execution
- Dependency Inversion Principle (DIP): Uses AgentContext and ToolHandlerRegistry for dependencies
"""

import json
from typing import Any, Dict, List, Optional

from loguru import logger

from simple_agent.agent.context import AgentContext
from simple_agent.tools.handler_registry import ToolHandlerRegistry
from simple_agent.tools.tool_definitions import TOOLS
from simple_agent.utils.compression import auto_compact, estimate_tokens, microcompact


class AgentLoop:
    """Agent conversation loop executor.

    This class follows the Single Responsibility Principle (SRP) by
    solely being responsible for executing the conversation loop.
    It coordinates between the LLM provider, tool execution, and
    message processing.

    Attributes:
        _ctx: Agent context containing all dependencies
        _tool_registry: Tool handler registry for executing tools
        _rounds_without_todo: Counter for tracking todo usage
    """

    def __init__(
        self,
        context: AgentContext,
        tool_registry: Optional[ToolHandlerRegistry] = None,
        permission_manager=None,
    ) -> None:
        """Initialize the agent loop.

        Args:
            context: Agent context with all dependencies
            tool_registry: Optional tool handler registry (created from context if None)
            permission_manager: Optional permission manager (for backward compatibility)
        """
        self._ctx = context
        self._rounds_without_todo = 0

        # Create or use provided tool registry
        if tool_registry is None:
            self._tool_registry = ToolHandlerRegistry(context, permission_manager)
        else:
            self._tool_registry = tool_registry

    def run(self, messages: List[Dict[str, Any]]) -> None:
        """Run the agent conversation loop.

        This method executes the main conversation loop:
        1. Compress messages if needed
        2. Process background notifications
        3. Process inbox messages
        4. Call LLM
        5. Execute tools if requested
        6. Repeat until no tool use

        Args:
            messages: Message history list (modified in-place)
        """
        while True:
            self._compress_if_needed(messages)
            self._process_background_notifications(messages)
            self._process_inbox(messages)

            response = self._call_llm(messages)
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                return

            self._execute_tools(response, messages)

    def _compress_if_needed(self, messages: List[Dict[str, Any]]) -> None:
        """Compress messages if token threshold exceeded.

        This method now uses session-aware compression when a session is active,
        saving the full conversation history to the session file and optionally
        creating a branch for the compressed conversation.

        Args:
            messages: Message history list (modified-in-place)
        """
        microcompact(messages)
        if estimate_tokens(messages) > self._ctx.settings.token_threshold:
            print("[auto-compact triggered]")

            # Try session-aware compression if session is available
            current_session = self._ctx.session_mgr.get_current_session()
            if current_session:
                from simple_agent.utils.compression import session_aware_compact

                try:
                    messages[:] = session_aware_compact(
                        messages,
                        self._ctx.provider,
                        self._ctx.settings.model_id or "default",
                        current_session.project_id,
                        current_session.session_id,
                        self._ctx.session_mgr,
                        create_branch=False,  # Can be made configurable later
                    )
                    print(f"[Session saved: {current_session.session_id[:8]}...]")
                    return
                except Exception as e:
                    print(f"[Session compression failed: {e}, using legacy method]")

            # Fallback to legacy compression
            messages[:] = auto_compact(
                messages,
                self._ctx.provider,
                self._ctx.settings.model_id or "default",
                self._ctx.settings.transcript_dir,
            )

    def _process_background_notifications(
        self, messages: List[Dict[str, Any]]
    ) -> None:
        """Process background task notifications.

        Args:
            messages: Message history list (modified in-place)
        """
        notifs = self._ctx.bg.drain()
        if notifs:
            txt = "\n".join(
                f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs
            )
            messages.append(
                {
                    "role": "user",
                    "content": f"<background-results>\n{txt}\n</background-results>",
                }
            )
            messages.append({"role": "assistant", "content": "Noted background results."})

    def _process_inbox(self, messages: List[Dict[str, Any]]) -> None:
        """Process inbox messages.

        Args:
            messages: Message history list (modified in-place)
        """
        inbox = self._ctx.bus.read_inbox("lead")
        if inbox:
            messages.append(
                {"role": "user", "content": f"<inbox>{json.dumps(inbox, indent=2)}</inbox>"}
            )
            messages.append({"role": "assistant", "content": "Noted inbox messages."})

    def _call_llm(self, messages: List[Dict[str, Any]]) -> Any:
        """Call the LLM provider.

        Args:
            messages: Message history list

        Returns:
            Provider response
        """
        return self._ctx.provider.create_message(
            messages=messages,
            tools=TOOLS,
            system=self._ctx.system_prompt,
            max_tokens=self._ctx.settings.max_tokens,
        )

    def _execute_tools(
        self, response: Any, messages: List[Dict[str, Any]]
    ) -> None:
        """Execute tool calls from LLM response.

        Args:
            response: Provider response with tool calls
            messages: Message history list (modified in-place)
        """
        # Get permission-aware handlers from tool registry
        handlers = self._tool_registry.get_permission_aware_handlers()

        logger.debug(f"[TOOL_EXECUTION] Tool calls received: {len(response.tool_calls)} tools")
        logger.debug(f"[TOOL_EXECUTION] Available handlers: {list(handlers.keys())}")

        results = []
        used_todo = False
        manual_compress = False

        for idx, tc in enumerate(response.tool_calls):
            logger.debug(f"[TOOL_EXECUTION] [{idx+1}/{len(response.tool_calls)}] Tool: {tc.name}")
            logger.debug(f"[TOOL_EXECUTION] [{idx+1}/{len(response.tool_calls)}] Input: {tc.input}")

            if tc.name == "compress":
                manual_compress = True

            handler = handlers.get(tc.name)

            if handler is None:
                logger.warning(f"[TOOL_EXECUTION] [{idx+1}/{len(response.tool_calls)}] Unknown tool: {tc.name}")
                output = f"Unknown tool: {tc.name}"
            else:
                logger.debug(f"[TOOL_EXECUTION] [{idx+1}/{len(response.tool_calls)}] Handler found, executing...")
                try:
                    output = handler(**tc.input)
                    logger.debug(f"[TOOL_EXECUTION] [{idx+1}/{len(response.tool_calls)}] Success. Output length: {len(str(output))} chars")
                except Exception as e:
                    logger.error(f"[TOOL_EXECUTION] [{idx+1}/{len(response.tool_calls)}] Error: {e}", exc_info=True)
                    output = f"Error: {e}"

            print(f"> {tc.name}: {str(output)[:200]}")
            results.append(
                {"type": "tool_result", "tool_use_id": tc.id, "content": str(output)}
            )

            if tc.name == "TodoWrite":
                used_todo = True

        # Nag reminder for todo usage
        self._rounds_without_todo = 0 if used_todo else self._rounds_without_todo + 1
        if self._rounds_without_todo >= 3:
            results.insert(
                0, {"type": "text", "text": "<reminder>Update your todos.</reminder>"}
            )

        messages.append({"role": "user", "content": results})

        # Manual compress if requested
        if manual_compress:
            print("[manual compact]")
            messages[:] = auto_compact(
                messages,
                self._ctx.provider,
                self._ctx.settings.model_id or "default",
                self._ctx.settings.transcript_dir,
            )


# Backward compatibility function
def agent_loop(messages: list, agent) -> None:
    """Run agent loop for conversation history.

    This is a backward compatibility wrapper that uses AgentLoop.

    Args:
        messages: Message history list (modified in-place)
        agent: Agent instance (must have _ctx attribute)
    """
    # Get context from agent (new Agent class has _ctx)
    if hasattr(agent, "_ctx"):
        context = agent._ctx
        # Try to use the agent's existing tool registry and permission manager
        tool_registry = getattr(agent, "_tool_registry", None)
        permission_manager = getattr(agent, "_permission_manager", None)
        logger.debug(f"[AGENT_LOOP] Using agent's tool_registry: {tool_registry is not None}")
        logger.debug(f"[AGENT_LOOP] Using agent's permission_manager: {permission_manager is not None}")
    else:
        # Legacy fallback - try to build context from agent attributes
        from simple_agent.agent.context import AgentContext
        context = AgentContext(
            settings=agent.settings,
            todo=agent.todo,
            task_mgr=agent.task_mgr,
            bg=agent.bg,
            bus=agent.bus,
            skill_loader=agent.skill_loader,
            teammate=agent.teammate,
            provider=agent.provider,
        )
        tool_registry = None
        permission_manager = None

    loop = AgentLoop(context, tool_registry, permission_manager)
    loop.run(messages)
