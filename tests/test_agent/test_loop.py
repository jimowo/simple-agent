"""Tests for AgentLoop behavior."""

from types import SimpleNamespace
from unittest.mock import Mock

from simple_agent.agent.loop import AgentLoop


class TestAgentLoopMemoryInjection:
    """Test memory retrieval and injection edge cases."""

    def test_memory_retrieval_uses_last_real_user_message(self, initialized_context):
        """Synthetic inbox/background messages should not drive memory lookup."""
        memory_mgr = Mock()
        memory_mgr.retrieve.return_value = SimpleNamespace(
            entries=[SimpleNamespace(content="Relevant fact")]
        )
        initialized_context.memory_mgr = memory_mgr
        initialized_context.session_mgr.set_current_session(
            SimpleNamespace(project_id="project-123", session_id="session-123")
        )

        loop = AgentLoop(initialized_context)
        messages = [
            {"role": "user", "content": "How do we fix the build pipeline regression?"},
            {"role": "assistant", "content": "Checking inbox."},
            {"role": "user", "content": "<inbox>noise</inbox>"},
        ]

        loop._retrieve_and_inject_memory(messages)

        query = memory_mgr.retrieve.call_args[0][0]
        assert query.query_text == "How do we fix the build pipeline regression?"
        assert messages[0]["role"] == "system"
        assert "Relevant fact" in messages[0]["content"]
        assert messages[1]["content"] == "How do we fix the build pipeline regression?"

    def test_find_last_real_user_message_skips_synthetic_notifications(self, initialized_context):
        """Synthetic user-role wrappers should be ignored when locating user input."""
        loop = AgentLoop(initialized_context)
        messages = [
            {"role": "user", "content": "Need a code review of the parser."},
            {"role": "user", "content": "<background-results>done</background-results>"},
            {"role": "user", "content": "<inbox>queued</inbox>"},
        ]

        assert loop._find_last_real_user_message_index(messages) == 0
