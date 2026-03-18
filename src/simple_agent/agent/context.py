"""Agent context for dependency injection.

This module defines the AgentContext class which holds all dependencies
needed by the Agent, following the Dependency Inversion Principle (DIP).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from simple_agent.models.config import Settings
from simple_agent.providers.base import BaseProvider

if TYPE_CHECKING:
    from simple_agent.core.container import ServiceContainer
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

    _DEPENDENCY_FIELDS = (
        "todo",
        "task_mgr",
        "bg",
        "bus",
        "skill_loader",
        "teammate",
        "project_mgr",
        "session_mgr",
    )

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
    def from_container(
        cls,
        settings: Settings,
        *,
        container: Optional["ServiceContainer"] = None,
        **overrides,
    ):
        """Create AgentContext from the service container.

        This factory method resolves all dependencies from the container,
        following the Dependency Inversion Principle (DIP).

        Args:
            settings: Application settings to use

        Returns:
            AgentContext instance with all dependencies resolved
        """
        from simple_agent.core.container import create_container
        from simple_agent.core.service_registration import _create_provider

        container = container or create_container(
            settings,
            overrides=cls._build_container_overrides(overrides),
        )

        resolved = cls._resolve_manager_dependencies(container, overrides)
        memory_mgr = cls._resolve_memory_manager(container, overrides)

        return cls.from_components(
            settings=settings,
            provider=overrides.get("provider") or _create_provider(settings),
            memory_mgr=memory_mgr,
            **resolved,
        )

    @classmethod
    def from_components(
        cls,
        *,
        settings: Settings,
        provider: BaseProvider,
        todo,
        task_mgr,
        bg,
        bus,
        skill_loader,
        teammate,
        project_mgr,
        session_mgr,
        memory_mgr=None,
    ):
        """Create AgentContext from already-resolved dependencies."""
        return cls(
            settings=settings,
            todo=todo,
            task_mgr=task_mgr,
            bg=bg,
            bus=bus,
            skill_loader=skill_loader,
            teammate=teammate,
            project_mgr=project_mgr,
            session_mgr=session_mgr,
            memory_mgr=memory_mgr,
            provider=provider,
        )

    @classmethod
    def _build_container_overrides(cls, overrides: dict) -> dict:
        """Map context override field names to container interfaces."""
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
        return {
            interface: overrides[field_name]
            for field_name, interface in interface_map.items()
            if overrides.get(field_name) is not None
        }

    @classmethod
    def _resolve_manager_dependencies(cls, container, overrides: dict) -> dict:
        """Resolve required manager dependencies from the container."""
        from simple_agent.interfaces.managers import (
            BackgroundManager,
            MessageBus,
            ProjectManager,
            SessionManager,
            SkillLoader,
            TaskManager,
            TeammateManager,
            TodoManager,
        )

        interface_map = {
            "todo": TodoManager,
            "task_mgr": TaskManager,
            "bg": BackgroundManager,
            "bus": MessageBus,
            "skill_loader": SkillLoader,
            "teammate": TeammateManager,
            "project_mgr": ProjectManager,
            "session_mgr": SessionManager,
        }
        return {
            field_name: overrides.get(field_name) or container.resolve(interface)
            for field_name, interface in interface_map.items()
        }

    @classmethod
    def _resolve_memory_manager(cls, container, overrides: dict):
        """Resolve the optional memory manager dependency."""
        if overrides.get("memory_mgr") is not None:
            return overrides["memory_mgr"]

        from simple_agent.interfaces.managers import MemoryManager

        try:
            return container.resolve(MemoryManager)
        except Exception:
            return None
