"""
Multi-provider AI support for simple-agent.

Supports:
- Anthropic (Claude)
- OpenAI (GPT-4o, o1, o3)
- Google Gemini (2.0, 2.5 Flash)
- Groq (fast inference)
- Local models (Ollama, vLLM)
"""

from simple_agent.providers.anthropic import AnthropicProvider
from simple_agent.providers.base import BaseProvider, ProviderFactory
from simple_agent.providers.gemini import GeminiProvider
from simple_agent.providers.groq import GroqProvider
from simple_agent.providers.local import LocalProvider
from simple_agent.providers.openai import OpenAIProvider

__all__ = [
    "BaseProvider",
    "ProviderFactory",
    "AnthropicProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "GroqProvider",
    "LocalProvider",
]
