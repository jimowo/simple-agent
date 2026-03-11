"""Local model provider implementation (Ollama, vLLM)."""

from simple_agent.providers.openai_compatible import OpenAICompatibleProvider


class LocalProvider(OpenAICompatibleProvider):
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
        """Initialize local provider.

        Args:
            **kwargs: Arguments passed to parent class
        """
        super().__init__(**kwargs)
        if self.base_url is None:
            self.base_url = self.DEFAULT_BASE_URL
        if self.model is None:
            self.model = self.DEFAULT_MODELS[0]
        # Local models typically don't need API key
        if self.api_key == "dummy":
            self.api_key = "ollama"

    def create_client(self):
        """Create OpenAI-compatible client for local models.

        Returns:
            OpenAI-compatible client instance
        """
        from openai import OpenAI

        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def create_message(self, *args, **kwargs):
        """Create a message using local model API with helpful error handling.

        Returns:
            ProviderResponse with standardized format

        Raises:
            ConnectionError: If cannot connect to local model server
        """
        try:
            return super().create_message(*args, **kwargs)
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
