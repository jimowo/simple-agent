"""Core components for simple-agent."""

from simple_agent.core.container import (
    ServiceContainer,
    ServiceDescriptor,
    get_container,
    reset_container,
)

__all__ = [
    "ServiceContainer",
    "ServiceDescriptor",
    "get_container",
    "reset_container",
]
