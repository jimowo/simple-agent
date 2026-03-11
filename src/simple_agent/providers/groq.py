"""Groq provider implementation (fast inference)."""

from simple_agent.providers.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    """Groq API provider - fast inference for various models."""

    DEFAULT_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    def __init__(self, **kwargs):
        """Initialize Groq provider.

        Args:
            **kwargs: Arguments passed to parent class
        """
        super().__init__(**kwargs)
        if self.model is None:
            self.model = self.DEFAULT_MODELS[0]

    def create_client(self):
        """Create Groq client.

        Returns:
            Groq client instance
        """
        from groq import Groq

        return Groq(api_key=self.api_key, base_url=self.base_url)
