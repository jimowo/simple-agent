"""OpenAI provider implementation."""

from simple_agent.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI API provider (GPT-4o, o1, o3, etc.)."""

    DEFAULT_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "o1",
        "o1-mini",
        "o3-mini",
    ]

    def __init__(self, **kwargs):
        """Initialize OpenAI provider.

        Args:
            **kwargs: Arguments passed to parent class
        """
        super().__init__(**kwargs)
        if self.model is None:
            self.model = self.DEFAULT_MODELS[0]

    def create_client(self):
        """Create OpenAI client.

        Returns:
            OpenAI client instance
        """
        from openai import OpenAI

        return OpenAI(api_key=self.api_key, base_url=self.base_url)
