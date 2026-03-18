"""Tests for memory factory exception handling."""

import pytest

from simple_agent.exceptions import ConfigurationError
from simple_agent.managers.encoders import MemoryEncoderFactory
from simple_agent.managers.memory.factory import MemoryFactory


class TestMemoryFactories:
    """Test standardized memory factory exceptions."""

    def test_unknown_memory_encoder_raises_configuration_error(self, mock_settings):
        """Unknown encoders should raise ConfigurationError."""
        mock_settings.memory_enabled = True
        mock_settings.memory_encoder = "missing-encoder"

        with pytest.raises(ConfigurationError):
            MemoryEncoderFactory.create(mock_settings)

    def test_unknown_memory_type_raises_configuration_error(self, mock_settings):
        """Unknown memory backends should raise ConfigurationError."""
        mock_settings.memory_enabled = True
        mock_settings.memory_backend = "missing-memory"

        with pytest.raises(ConfigurationError):
            MemoryFactory.create(mock_settings, encoder=None)
