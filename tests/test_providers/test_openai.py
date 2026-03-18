"""Test OpenAI provider with focus on security."""

import json
from unittest.mock import Mock

import pytest

from simple_agent.providers.base import ToolCall
from simple_agent.providers.openai import OpenAIProvider


@pytest.mark.security
class TestOpenAIProviderSecurity:
    """Test OpenAI provider security aspects."""

    def test_json_parsing_not_eval(self):
        """Test that function arguments use json.loads, not eval."""
        provider = OpenAIProvider(api_key="test-key")

        # Create mock response with valid JSON function call
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Response text"

        # Create mock tool call with proper attribute access
        mock_tc = Mock()
        mock_tc.id = "call_123"
        mock_tc.function.name = "test_tool"
        mock_tc.function.arguments = '{"param": "value", "number": 42}'

        mock_message.tool_calls = [mock_tc]
        mock_response.choices = [Mock(message=mock_message, finish_reason="stop")]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=20)

        result = provider.convert_response_to_standard(mock_response)

        assert len(result.tool_calls) == 1
        tool_call = result.tool_calls[0]
        assert isinstance(tool_call, ToolCall)
        assert tool_call.name == "test_tool"
        # Verify it's parsed as a dict, not eval'd
        assert tool_call.input == {"param": "value", "number": 42}

    def test_malicious_code_injection_blocked(self):
        """Test that malicious code injection is safely rejected."""
        provider = OpenAIProvider(api_key="test-key")

        # Attempt to inject Python code
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Response"

        mock_tc = Mock()
        mock_tc.id = "call_456"
        mock_tc.function.name = "test_tool"
        mock_tc.function.arguments = '__import__("os").system("rm -rf /")'

        mock_message.tool_calls = [mock_tc]
        mock_response.choices = [Mock(message=mock_message, finish_reason="stop")]

        # Should raise JSON decode error, not execute code
        with pytest.raises(json.JSONDecodeError):
            provider.convert_response_to_standard(mock_response)

    def test_invalid_json_handling(self):
        """Test handling of invalid JSON."""
        provider = OpenAIProvider(api_key="test-key")

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Response"

        mock_tc = Mock()
        mock_tc.id = "call_789"
        mock_tc.function.name = "test_tool"
        mock_tc.function.arguments = '{invalid json}'

        mock_message.tool_calls = [mock_tc]
        mock_response.choices = [Mock(message=mock_message, finish_reason="stop")]

        # Should raise error, not crash
        with pytest.raises(json.JSONDecodeError):
            provider.convert_response_to_standard(mock_response)

    def test_empty_json_object(self):
        """Test handling of empty JSON object."""
        provider = OpenAIProvider(api_key="test-key")

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Response"

        mock_tc = Mock()
        mock_tc.id = "call_empty"
        mock_tc.function.name = "test_tool"
        mock_tc.function.arguments = '{}'

        mock_message.tool_calls = [mock_tc]
        mock_response.choices = [Mock(message=mock_message, finish_reason="stop")]

        result = provider.convert_response_to_standard(mock_response)
        assert result.tool_calls[0].input == {}

    def test_complex_json_structure(self):
        """Test handling of complex nested JSON."""
        provider = OpenAIProvider(api_key="test-key")

        complex_json = json.dumps({
            "nested": {
                "array": [1, 2, 3],
                "object": {"key": "value"}
            },
            "string": "test",
            "number": 123,
            "boolean": True,
            "null": None
        })

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Response"

        mock_tc = Mock()
        mock_tc.id = "call_complex"
        mock_tc.function.name = "test_tool"
        mock_tc.function.arguments = complex_json

        mock_message.tool_calls = [mock_tc]
        mock_response.choices = [Mock(message=mock_message, finish_reason="stop")]

        result = provider.convert_response_to_standard(mock_response)
        assert result.tool_calls[0].input["nested"]["array"] == [1, 2, 3]

    def test_unicode_in_json(self):
        """Test handling of Unicode characters in JSON."""
        provider = OpenAIProvider(api_key="test-key")

        unicode_json = json.dumps({"text": "Hello 世界 🌍"})

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Response"

        mock_tc = Mock()
        mock_tc.id = "call_unicode"
        mock_tc.function.name = "test_tool"
        mock_tc.function.arguments = unicode_json

        mock_message.tool_calls = [mock_tc]
        mock_response.choices = [Mock(message=mock_message, finish_reason="stop")]

        result = provider.convert_response_to_standard(mock_response)
        assert result.tool_calls[0].input["text"] == "Hello 世界 🌍"

    def test_no_tool_calls(self):
        """Test response with no tool calls."""
        provider = OpenAIProvider(api_key="test-key")

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Just text response"
        mock_message.tool_calls = None
        mock_response.choices = [Mock(message=mock_message, finish_reason="stop")]

        result = provider.convert_response_to_standard(mock_response)
        assert len(result.tool_calls) == 0
        assert len(result.content) == 1
        assert result.content[0]["text"] == "Just text response"

    def test_multiple_tool_calls(self):
        """Test response with multiple tool calls."""
        provider = OpenAIProvider(api_key="test-key")

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Processing"

        mock_tc1 = Mock()
        mock_tc1.id = "call_1"
        mock_tc1.function.name = "tool1"
        mock_tc1.function.arguments = '{"param": "value1"}'

        mock_tc2 = Mock()
        mock_tc2.id = "call_2"
        mock_tc2.function.name = "tool2"
        mock_tc2.function.arguments = '{"param": "value2"}'

        mock_message.tool_calls = [mock_tc1, mock_tc2]
        mock_response.choices = [Mock(message=mock_message, finish_reason="stop")]

        result = provider.convert_response_to_standard(mock_response)
        assert len(result.tool_calls) == 2
        assert result.tool_calls[0].name == "tool1"
        assert result.tool_calls[1].name == "tool2"

    def test_convert_messages_preserves_tool_round_trip(self):
        """Test OpenAI-compatible history conversion for tool use follow-up turns."""
        provider = OpenAIProvider(api_key="test-key")

        messages = [
            {"role": "system", "content": "memory context"},
            {"role": "user", "content": "List files"},
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "I'll inspect the workspace."}],
                "tool_calls": [
                    ToolCall(
                        id="call_1",
                        name="bash",
                        input={"command": "ls"},
                    )
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "call_1", "content": "a.py"},
                    {"type": "text", "text": "<reminder>Update your todos.</reminder>"},
                ],
            },
        ]

        system_prompt, filtered = provider.split_system_messages(messages, "base system")
        formatted = provider.convert_messages_to_format(filtered)

        assert system_prompt == "base system\n\nmemory context"
        assert formatted[0]["role"] == "user"
        assert formatted[1]["role"] == "assistant"
        assert formatted[1]["tool_calls"][0]["function"]["arguments"] == '{"command": "ls"}'
        assert formatted[2] == {"role": "tool", "tool_call_id": "call_1", "content": "a.py"}
        assert formatted[3] == {"role": "user", "content": "<reminder>Update your todos.</reminder>"}


