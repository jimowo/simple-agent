"""OpenAI-compatible provider base class.

This module provides a base class for providers that use the OpenAI API format,
including OpenAI, Groq, and local model providers.
"""

import json
from typing import Any, Dict, List, Optional

from simple_agent.providers.base import BaseProvider, ProviderResponse, ToolCall


class OpenAICompatibleProvider(BaseProvider):
    """Base class for OpenAI-compatible API providers.

    This provider class handles the standard OpenAI API format used by
    multiple providers (OpenAI, Groq, local models via Ollama/vLLM, etc.).

    Subclasses only need to implement:
    - create_client(): Initialize the provider-specific client
    - convert_response_to_standard(): Convert provider response to standard format
    """

    def convert_messages_to_format(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert standard message format to OpenAI-compatible format.

        Args:
            messages: List of messages in standard format

        Returns:
            List of messages in OpenAI-compatible format
        """
        formatted = []
        for msg in messages:
            formatted_msg = {"role": msg["role"], "content": msg["content"]}
            formatted.append(formatted_msg)
        return formatted

    def convert_tools_to_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert standard tool format to OpenAI-compatible function format.

        Args:
            tools: List of tools in standard format

        Returns:
            List of tools in OpenAI-compatible function format
        """
        openai_tools = []
        for tool in tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            }
            openai_tools.append(openai_tool)
        return openai_tools

    def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 8000,
        **kwargs,
    ) -> ProviderResponse:
        """Create a message using the OpenAI-compatible API.

        Args:
            messages: Conversation history
            tools: Available tools
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            ProviderResponse with standardized format
        """
        formatted_messages = self.convert_messages_to_format(messages)

        # Add system message at the beginning
        if system:
            formatted_messages.insert(0, {"role": "system", "content": system})

        params = {
            "model": self.model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            **kwargs,
        }

        if tools:
            params["tools"] = self.convert_tools_to_format(tools)

        response = self.client.chat.completions.create(**params)
        return self.convert_response_to_standard(response)

    def convert_response_to_standard(self, response: Any) -> ProviderResponse:
        """Convert OpenAI-compatible response to standard format.

        This method extracts content and tool calls from the response.
        Subclasses can override if the response format differs.

        Args:
            response: Provider response

        Returns:
            ProviderResponse with standardized format
        """
        content = []
        tool_calls = []

        message = response.choices[0].message

        # Text content
        if hasattr(message, "content") and message.content:
            content.append({"type": "text", "text": message.content})

        # Tool calls
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        input=json.loads(tc.function.arguments),  # OpenAI returns JSON string
                    )
                )

        usage = None
        if hasattr(response, "usage"):
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }

        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=response.choices[0].finish_reason,
            usage=usage,
        )
