"""Anthropic (Claude) provider implementation."""

from typing import Any, Dict, List, Optional

from anthropic import Anthropic

from simple_agent.providers.base import BaseProvider, ProviderResponse, ToolCall


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider."""

    DEFAULT_MODELS = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.model is None:
            self.model = self.DEFAULT_MODELS[0]

    def create_client(self):
        """Create Anthropic client."""
        if self.base_url:
            return Anthropic(base_url=self.base_url, api_key=self.api_key)
        return Anthropic(api_key=self.api_key)

    def convert_messages_to_format(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert standard message format to Anthropic content blocks."""
        formatted: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")
            blocks: List[Dict[str, Any]] = []

            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type")
                        if block_type == "text":
                            blocks.append({"type": "text", "text": str(block.get("text", ""))})
                        elif block_type == "tool_result":
                            blocks.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.get("tool_use_id", ""),
                                    "content": str(block.get("content", "")),
                                }
                            )
                    elif hasattr(block, "type") and getattr(block, "type", "") == "text":
                        blocks.append({"type": "text", "text": str(getattr(block, "text", ""))})
            else:
                text = self.content_to_text(content)
                if text:
                    blocks.append({"type": "text", "text": text})

            if role == "assistant":
                for tc in self.extract_tool_calls(msg):
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.input,
                        }
                    )

            formatted.append({"role": role, "content": blocks or [{"type": "text", "text": ""}]})

        return formatted

    def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 8000,
        **kwargs,
    ) -> ProviderResponse:
        """Create a message using Anthropic API."""
        system_prompt, filtered_messages = self.split_system_messages(messages, system)
        params = {
            "model": self.model,
            "messages": self.convert_messages_to_format(filtered_messages),
            "max_tokens": max_tokens,
            **kwargs,
        }

        if tools:
            params["tools"] = self.convert_tools_to_format(tools)

        if system_prompt:
            params["system"] = system_prompt

        response = self.client.messages.create(**params)
        return self.convert_response_to_standard(response)

    def convert_response_to_standard(self, response: Any) -> ProviderResponse:
        """Convert Anthropic response to standard format."""
        tool_calls = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, input=block.input)
                )

        usage = None
        if hasattr(response, "usage"):
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

        return ProviderResponse(
            content=response.content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage=usage,
        )