@pytest.mark.security
class TestGroqProviderSecurity:
    """Test Groq provider security aspects."""

    def test_json_parsing_not_eval(self):
        """Test that Groq also uses json.loads."""
        from simple_agent.providers.groq import GroqProvider

        provider = GroqProvider(api_key="test-key")

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Response"

        mock_tc = Mock()
        mock_tc.id = "call_123"
        mock_tc.function.name = "test_tool"
        mock_tc.function.arguments = '{"test": "value"}'

        mock_message.tool_calls = [mock_tc]
        mock_response.choices = [Mock(message=mock_message, finish_reason="stop")]

        result = provider.convert_response_to_standard(mock_response)
        assert result.tool_calls[0].input == {"test": "value"}


@pytest.mark.security
class TestLocalProviderSecurity:
    """Test Local provider security aspects."""

    def test_json_parsing_not_eval(self):
        """Test that Local provider also uses json.loads."""
        from simple_agent.providers.local import LocalProvider

        provider = LocalProvider(api_key="test-key")

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Response"

        mock_tc = Mock()
        mock_tc.id = "call_123"
        mock_tc.function.name = "test_tool"
        mock_tc.function.arguments = '{"test": "value"}'

        mock_message.tool_calls = [mock_tc]
        mock_response.choices = [Mock(message=mock_message, finish_reason="stop")]

        result = provider.convert_response_to_standard(mock_response)
        assert result.tool_calls[0].input == {"test": "value"}
