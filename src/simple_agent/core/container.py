"""Dependency Injection Container for simple-agent.

This module implements a simple dependency injection container that follows
the Dependency Inversion Principle (DIP) of SOLID. It allows for loose coupling
between components and facilitates testing.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Type, TypeVar

T = TypeVar("T")


@dataclass
class ServiceDescriptor:
    """Descriptor for a registered service."""

    factory: Callable[["ServiceContainer"], Any]
    singleton: bool = True
    instance: Any = field(default=None, init=False)

    def __post_init__(self):
        """Initialize descriptor."""
        object.__setattr__(self, "instance", None)


class ServiceContainer:
    """Simple dependency injection container.

    This container manages service lifecycle and dependencies. It supports
    both singleton and transient service lifetimes.
    """

    def __init__(self) -> None:
        """Initialize an empty container."""
        self._services: Dict[str, ServiceDescriptor] = {}
        self._singletons: Dict[str, Any] = {}

    def register_singleton(
        self, interface: Type[T], factory: Callable[["ServiceContainer"], T]
    ) -> None:
        """Register a singleton service.

        A singleton service is created once and reused for all requests.

        Args:
            interface: The interface/class type to register
            factory: Factory function that creates the service instance

        Example:
            container.register_singleton(
                Settings,
                lambda c: Settings()
            )
        """
        name = self._get_service_name(interface)
        self._services[name] = ServiceDescriptor(factory=factory, singleton=True)

    def register_transient(
        self, interface: Type[T], factory: Callable[["ServiceContainer"], T]
    ) -> None:
        """Register a transient service.

        A transient service is created on each request.

        Args:
            interface: The interface/class type to register
            factory: Factory function that creates the service instance
        """
        name = self._get_service_name(interface)
        self._services[name] = ServiceDescriptor(factory=factory, singleton=False)

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register an existing instance as a singleton.

        Args:
            interface: The interface/class type to register
            instance: The instance to register
        """
        name = self._get_service_name(interface)
        descriptor = ServiceDescriptor(factory=lambda c: instance, singleton=True)
        descriptor.instance = instance
        self._services[name] = descriptor

    def resolve(self, interface: Type[T]) -> T:
        """Resolve a service from the container.

        Args:
            interface: The interface/class type to resolve

        Returns:
            The service instance

        Raises:
            ValueError: If the service is not registered
        """
        name = self._get_service_name(interface)
        if name not in self._services:
            available = ", ".join(sorted(self._services.keys()))
            raise ValueError(
                f"Service '{name}' not registered. Available services: {available}"
            )

        descriptor = self._services[name]

        if descriptor.singleton:
            if descriptor.instance is None:
                descriptor.instance = descriptor.factory(self)
            return descriptor.instance
        else:
            return descriptor.factory(self)

    def has(self, interface: Type[T]) -> bool:
        """Check if a service is registered.

        Args:
            interface: The interface/class type to check

        Returns:
            True if registered, False otherwise
        """
        name = self._get_service_name(interface)
        return name in self._services

    def _get_service_name(self, interface: Type[T]) -> str:
        """Get the service name for an interface type.

        Args:
            interface: The interface/class type

        Returns:
            The service name (class name)
        """
        # Handle typing.ForwardRef and other special cases
        if hasattr(interface, "__name__"):
            return interface.__name__
        return str(interface)

    def clear(self) -> None:
        """Clear all registered services and singletons.

        This is primarily useful for testing.
        """
        self._services.clear()
        self._singletons.clear()


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Get the global service container.

    The container is lazily initialized with default services on first access.

    Returns:
        The global ServiceContainer instance
    """
    global _container
    if _container is None:
        _container = ServiceContainer()
        _register_default_services(_container)
    return _container


def reset_container() -> None:
    """Reset the global container.

    This is primarily useful for testing. It clears all services
    and allows a fresh container to be created on next access.
    """
    global _container
    _container = None


def _register_default_services(container: ServiceContainer) -> None:
    """Register default services for the container.

    This function is called automatically when the container is first created.
    It can be extended to register additional services.

    Args:
        container: The container to register services with
    """
    # Import here to avoid circular imports
    from simple_agent.core.service_registration import (
        register_managers,
        register_providers,
    )
    from simple_agent.models.config import Settings

    # Register Settings first as it's a dependency for other services
    container.register_singleton(Settings, lambda c: Settings())

    # Register managers
    register_managers(container)

    # Register providers
    register_providers(container)
