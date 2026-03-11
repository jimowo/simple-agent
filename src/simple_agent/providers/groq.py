"""Groq provider implementation (fast inference)."""

import json
from typing import Any, Dict, List, Optional

from groq import Groq

from simple_agent.providers.base import BaseProvider, ProviderResponse, ToolCall


class GroqProvider(BaseProvider):
    """Groq API provider - fast inference for various models."""

    DEFAULT_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.model is None:
            self.model = self.DEFAULT_MODELS[0]

    def create_client(self):
        """Create Groq client."""
        return Groq(api_key=self.api_key, base_url=self.base_url)

    def convert_messages_to_format(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert to Groq message format (OpenAI compatible)."""
        formatted = []
        for msg in messages:
            formatted_msg = {"role": msg["role"], "content": msg["content"]}
            formatted.append(formatted_msg)
        return formatted

    def convert_tools_to_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert to Groq function format (OpenAI compatible)."""
        groq_tools = []
        for tool in tools:
            groq_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            }
            groq_tools.append(groq_tool)
        return groq_tools

    def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 8000,
        **kwargs,
    ) -> ProviderResponse:
        """Create a message using Groq API."""
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
        """Convert Groq response to standard format."""
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
                        input=json.loads(tc.function.arguments),
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

    @staticmethod
    def count_tokens(text: str) -> int:
        """Approximate token count for Groq."""
        return len(text) // 4
