"""Tests for session storage layout and migration behavior."""

from simple_agent.managers.project import ProjectManager
from simple_agent.managers.session import SessionManager
from simple_agent.models.projects import SessionMessage
from simple_agent.utils.path_utils import (
    get_legacy_session_messages_file,
    get_session_messages_file,
)


class TestSessionManagerStorage:
    """Test canonical session storage layout."""

    def test_append_message_writes_into_session_directory(self, mock_settings):
        """Messages should be stored under the session directory."""
        project_mgr = ProjectManager(mock_settings)
        session_mgr = SessionManager(mock_settings)

        project = project_mgr.get_or_create_project(mock_settings.workdir)
        session = session_mgr.create_session(project.project_id, title="Test")

        session_mgr.append_message(
            project.project_id,
            session.session_id,
            SessionMessage(role="user", content="hello", timestamp=1.0),
        )

        canonical_file = get_session_messages_file(
            mock_settings.projects_root,
            project.project_id,
            session.session_id,
        )
        assert canonical_file.exists()
        assert "hello" in canonical_file.read_text(encoding="utf-8")

    def test_append_message_migrates_legacy_flat_jsonl(self, mock_settings):
        """Legacy flat jsonl files should be moved into the session directory."""
        project_mgr = ProjectManager(mock_settings)
        session_mgr = SessionManager(mock_settings)

        project = project_mgr.get_or_create_project(mock_settings.workdir)
        session = session_mgr.create_session(project.project_id, title="Legacy")

        legacy_file = get_legacy_session_messages_file(
            mock_settings.projects_root,
            project.project_id,
            session.session_id,
        )
        legacy_file.write_text('{"role":"user","content":"old","timestamp":1.0}\n', encoding="utf-8")

        session_mgr.append_message(
            project.project_id,
            session.session_id,
            SessionMessage(role="assistant", content="new", timestamp=2.0),
        )

        canonical_file = get_session_messages_file(
            mock_settings.projects_root,
            project.project_id,
            session.session_id,
        )
        assert canonical_file.exists()
        content = canonical_file.read_text(encoding="utf-8")
        assert '"content":"old"' in content
        assert '"content":"new"' in content
        assert not legacy_file.exists()
