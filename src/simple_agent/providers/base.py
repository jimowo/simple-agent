"""Base provider class and factory for multi-provider support."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    """Standardized message format."""
    role: str
    content: str


@dataclass
class ToolCall:
    """Standardized tool call format."""
    id: str
    name: str
    input: Dict[str, Any]


@dataclass
class ToolResult:
    """Standardized tool result format."""
    tool_use_id: str
    content: str


@dataclass
class ProviderResponse:
    """Standardized provider response."""
    content: List[Any]
    tool_calls: List[ToolCall]
    stop_reason: str
    usage: Optional[Dict[str, int]] = None


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._client = None

    @abstractmethod
    def create_client(self):
        """Create and return the provider's client instance."""
        pass

    @property
    def client(self):
        """Lazy client initialization."""
        if self._client is None:
            self._client = self.create_client()
        return self._client

    @abstractmethod
    def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 8000,
        **kwargs,
    ) -> ProviderResponse:
        """
        Create a message using the provider's API.

        Args:
            messages: Conversation history
            tools: Available tools
            system: System prompt
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            ProviderResponse with standardized format
        """
        pass

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text (approximately).

        Default implementation uses the rough estimate: 1 token ~ 4 characters.
        Subclasses can override this for more accurate token counting if needed.
        """
        return len(text) // 4

    def convert_messages_to_format(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert standard message format to provider-specific format.
        Override if provider uses different format.
        """
        return messages

    def convert_tools_to_format(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert standard tool format to provider-specific format.
        Override if provider uses different format.
        """
        return tools

    def convert_response_to_standard(
        self, response: Any
    ) -> ProviderResponse:
        """
        Convert provider response to standard ProviderResponse.
        Must be implemented by each provider.
        """
        raise NotImplementedError("Subclasses must implement convert_response_to_standard")


class ProviderFactory:
    """Factory for creating provider instances."""

    _providers: Dict[str, type] = {}
    _registered = False

    @classmethod
    def register(cls, name: str, provider_class: type):
        """Register a provider class."""
        cls._providers[name] = provider_class

    @classmethod
    def _ensure_registered(cls):
        """Ensure built-in providers are registered (lazy initialization)."""
        if not cls._registered:
            from simple_agent.providers.anthropic import AnthropicProvider
            from simple_agent.providers.gemini import GeminiProvider
            from simple_agent.providers.groq import GroqProvider
            from simple_agent.providers.local import LocalProvider
            from simple_agent.providers.openai import OpenAIProvider

            cls.register("anthropic", AnthropicProvider)
            cls.register("openai", OpenAIProvider)
            cls.register("gemini", GeminiProvider)
            cls.register("groq", GroqProvider)
            cls.register("local", LocalProvider)
            cls._registered = True

    @classmethod
    def create(
        cls,
        provider_name: str,
        api_key: str,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> BaseProvider:
        """
        Create a provider instance.

        Args:
            provider_name: Name of the provider (anthropic, openai, etc.)
            api_key: API key for the provider
            base_url: Optional base URL
            model: Optional model override
            **kwargs: Additional provider-specific parameters

        Returns:
            Provider instance

        Raises:
            ValueError: If provider is not registered
        """
        cls._ensure_registered()
        provider_class = cls._providers.get(provider_name)
        if provider_class is None:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available: {list(cls._providers.keys())}"
            )
        return provider_class(api_key=api_key, base_url=base_url, model=model, **kwargs)

    @classmethod
    def list_providers(cls) -> List[str]:
        """List all registered providers."""
        cls._ensure_registered()
        return list(cls._providers.keys())
