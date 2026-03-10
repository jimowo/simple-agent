"""Agent context for dependency injection.

This module defines the AgentContext class which holds all dependencies
needed by the Agent, following the Dependency Inversion Principle (DIP).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from simple_agent.models.config import Settings
from simple_agent.providers.base import BaseProvider

if TYPE_CHECKING:
    from simple_agent.interfaces.managers import (
        BackgroundManager,
        MessageBus,
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
        provider: AI provider instance
    """

    settings: Settings
    todo: "TodoManager"
    task_mgr: "TaskManager"
    bg: "BackgroundManager"
    bus: "MessageBus"
    skill_loader: "SkillLoader"
    teammate: "TeammateManager"
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
    def from_container(cls, settings: Settings):
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
            MessageBus,
            SkillLoader,
            TaskManager,
            TeammateManager,
            TodoManager,
        )

        container = get_container()

        # Override Settings with the provided one
        container.register_instance(Settings, settings)

        # Resolve all dependencies
        provider = _create_provider(settings)

        return cls(
            settings=settings,
            todo=container.resolve(TodoManager),
            task_mgr=container.resolve(TaskManager),
            bg=container.resolve(BackgroundManager),
            bus=container.resolve(MessageBus),
            skill_loader=container.resolve(SkillLoader),
            teammate=container.resolve(TeammateManager),
            provider=provider,
        )
