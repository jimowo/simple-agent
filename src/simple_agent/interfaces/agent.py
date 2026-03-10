"""Agent interface definitions.

This module defines the interfaces for agent creation and management,
following the Dependency Inversion Principle (DIP) of SOLID.
"""

from typing import Protocol

from simple_agent.models.config import Settings


class AgentFactory(Protocol):
    """Interface for creating Agent instances.

    This factory pattern allows for different Agent implementations
    and facilitates testing with mock agents.
    """

    def create_agent(self, settings: Settings) -> "Agent":
        """Create an Agent instance with the given settings.

        Args:
            settings: Configuration settings

        Returns:
            Agent instance
        """
        ...


class Agent(Protocol):
    """Interface for AI Agent.

    The Agent is responsible for processing user queries and managing
    the conversation flow.
    """

    def process_query(self, query: str, history: list = None) -> str:
        """Process a user query.

        Args:
            query: User query string
            history: Optional conversation history

        Returns:
            Agent response string
        """
        ...

    @property
    def settings(self) -> Settings:
        """Get agent settings.

        Returns:
            Settings instance
        """
        ...

    @property
    def system_prompt(self) -> str:
        """Get system prompt for the agent.

        Returns:
            System prompt string
        """
        ...
