"""OpenAI Embeddings encoder for memory system.

This module provides the OpenAI-based encoder that converts text
to vector embeddings using OpenAI's embeddings API.
"""

from typing import List, Optional

from loguru import logger


class OpenAIEmbeddingEncoder:
    """OpenAI Embeddings API encoder.

    This encoder uses OpenAI's text-embedding models to convert
    text to vector embeddings for semantic search.

    Attributes:
        client: OpenAI client instance
        model: Model name to use for embeddings
        api_key: API key for OpenAI
        base_url: Optional base URL for API requests
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "text-embedding-3-small"
    ):
        """Initialize the OpenAI encoder.

        Args:
            api_key: OpenAI API key
            base_url: Optional base URL (for custom endpoints)
            model: Model name to use (default: text-embedding-3-small)
        """
        from openai import OpenAI

        self.api_key = api_key
        self.base_url = base_url
        self.model = model

        # Create OpenAI client
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = OpenAI(**client_kwargs)

        logger.debug(
            f"[OpenAIEncoder] Initialized with model={model}, "
            f"base_url={base_url or 'default'}"
        )

    def encode(self, text: str) -> List[float]:
        """Encode a single text to vector embedding.

        Args:
            text: Text to encode

        Returns:
            Vector embedding as list of floats
        """
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            embedding = response.data[0].embedding
            logger.debug(f"[OpenAIEncoder] Encoded text (length={len(text)}) -> {len(embedding)}d")
            return embedding
        except Exception as e:
            logger.error(f"[OpenAIEncoder] Failed to encode text: {e}")
            raise

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts to vector embeddings.

        Args:
            texts: List of texts to encode

        Returns:
            List of vector embeddings
        """
        if not texts:
            return []

        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            embeddings = [item.embedding for item in response.data]
            logger.debug(
                f"[OpenAIEncoder] Encoded batch ({len(texts)} texts) -> "
                f"{len(embeddings)} embeddings"
            )
            return embeddings
        except Exception as e:
            logger.error(f"[OpenAIEncoder] Failed to encode batch: {e}")
            raise

    def __repr__(self) -> str:
        """String representation of the encoder."""
        return f"OpenAIEmbeddingEncoder(model={self.model}, base_url={self.base_url})"


__all__ = ["OpenAIEmbeddingEncoder"]
