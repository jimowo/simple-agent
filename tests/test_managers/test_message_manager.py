"""Tests for MessageBus exception handling."""

import pytest

from simple_agent.exceptions import MessageBusError
from simple_agent.managers.message import MessageBus


class TestMessageBusExceptions:
    """Test standardized message bus exceptions."""

    def test_invalid_message_type_raises_error(self, mock_settings):
        """Invalid message types should raise MessageBusError."""
        bus = MessageBus(mock_settings)

        with pytest.raises(MessageBusError):
            bus.send("lead", "worker", "hello", "invalid-type")
