"""Core Agent functionality.

This module implements the Agent class following SOLID principles:
- Single Responsibility Principle (SRP): Agent focuses solely on query processing
- Dependency Inversion Principle (DIP): Uses AgentContext for injected dependencies
"""

import uuid
from typing import Optional

from simple_agent.agent.context import AgentContext
from simple_agent.agent.loop import AgentLoop
from simple_agent.models.config import Settings


def handle_shutdown_request(bus, teammate: str) -> str:
    """Handle shutdown request for a teammate.

    Args:
        bus: Message bus instance
        teammate: Name of teammate to shutdown

    Returns:
        Confirmation message
    """
    from simple_agent.managers.teammate import shutdown_requests

    req_id = str(uuid.uuid4())[:8]
    shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
    bus.send(
        "lead",
        teammate,
        "Please shut down.",
        "shutdown_request",
        {"request_id": req_id},
    )
    return f"Shutdown request {req_id} sent to '{teammate}'"


def handle_plan_review(
    bus, request_id: str, approve: bool, feedback: str = ""
) -> str:
    """Handle plan approval response.

    Args:
        bus: Message bus instance
        request_id: Plan request ID
        approve: Whether to approve the plan
        feedback: Optional feedback message

    Returns:
        Confirmation message
    """
    from simple_agent.managers.teammate import plan_requests

    req = plan_requests.get(request_id)
    if not req:
        return f"Error: Unknown plan request_id '{request_id}'"
    req["status"] = "approved" if approve else "rejected"
    bus.send(
        "lead",
        req["from"],
        feedback,
        "plan_approval_response",
        {
            "request_id": request_id,
            "approve": approve,
            "feedback": feedback,
        },
    )
    return f"Plan {req['status']} for '{req['from']}'"


class Agent:
    """Main Agent class.

    This class follows the Single Responsibility Principle (SRP) by
    focusing solely on processing user queries and coordinating
    with other components through dependency injection.

    The Agent uses AgentContext to access all its dependencies,
    following the Dependency Inversion Principle (DIP).
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        context: Optional[AgentContext] = None,
        permission_manager=None,
    ):
        """Initialize the Agent.

        Args:
            settings: Application settings (optional, uses default if None)
            context: Pre-built AgentContext (optional, creates from settings if None)
            permission_manager: Optional pre-configured permission manager
        """
        resolved_settings = settings or Settings()
        self._ctx = self._resolve_context(resolved_settings, context=context)
        self._permission_manager = self._resolve_permission_manager(permission_manager)
        self._tool_registry = self._create_tool_registry(self._ctx, self._permission_manager)

    def _resolve_context(
        self,
        settings: Settings,
        *,
        context: Optional[AgentContext],
    ) -> AgentContext:
        """Resolve the active AgentContext through the modern context factory."""
        if context is not None:
            return context

        return AgentContext.from_container(settings)

    def _resolve_permission_manager(self, permission_manager):
        """Resolve the permission manager used by this agent."""
        if permission_manager is not None:
            return permission_manager

        from simple_agent.permissions import PermissionManager

        return PermissionManager()

    def _create_tool_registry(self, context: AgentContext, permission_manager):
        """Create the tool registry used by the agent loop."""
        from simple_agent.tools.handler_registry import ToolHandlerRegistry

        return ToolHandlerRegistry(context, permission_manager)

    @property
    def settings(self) -> Settings:
        """Get agent settings.

        Returns:
            Settings instance
        """
        return self._ctx.settings

    @property
    def system_prompt(self) -> str:
        """Get system prompt for the agent.

        Returns:
            System prompt string
        """
        return self._ctx.system_prompt

    @property
    def todo(self):
        """Get todo manager.

        Returns:
            TodoManager instance
        """
        return self._ctx.todo

    @property
    def task_mgr(self):
        """Get task manager.

        Returns:
            TaskManager instance
        """
        return self._ctx.task_mgr

    @property
    def bg(self):
        """Get background manager.

        Returns:
            BackgroundManager instance
        """
        return self._ctx.bg

    @property
    def bus(self):
        """Get message bus.

        Returns:
            MessageBus instance
        """
        return self._ctx.bus

    @property
    def skill_loader(self):
        """Get skill loader.

        Returns:
            SkillLoader instance
        """
        return self._ctx.skill_loader

    @property
    def teammate(self):
        """Get teammate manager.

        Returns:
            TeammateManager instance
        """
        return self._ctx.teammate

    @property
    def provider(self):
        """Get AI provider.

        Returns:
            BaseProvider instance
        """
        return self._ctx.provider

    @property
    def permission_manager(self):
        """Get permission manager.

        Returns:
            PermissionManager instance
        """
        return self._permission_manager

    def process_query(self, query: str, history: Optional[list] = None) -> str:
        """Process a user query.

        This method delegates to AgentLoop for the actual conversation loop,
        following the Single Responsibility Principle (SRP).

        Args:
            query: User query
            history: Optional message history (modified in-place)

        Returns:
            Agent response string
        """
        if history is None:
            history = []

        history.append({"role": "user", "content": query})

        # Use AgentLoop for the conversation logic with ToolHandlerRegistry
        loop = AgentLoop(self._ctx, self._tool_registry, self._permission_manager)
        loop.run(history)

        # Extract and return the last assistant response
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                content = msg.get("content", [])
                if isinstance(content, list):
                    text_parts = []
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            text = c.get("text", "")
                            if text:
                                text_parts.append(str(text))
                        elif hasattr(c, "text"):
                            text = getattr(c, "text", "")
                            if text:
                                text_parts.append(str(text))
                    return "\n".join(text_parts)
                return str(content)
        return "(no response)"
