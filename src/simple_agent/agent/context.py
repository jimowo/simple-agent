"""Agent context for dependency injection.

This module defines the AgentContext class which holds all dependencies
needed by the Agent, following the Dependency Inversion Principle (DIP).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from simple_agent.models.config import Settings
from simple_agent.providers.base import BaseProvider

if TYPE_CHECKING:
    from simple_agent.interfaces.managers import (
        BackgroundManager,
        MemoryManager,
        MessageBus,
        ProjectManager,
        SessionManager,
        SkillLoader,
        TaskManager,
        TeammateManager,
        TodoManager,
    )


@dataclass
class AgentContext:
    """Context object holding all Agent dependencies.

    This class follows the Single Responsibility Principle (SRP) by
    solely being responsible for holding and providing access to
    Agent dependencies. It enables dependency injection without
    requiring the Agent to know how to create its dependencies.

    Attributes:
        settings: Application settings
        todo: Todo manager instance
        task_mgr: Task manager instance
        bg: Background manager instance
        bus: Message bus instance
        skill_loader: Skill loader instance
        teammate: Teammate manager instance
        project_mgr: Project manager instance
        session_mgr: Session manager instance
        memory_mgr: Memory manager instance (optional)
        provider: AI provider instance
    """

    settings: Settings
    todo: "TodoManager"
    task_mgr: "TaskManager"
    bg: "BackgroundManager"
    bus: "MessageBus"
    skill_loader: "SkillLoader"
    teammate: "TeammateManager"
    project_mgr: "ProjectManager"
    session_mgr: "SessionManager"
    memory_mgr: Optional["MemoryManager"]
    provider: BaseProvider

    @property
    def system_prompt(self) -> str:
        """Get system prompt for the agent.

        Returns:
            System prompt string
        """
        return f"""You are a coding agent at {self.settings.workdir}.
Use tools to solve tasks. Use TodoWrite for multi-step work.
Use task for subagent delegation. Use load_skill for specialized knowledge.

Skills available:
{self.skill_loader.descriptions()}"""

    @classmethod
    def from_container(cls, settings: Settings, **overrides):
        """Create AgentContext from the service container.

        This factory method resolves all dependencies from the container,
        following the Dependency Inversion Principle (DIP).

        Args:
            settings: Application settings to use

        Returns:
            AgentContext instance with all dependencies resolved
        """
        from simple_agent.core.container import get_container
        from simple_agent.core.service_registration import _create_provider
        from simple_agent.interfaces.managers import (
            BackgroundManager,
            MemoryManager,
            MessageBus,
            ProjectManager,
            SessionManager,
            SkillLoader,
            TaskManager,
            TeammateManager,
            TodoManager,
        )

        container = get_container()

        # Override Settings with the provided one
        container.register_instance(Settings, settings)

        # Override selected manager instances when the caller needs shared state.
        interface_map = {
            "todo": TodoManager,
            "task_mgr": TaskManager,
            "bg": BackgroundManager,
            "bus": MessageBus,
            "skill_loader": SkillLoader,
            "teammate": TeammateManager,
            "project_mgr": ProjectManager,
            "session_mgr": SessionManager,
            "memory_mgr": MemoryManager,
        }
        for field_name, interface in interface_map.items():
            if overrides.get(field_name) is not None:
                container.register_instance(interface, overrides[field_name])

        # Resolve all dependencies
        provider = _create_provider(settings)

        # Resolve MemoryManager (may be None if disabled)
        memory_mgr = overrides.get("memory_mgr")
        if memory_mgr is None:
            try:
                memory_mgr = container.resolve(MemoryManager)
            except Exception:
                pass  # Memory manager is optional

        return cls(
            settings=settings,
            todo=overrides.get("todo") or container.resolve(TodoManager),
            task_mgr=overrides.get("task_mgr") or container.resolve(TaskManager),
            bg=overrides.get("bg") or container.resolve(BackgroundManager),
            bus=overrides.get("bus") or container.resolve(MessageBus),
            skill_loader=overrides.get("skill_loader") or container.resolve(SkillLoader),
            teammate=overrides.get("teammate") or container.resolve(TeammateManager),
            project_mgr=overrides.get("project_mgr") or container.resolve(ProjectManager),
            session_mgr=overrides.get("session_mgr") or container.resolve(SessionManager),
            memory_mgr=memory_mgr,
            provider=provider,
        )
