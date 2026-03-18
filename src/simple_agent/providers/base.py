"""Base provider class and factory for multi-provider support."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from simple_agent.exceptions import InvalidProviderError, ProviderResponseError


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
        raise ProviderResponseError(
            self.__class__.__name__,
            "Subclasses must implement convert_response_to_standard",
        )

    def split_system_messages(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """Extract in-band system messages into a single top-level system prompt."""
        system_parts: List[str] = []
        if system:
            system_parts.append(system)

        filtered_messages: List[Dict[str, Any]] = []
        for msg in messages:
            if msg.get("role") == "system":
                text = self.content_to_text(msg.get("content", ""))
                if text:
                    system_parts.append(text)
            else:
                filtered_messages.append(msg)

        combined_system = "\n\n".join(part for part in system_parts if part).strip() or None
        return combined_system, filtered_messages

    def content_to_text(self, content: Any) -> str:
        """Extract plain text from a standard content payload."""
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for block in content:
                text = self.block_to_text(block)
                if text:
                    parts.append(text)
            return "\n".join(parts)
        return str(content)

    def block_to_text(self, block: Any) -> str:
        """Extract text from a single content block."""
        if block is None:
            return ""
        if isinstance(block, str):
            return block
        if isinstance(block, dict):
            block_type = block.get("type")
            if block_type == "text":
                return str(block.get("text", ""))
            if block_type == "tool_result":
                return str(block.get("content", ""))
            if block_type == "tool_use":
                return ""
        if hasattr(block, "type"):
            block_type = getattr(block, "type", "")
            if block_type == "text":
                return str(getattr(block, "text", ""))
            if block_type == "tool_result":
                return str(getattr(block, "content", ""))
        return ""

    def extract_tool_calls(self, message: Dict[str, Any]) -> List[ToolCall]:
        """Extract standardized tool calls from a message payload."""
        tool_calls: List[ToolCall] = []

        for tc in message.get("tool_calls") or []:
            if isinstance(tc, ToolCall):
                tool_calls.append(tc)
            elif isinstance(tc, dict):
                tool_calls.append(
                    ToolCall(
                        id=str(tc.get("id", "")),
                        name=str(tc.get("name", "")),
                        input=dict(tc.get("input", {})),
                    )
                )

        content = message.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            id=str(block.get("id", "")),
                            name=str(block.get("name", "")),
                            input=dict(block.get("input", {})),
                        )
                    )
                elif hasattr(block, "type") and getattr(block, "type", "") == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            id=str(getattr(block, "id", "")),
                            name=str(getattr(block, "name", "")),
                            input=dict(getattr(block, "input", {})),
                        )
                    )

        deduped: List[ToolCall] = []
        seen_ids: set[str] = set()
        for tc in tool_calls:
            if tc.id and tc.id not in seen_ids:
                seen_ids.add(tc.id)
                deduped.append(tc)
        return deduped

    def serialize_tool_call_arguments(self, input_data: Dict[str, Any]) -> str:
        """Serialize tool call input for providers that expect JSON strings."""
        return json.dumps(input_data, ensure_ascii=False)


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
            InvalidProviderError: If provider is not registered
        """
        cls._ensure_registered()
        provider_class = cls._providers.get(provider_name)
        if provider_class is None:
            raise InvalidProviderError(provider_name, list(cls._providers.keys()))
        return provider_class(api_key=api_key, base_url=base_url, model=model, **kwargs)

    @classmethod
    def list_providers(cls) -> List[str]:
        """List all registered providers."""
        cls._ensure_registered()
        return list(cls._providers.keys())
