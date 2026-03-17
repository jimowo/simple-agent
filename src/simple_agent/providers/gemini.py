"""Google Gemini provider implementation using the new google.genai package."""

from typing import Any, Dict, List, Optional

from google import genai
from google.genai.types import FunctionDeclaration, GenerateContentConfig, Tool

from simple_agent.providers.base import BaseProvider, ProviderResponse, ToolCall


class GeminiProvider(BaseProvider):
    """Google Gemini API provider using the new google.genai package."""

    DEFAULT_MODELS = [
        "gemini-2.5-flash-preview-04-17",
        "gemini-2.5-pro-preview-05-04",
        "gemini-2.0-flash-exp",
        "gemini-exp-1206",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.model is None:
            self.model = self.DEFAULT_MODELS[0]

    def create_client(self):
        """Configure Gemini API client."""
        client = genai.Client(api_key=self.api_key)
        return client

    def convert_messages_to_format(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert to Gemini message format."""
        # The new google.genai package handles this automatically
        return messages

    def convert_tools_to_format(self, tools: List[Dict[str, Any]]) -> Tool:
        """Convert to Gemini function declaration format."""
        function_declarations = []
        for tool in tools:
            function_declarations.append(
                FunctionDeclaration(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    parameters=tool.get("input_schema", {}),
                )
            )
        return Tool(function_declarations=function_declarations)

    def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 8000,
        **kwargs,
    ) -> ProviderResponse:
        """Create a message using Gemini API."""
        system_prompt, filtered_messages = self.split_system_messages(messages, system)

        # Build contents from messages using raw dict payloads so tool history can round-trip.
        contents = []
        for msg in filtered_messages:
            role = msg["role"]
            parts = []

            if role == "assistant":
                text = self.content_to_text(msg.get("content", ""))
                if text:
                    parts.append({"text": text})
                for tc in self.extract_tool_calls(msg):
                    parts.append(
                        {
                            "functionCall": {
                                "name": tc.name,
                                "args": tc.input,
                            }
                        }
                    )
                if parts:
                    contents.append({"role": "model", "parts": parts})
                continue

            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        parts.append(
                            {
                                "functionResponse": {
                                    "name": block.get("tool_name", "tool"),
                                    "response": {"output": str(block.get("content", ""))},
                                }
                            }
                        )
                    else:
                        text = self.block_to_text(block)
                        if text:
                            parts.append({"text": text})
            else:
                text = self.content_to_text(content)
                if text:
                    parts.append({"text": text})

            if parts:
                contents.append({"role": "user", "parts": parts})

        # Configure generation
        config = GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=kwargs.get("temperature", 1.0),
        )

        # Convert tools if provided
        gemini_tools = None
        if tools:
            gemini_tools = [self.convert_tools_to_format(tools)]

        # Generate response
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
            tools=gemini_tools,
            system_instruction=system_prompt,
        )

        return self.convert_response_to_standard(response)

    def convert_response_to_standard(self, response: Any) -> ProviderResponse:
        """Convert Gemini response to standard format."""
        content = []
        tool_calls = []

        stop_reason = "stop"

        # Process candidates
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]

            # Text content
            if hasattr(candidate, "content") and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        content.append({"type": "text", "text": part.text})

                    # Function calls (tool calls)
                    if hasattr(part, "function_call") and part.function_call:
                        func_call = part.function_call
                        tool_calls.append(
                            ToolCall(
                                id=f"call_{len(tool_calls)}",
                                name=func_call.name,
                                input=dict(func_call.args) if hasattr(func_call, "args") else {},
                            )
                        )

            # Finish reason
            if hasattr(candidate, "finish_reason"):
                finish_reason = candidate.finish_reason
                stop_reason = finish_reason.name.lower() if hasattr(finish_reason, "name") else str(finish_reason).lower()

        # Usage metadata
        usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "input_tokens": response.usage_metadata.prompt_token_count or 0,
                "output_tokens": response.usage_metadata.candidates_token_count or 0,
                "total_tokens": response.usage_metadata.total_token_count or 0,
            }

        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage=usage,
        )
