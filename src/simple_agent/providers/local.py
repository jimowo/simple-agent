"""Local model provider implementation (Ollama, vLLM)."""

from typing import Any, Dict, List, Optional

from openai import OpenAI

from simple_agent.providers.base import BaseProvider, ProviderResponse, ToolCall


class LocalProvider(BaseProvider):
    """
    Local model provider using Ollama or vLLM.

    Uses OpenAI-compatible API format.
    Default base_url: http://localhost:11434/v1 (Ollama)
    """

    DEFAULT_MODELS = [
        "llama3.2",
        "qwen2.5",
        "mistral",
        "codellama",
    ]

    DEFAULT_BASE_URL = "http://localhost:11434/v1"  # Ollama default

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.base_url is None:
            self.base_url = self.DEFAULT_BASE_URL
        if self.model is None:
            self.model = self.DEFAULT_MODELS[0]
        # Local models typically don't need API key
        if self.api_key == "dummy":
            self.api_key = "ollama"

    def create_client(self):
        """Create OpenAI-compatible client for local models."""
        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def convert_messages_to_format(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert to OpenAI-compatible message format."""
        formatted = []
        for msg in messages:
            formatted_msg = {"role": msg["role"], "content": msg["content"]}
            formatted.append(formatted_msg)
        return formatted

    def convert_tools_to_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert to OpenAI-compatible function format."""
        local_tools = []
        for tool in tools:
            local_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            }
            local_tools.append(local_tool)
        return local_tools

    def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 8000,
        **kwargs,
    ) -> ProviderResponse:
        """Create a message using local model API."""
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

        try:
            response = self.client.chat.completions.create(**params)
            return self.convert_response_to_standard(response)
        except Exception as e:
            # Provide helpful error message for common issues
            error_msg = str(e).lower()
            if "connection" in error_msg or "refused" in error_msg:
                raise ConnectionError(
                    f"Could not connect to local model server at {self.base_url}. "
                    f"Make sure Ollama/vLLM is running. "
                    f"For Ollama: 'ollama serve'"
                ) from e
            raise

    def convert_response_to_standard(self, response: Any) -> ProviderResponse:
        """Convert local model response to standard format."""
        content = []
        tool_calls = []

        message = response.choices[0].message

        # Text content
        if hasattr(message, "content") and message.content:
            content.append({"type": "text", "text": message.content})

        # Tool calls (if supported by the model)
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        input=eval(tc.function.arguments),
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
        """Approximate token count for local models."""
        return len(text) // 4
