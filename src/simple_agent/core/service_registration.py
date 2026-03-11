"""Service registration for the dependency injection container.

This module contains functions to register the default service implementations
with the container, following the Dependency Inversion Principle (DIP).
"""

from typing import Any, Dict

from simple_agent.core.container import ServiceContainer
from simple_agent.exceptions import MissingApiKeyError
from simple_agent.models.config import Settings
from simple_agent.providers.base import BaseProvider


def register_managers(container: ServiceContainer) -> None:
    """Register manager services with the container.

    This registers all the manager implementations as singleton services.
    The managers are registered using their Protocol interfaces from
    simple_agent.interfaces.

    Args:
        container: The container to register services with
    """
    # Import here to avoid circular imports
    from simple_agent.interfaces.managers import (
        BackgroundManager,
        MessageBus,
        SkillLoader,
        TaskManager,
        TeammateManager,
        TodoManager,
    )
    from simple_agent.managers.background import BackgroundManager as BackgroundManagerImpl
    from simple_agent.managers.message import MessageBus as MessageBusImpl
    from simple_agent.managers.skill import SkillLoader as SkillLoaderImpl
    from simple_agent.managers.task import TaskManager as TaskManagerImpl
    from simple_agent.managers.teammate import TeammateManager as TeammateManagerImpl
    from simple_agent.managers.todo import TodoManager as TodoManagerImpl

    # TodoManager - no dependencies
    container.register_singleton(
        TodoManager,
        lambda c: TodoManagerImpl(),
    )

    # TaskManager - depends on Settings
    container.register_singleton(
        TaskManager,
        lambda c: TaskManagerImpl(settings=c.resolve(Settings)),
    )

    # BackgroundManager - depends on Settings
    container.register_singleton(
        BackgroundManager,
        lambda c: BackgroundManagerImpl(settings=c.resolve(Settings)),
    )

    # MessageBus - depends on Settings
    container.register_singleton(
        MessageBus,
        lambda c: MessageBusImpl(settings=c.resolve(Settings)),
    )

    # SkillLoader - depends on Settings
    container.register_singleton(
        SkillLoader,
        lambda c: SkillLoaderImpl(settings=c.resolve(Settings)),
    )

    # TeammateManager - depends on MessageBus, TaskManager, Settings
    container.register_singleton(
        TeammateManager,
        lambda c: TeammateManagerImpl(
            bus=c.resolve(MessageBus),
            task_mgr=c.resolve(TaskManager),
            settings=c.resolve(Settings),
        ),
    )


def register_providers(container: ServiceContainer) -> None:
    """Register provider-related services with the container.

    The provider is registered as a transient service since a new instance
    may be needed for different configurations.

    Args:
        container: The container to register services with
    """
    # Provider factory - creates provider based on settings
    container.register_transient(
        BaseProvider,
        lambda c: _create_provider(c.resolve(Settings)),
    )


def _create_provider(settings: Settings) -> BaseProvider:
    """Create a provider instance from settings.

    This function extracts the provider configuration from settings
    and uses ProviderFactory to create the appropriate provider.

    Args:
        settings: Application settings

    Returns:
        Provider instance
    """
    from simple_agent.models.config import ProviderConfigFactory
    from simple_agent.providers import ProviderFactory

    provider_name = settings.get_active_provider()
    provider_config = ProviderConfigFactory.create_config(settings, provider_name)

    api_key = provider_config.api_key
    if not api_key and provider_name != "local":
        import os

        env_key = ProviderConfigFactory.ENV_KEY_MAP.get(provider_name)
        if env_key:
            api_key = os.getenv(env_key)

    if not api_key and provider_name != "local":
        raise MissingApiKeyError(provider_name)

    return ProviderFactory.create(
        provider_name=provider_name,
        api_key=api_key or "dummy",
        base_url=provider_config.base_url,
        model=settings.model_id or None,
    )


# Utility functions for getting service instances
def get_managers(container: ServiceContainer | None = None) -> Dict[str, Any]:
    """Get all manager instances from the container.

    This is a convenience function for getting all managers at once,
    primarily used by the tool handlers system.

    Args:
        container: Optional container. If None, uses the global container.

    Returns:
        Dictionary of manager instances
    """
    if container is None:
        from simple_agent.core.container import get_container
        container = get_container()

    from simple_agent.interfaces.managers import (
        BackgroundManager,
        MessageBus,
        SkillLoader,
        TaskManager,
        TeammateManager,
        TodoManager,
    )

    return {
        "todo": container.resolve(TodoManager),
        "task": container.resolve(TaskManager),
        "background": container.resolve(BackgroundManager),
        "bus": container.resolve(MessageBus),
        "skill": container.resolve(SkillLoader),
        "teammate": container.resolve(TeammateManager),
    }
