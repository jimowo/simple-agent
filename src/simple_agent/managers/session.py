"""Session manager for conversation persistence.

This module provides the SessionManager class that handles session
persistence, message storage, and session history, following
Claude Code's session management pattern.
"""

import json
import uuid
from pathlib import Path
from typing import Generator, List, Optional

from pydantic import ValidationError

from simple_agent.exceptions import (
    ProjectValidationError,
    SessionNotFoundError,
    SessionValidationError,
)
from simple_agent.managers.base import BaseManager
from simple_agent.models.config import Settings
from simple_agent.models.projects import (
    SessionMessage,
    SessionMetadata,
    SubagentMetadata,
)
from simple_agent.utils.path_utils import (
    get_legacy_session_messages_file,
    get_project_dir,
    get_session_dir,
    get_session_messages_file,
    get_session_metadata_file,
    get_session_subagents_dir,
)


class SessionManager(BaseManager):
    """Manager for session persistence and history.

    This class handles:
    - Creating and loading sessions
    - Storing session messages in jsonl format
    - Managing subagent metadata
    - Listing and querying sessions

    Attributes:
        settings: Application settings
        projects_root: Root directory for project data
        _current_session: Currently active session
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the session manager.

        Args:
            settings: Optional settings instance
        """
        super().__init__(settings)
        self.projects_root = self.settings.projects_root
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self._current_session: Optional[SessionMetadata] = None

    def create_session(
        self,
        project_id: str,
        parent_session_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> SessionMetadata:
        """Create a new session.

        Args:
            project_id: Project ID to create session under
            parent_session_id: Optional parent session ID for branching
            title: Optional session title

        Returns:
            SessionMetadata for the new session
        """
        session_id = str(uuid.uuid4())
        project_dir = get_project_dir(self.projects_root, project_id)
        project_dir.mkdir(exist_ok=True)

        session = SessionMetadata(
            session_id=session_id,
            project_id=project_id,
            parent_session_id=parent_session_id,
            title=title,
        )

        # Create session directory structure
        session_dir = get_session_dir(self.projects_root, project_id, session_id)
        session_dir.mkdir(exist_ok=True)
        get_session_subagents_dir(self.projects_root, project_id, session_id).mkdir(
            exist_ok=True
        )

        # Save session metadata
        self._save_session_metadata(project_dir, session)

        # Update project session count
        self._increment_project_session_count(project_dir)

        self._current_session = session
        return session

    def get_session(
        self,
        project_id: str,
        session_id: str,
    ) -> Optional[SessionMetadata]:
        """Get session metadata by ID.

        Args:
            project_id: Project ID
            session_id: Session ID

        Returns:
            SessionMetadata if found, None otherwise
        """
        session_file = get_session_metadata_file(
            self.projects_root, project_id, session_id
        )

        if not session_file.exists():
            return None

        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
            return SessionMetadata(**data)
        except (OSError, json.JSONDecodeError, ValidationError, ValueError):
            return None

    def get_session_or_raise(self, project_id: str, session_id: str) -> SessionMetadata:
        """Get session metadata by ID or raise a standardized exception."""
        session = self.get_session(project_id, session_id)
        if session is None:
            raise SessionNotFoundError(session_id, project_id=project_id)
        return session

    def append_message(
        self,
        project_id: str,
        session_id: str,
        message: SessionMessage,
    ) -> None:
        """Append a message to a session.

        Args:
            project_id: Project ID
            session_id: Session ID
            message: Message to append
        """
        session_file = self._ensure_session_messages_file(project_id, session_id)

        # Append message to jsonl file
        with open(session_file, "a", encoding="utf-8") as f:
            f.write(message.model_dump_json(exclude_none=True) + "\n")

        # Update session metadata
        session = self.get_session_or_raise(project_id, session_id)
        session.message_count += 1
        session.last_updated = session.last_updated.now()
        project_dir = get_project_dir(self.projects_root, project_id)
        self._save_session_metadata(project_dir, session)

        # Update current session if it's the same
        if self._current_session and self._current_session.session_id == session_id:
            self._current_session = session

    def read_messages(
        self,
        project_id: str,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[SessionMessage]:
        """Read messages from a session.

        Args:
            project_id: Project ID
            session_id: Session ID
            limit: Optional maximum number of messages to return

        Returns:
            List of SessionMessage instances
        """
        session_file = self._resolve_session_messages_file(project_id, session_id)

        if not session_file.exists():
            return []

        messages = []
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        msg = SessionMessage.model_validate_json(line)
                        messages.append(msg)
                    except ValueError:
                        # Skip invalid messages
                        continue

        if limit:
            return messages[-limit:]

        return messages

    def stream_messages(
        self,
        project_id: str,
        session_id: str,
    ) -> Generator[SessionMessage, None, None]:
        """Stream messages from a session (memory-efficient).

        Args:
            project_id: Project ID
            session_id: Session ID

        Yields:
            SessionMessage instances one at a time
        """
        session_file = self._resolve_session_messages_file(project_id, session_id)

        if not session_file.exists():
            return

        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        yield SessionMessage.model_validate_json(line)
                    except ValueError:
                        # Skip invalid messages
                        continue

    def save_subagent(
        self,
        project_id: str,
        session_id: str,
        agent_id: str,
        metadata: SubagentMetadata,
    ) -> None:
        """Save subagent metadata.

        Args:
            project_id: Project ID
            session_id: Session ID
            agent_id: Subagent ID
            metadata: Subagent metadata to save
        """
        subagent_file = (
            get_session_subagents_dir(self.projects_root, project_id, session_id)
            / f"agent-{agent_id}.meta.json"
        )

        subagent_file.parent.mkdir(parents=True, exist_ok=True)
        subagent_file.write_text(
            metadata.model_dump_json(exclude_none=True, indent=2),
            encoding="utf-8",
        )

    def list_sessions(
        self,
        project_id: str,
        include_archived: bool = False,
        limit: Optional[int] = None,
    ) -> List[SessionMetadata]:
        """List sessions for a project.

        Args:
            project_id: Project ID
            include_archived: Whether to include archived sessions
            limit: Optional maximum number of sessions to return

        Returns:
            List of SessionMetadata instances
        """
        project_dir = get_project_dir(self.projects_root, project_id)

        if not project_dir.exists():
            return []

        sessions = []

        for session_dir in project_dir.glob("*/"):
            if not session_dir.is_dir():
                continue

            session_file = session_dir / "session.json"
            if session_file.exists():
                try:
                    data = json.loads(session_file.read_text(encoding="utf-8"))
                    session = SessionMetadata(**data)

                    if include_archived or session.status == "active":
                        sessions.append(session)
                except (json.JSONDecodeError, ValueError):
                    # Skip corrupted session files
                    continue

        # Sort by created_at descending
        sessions.sort(key=lambda s: s.created_at, reverse=True)

        if limit:
            return sessions[:limit]

        return sessions

    def archive_session(
        self,
        project_id: str,
        session_id: str,
    ) -> SessionMetadata:
        """Archive a session.

        Args:
            project_id: Project ID
            session_id: Session ID to archive

        Returns:
            Updated SessionMetadata
        """
        session = self.get_session_or_raise(project_id, session_id)

        session.status = "archived"
        project_dir = get_project_dir(self.projects_root, project_id)
        self._save_session_metadata(project_dir, session)

        return session

    def get_current_session(self) -> Optional[SessionMetadata]:
        """Get the currently active session.

        Returns:
            Current SessionMetadata or None if no session is active
        """
        return self._current_session

    def set_current_session(self, session: SessionMetadata) -> None:
        """Set the currently active session.

        Args:
            session: Session to set as current
        """
        self._current_session = session

    def _save_session_metadata(
        self,
        project_dir: Path,
        session: SessionMetadata,
    ) -> None:
        """Save session metadata to file.

        Args:
            project_dir: Project directory path
            session: Session to save
        """
        session_file = get_session_metadata_file(
            self.projects_root, session.project_id, session.session_id
        )
        try:
            session_file.write_text(
                session.model_dump_json(exclude_none=True, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise SessionValidationError(
                f"Failed to save session metadata: {exc}",
                session_id=session.session_id,
            ) from exc

    def _increment_project_session_count(self, project_dir: Path) -> None:
        """Increment the session count for a project.

        Args:
            project_dir: Project directory path
        """
        metadata_file = project_dir / "project.json"
        if metadata_file.exists():
            try:
                data = json.loads(metadata_file.read_text(encoding="utf-8"))
                data["session_count"] = data.get("session_count", 0) + 1
                metadata_file.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except OSError as exc:
                raise ProjectValidationError(
                    f"Failed to update project session count: {exc}"
                ) from exc
            except (json.JSONDecodeError, ValueError):
                # Skip if metadata is corrupted
                pass

    def _resolve_session_messages_file(self, project_id: str, session_id: str) -> Path:
        """Resolve the canonical or legacy session messages file."""
        canonical = get_session_messages_file(self.projects_root, project_id, session_id)
        if canonical.exists():
            return canonical

        legacy = get_legacy_session_messages_file(self.projects_root, project_id, session_id)
        if legacy.exists():
            return legacy

        return canonical

    def _ensure_session_messages_file(self, project_id: str, session_id: str) -> Path:
        """Ensure the canonical messages file exists, migrating legacy data if needed."""
        canonical = get_session_messages_file(self.projects_root, project_id, session_id)
        try:
            canonical.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise SessionValidationError(
                f"Failed to create session messages directory: {exc}",
                session_id=session_id,
            ) from exc

        legacy = get_legacy_session_messages_file(self.projects_root, project_id, session_id)
        if legacy.exists() and not canonical.exists():
            try:
                canonical.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
                legacy.unlink()
            except OSError as exc:
                raise SessionValidationError(
                    f"Failed to migrate legacy session messages: {exc}",
                    session_id=session_id,
                ) from exc

        return canonical
