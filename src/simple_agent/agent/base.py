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
        # Legacy parameters for backward compatibility
        todo_manager=None,
        task_manager=None,
        background_manager=None,
        message_bus=None,
        teammate_manager=None,
        skill_loader=None,
        permission_manager=None,
    ):
        """Initialize the Agent.

        Args:
            settings: Application settings (optional, uses default if None)
            context: Pre-built AgentContext (optional, creates from settings if None)
            todo_manager: Legacy parameter for backward compatibility
            task_manager: Legacy parameter for backward compatibility
            background_manager: Legacy parameter for backward compatibility
            message_bus: Legacy parameter for backward compatibility
            teammate_manager: Legacy parameter for backward compatibility
            skill_loader: Legacy parameter for backward compatibility
            permission_manager: Optional pre-configured permission manager
        """
        # Use provided context or create from settings
        if context is not None:
            self._ctx = context
        else:
            # Check for legacy-style initialization
            if any(
                x is not None
                for x in [
                    todo_manager,
                    task_manager,
                    background_manager,
                    message_bus,
                    teammate_manager,
                    skill_loader,
                ]
            ):
                # Legacy mode: create context from provided managers
                self._ctx = self._create_legacy_context(
                    settings or Settings(),
                    todo_manager,
                    task_manager,
                    background_manager,
                    message_bus,
                    teammate_manager,
                    skill_loader,
                )
            else:
                # Modern mode: create context from settings using container
                self._ctx = AgentContext.from_container(settings or Settings())

        # Store permission manager for later use
        self._external_permission_manager = permission_manager

        # Initialize tool handlers with managers from context
        self._initialize_tool_handlers()

    def _create_legacy_context(
        self,
        settings: Settings,
        todo_manager,
        task_manager,
        background_manager,
        message_bus,
        teammate_manager,
        skill_loader,
    ) -> AgentContext:
        """Create AgentContext from legacy manager arguments.

        This maintains backward compatibility with code that directly
        provides manager instances.

        Args:
            settings: Application settings
            todo_manager: Todo manager instance
            task_manager: Task manager instance
            background_manager: Background manager instance
            message_bus: Message bus instance
            teammate_manager: Teammate manager instance
            skill_loader: Skill loader instance

        Returns:
            AgentContext with provided managers
        """
        from simple_agent.core.service_registration import _create_provider
        from simple_agent.managers.background import (
            BackgroundManager as BackgroundManagerImpl,
        )
        from simple_agent.managers.message import MessageBus as MessageBusImpl
        from simple_agent.managers.project import ProjectManager as ProjectManagerImpl
        from simple_agent.managers.session import SessionManager as SessionManagerImpl
        from simple_agent.managers.skill import SkillLoader as SkillLoaderImpl
        from simple_agent.managers.task import TaskManager as TaskManagerImpl
        from simple_agent.managers.teammate import TeammateManager as TeammateManagerImpl

        # Create managers if not provided
        from simple_agent.managers.todo import TodoManager as TodoManagerImpl

        todo = todo_manager or TodoManagerImpl()
        task = task_manager or TaskManagerImpl(settings)
        bg = background_manager or BackgroundManagerImpl(settings)
        bus = message_bus or MessageBusImpl(settings)
        skill = skill_loader or SkillLoaderImpl(settings=settings)
        teammate = teammate_manager or TeammateManagerImpl(bus, task, settings)
        project = ProjectManagerImpl(settings)
        session = SessionManagerImpl(settings)
        provider = _create_provider(settings)

        return AgentContext(
            settings=settings,
            todo=todo,
            task_mgr=task,
            bg=bg,
            bus=bus,
            skill_loader=skill,
            teammate=teammate,
            project_mgr=project,
            session_mgr=session,
            memory_mgr=None,
            provider=provider,
        )

    def _initialize_tool_handlers(self) -> None:
        """Initialize tool handlers with managers from context.

        This creates a ToolHandlerRegistry using dependency injection,
        following modern best practices. Global state initialization is
        kept for backward compatibility only.
        """
        from simple_agent.permissions import PermissionManager
        from simple_agent.tools.handler_registry import ToolHandlerRegistry

        # Use provided permission manager or create a default one
        if self._external_permission_manager is not None:
            permission_manager = self._external_permission_manager
        else:
            permission_manager = PermissionManager()

        # Create tool handler registry using dependency injection
        self._tool_registry = ToolHandlerRegistry(self._ctx, permission_manager)

        # Store permission manager for access
        self._permission_manager = permission_manager

        # Initialize global state for backward compatibility
        # TODO: Remove this in future version when all code uses DI
        self._initialize_legacy_handlers(permission_manager)

    def _initialize_legacy_handlers(self, permission_manager) -> None:
        """Initialize legacy global tool handlers for backward compatibility.

        DEPRECATED: This method exists for backward compatibility only.
        New code should use ToolHandlerRegistry via dependency injection.
        """
        from simple_agent.tools.tool_handlers import initialize_handlers

        initialize_handlers(
            self._ctx.todo,
            self._ctx.task_mgr,
            self._ctx.bg,
            self._ctx.bus,
            self._ctx.teammate,
            self._ctx.skill_loader,
            self._ctx.provider,
            self._ctx.settings,
            permission_manager=permission_manager,
        )

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

    # Backward compatibility property aliases
    @property
    def todo_manager(self):
        """Alias for todo property (backward compatibility)."""
        return self._ctx.todo

    @property
    def task_manager(self):
        """Alias for task_mgr property (backward compatibility)."""
        return self._ctx.task_mgr

    @property
    def background_manager(self):
        """Alias for bg property (backward compatibility)."""
        return self._ctx.bg

    @property
    def message_bus(self):
        """Alias for bus property (backward compatibility)."""
        return self._ctx.bus
