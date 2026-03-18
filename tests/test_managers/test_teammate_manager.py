"""Tests for TeammateManager exception handling."""

from types import SimpleNamespace

import pytest

from simple_agent.exceptions import TeammateError
from simple_agent.managers.teammate import TeammateManager


class TestTeammateManagerExceptions:
    """Test standardized teammate exceptions."""

    def test_spawn_busy_teammate_raises_error(self, mock_settings):
        """Spawning an already-busy teammate should raise TeammateError."""
        manager = TeammateManager(
            bus=SimpleNamespace(send=lambda *args, **kwargs: "", read_inbox=lambda *args, **kwargs: []),
            task_mgr=SimpleNamespace(claim=lambda *args, **kwargs: ""),
            settings=mock_settings,
            provider_factory=lambda settings: object(),
        )
        manager.config["members"] = [{"name": "alice", "role": "dev", "status": "working"}]

        with pytest.raises(TeammateError):
            manager.spawn("alice", "dev", "work on task")

    def test_unknown_tool_is_formatted_consistently(self, mock_settings):
        """Unknown teammate tools should be formatted through the shared error formatter."""
        manager = TeammateManager(
            bus=SimpleNamespace(send=lambda *args, **kwargs: "", read_inbox=lambda *args, **kwargs: []),
            task_mgr=SimpleNamespace(claim=lambda *args, **kwargs: ""),
            settings=mock_settings,
            provider_factory=lambda settings: object(),
        )
        tool_call = SimpleNamespace(name="missing_tool", input={}, id="call_1")
        call_count = {"value": 0}

        def create_message(**kwargs):
            call_count["value"] += 1
            if call_count["value"] == 1:
                return SimpleNamespace(
                    content=[{"type": "text", "text": "need tool"}],
                    stop_reason="tool_use",
                    tool_calls=[tool_call],
                )
            return SimpleNamespace(
                content=[{"type": "text", "text": "done"}],
                stop_reason="stop",
                tool_calls=[],
            )

        provider = SimpleNamespace(create_message=create_message)

        messages = [{"role": "user", "content": "hi"}]
        should_idle = manager._work_phase("alice", "dev", "team", messages, [], provider)

        assert should_idle is False
        assert "Tool 'missing_tool' not found" in str(messages[-2]["content"][0]["content"])
