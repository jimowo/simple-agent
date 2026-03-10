"""Interfaces and protocols for simple-agent."""

from simple_agent.interfaces.agent import Agent, AgentFactory
from simple_agent.interfaces.managers import (
    BackgroundManager,
    MessageBus,
    SkillLoader,
    TaskManager,
    TeammateManager,
    TodoManager,
)

__all__ = [
    "TodoManager",
    "TaskManager",
    "BackgroundManager",
    "MessageBus",
    "SkillLoader",
    "TeammateManager",
    "AgentFactory",
    "Agent",
]
