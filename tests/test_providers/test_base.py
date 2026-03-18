"""Tests for provider base exception handling."""

import pytest

from simple_agent.exceptions import InvalidProviderError, ProviderResponseError
from simple_agent.providers.base import BaseProvider, ProviderFactory


class DummyProvider(BaseProvider):
    """Minimal provider for testing base behavior."""

    def create_client(self):
        return object()

    def create_message(self, messages, tools, system=None, max_tokens=8000, **kwargs):
        raise NotImplementedError


class TestProviderBaseExceptions:
    """Test standardized provider exceptions."""

    def test_convert_response_to_standard_raises_provider_response_error(self):
        """Base implementation should raise ProviderResponseError."""
        provider = DummyProvider(api_key="test-key")

        with pytest.raises(ProviderResponseError):
            provider.convert_response_to_standard(object())

    def test_provider_factory_unknown_provider_raises_invalid_provider(self):
        """Unknown providers should raise InvalidProviderError."""
        with pytest.raises(InvalidProviderError):
            ProviderFactory.create("missing-provider", api_key="test-key")
