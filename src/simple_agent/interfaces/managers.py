"""Manager interface definitions using Protocol.

These interfaces define the contracts that manager implementations must follow,
following the Dependency Inversion Principle (DIP) of SOLID.
"""

from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Protocol


class TodoManager(Protocol):
    """Interface for todo list management."""

    def update(self, items: List[Dict[str, Any]]) -> str:
        """Update todo list with new items.

        Args:
            items: List of todo items with content, status, and activeForm

        Returns:
            Confirmation message
        """
        ...

    def render(self) -> str:
        """Render todo list as string.

        Returns:
            Formatted todo list string
        """
        ...


class TaskManager(Protocol):
    """Interface for persistent task management."""

    def create(self, subject: str, description: str = "") -> str:
        """Create a new task.

        Args:
            subject: Task subject/title
            description: Optional description

        Returns:
            JSON string of created task
        """
        ...

    def get(self, tid: int) -> str:
        """Get task by ID.

        Args:
            tid: Task ID

        Returns:
            JSON string of task
        """
        ...

    def update(
        self,
        tid: int,
        status: Optional[str] = None,
        add_blocked_by: Optional[List[int]] = None,
        add_blocks: Optional[List[int]] = None,
    ) -> str:
        """Update task.

        Args:
            tid: Task ID
            status: New status (pending, in_progress, completed, deleted)
            add_blocked_by: List of task IDs this task is blocked by
            add_blocks: List of task IDs this task blocks

        Returns:
            JSON string of updated task
        """
        ...

    def list_all(self) -> str:
        """List all tasks.

        Returns:
            Formatted task list string
        """
        ...

    def claim(self, tid: int, owner: str) -> str:
        """Claim a task.

        Args:
            tid: Task ID
            owner: Owner name

        Returns:
            Confirmation message
        """
        ...


class BackgroundManager(Protocol):
    """Interface for background task execution."""

    def run(self, command: str, timeout: int = 120) -> str:
        """Run command in background.

        Args:
            command: Shell command to run
            timeout: Timeout in seconds

        Returns:
            Task ID and status message
        """
        ...

    def check(self, tid: Optional[str] = None) -> str:
        """Check background task status.

        Args:
            tid: Optional task ID. If None, checks all tasks.

        Returns:
            Task status information
        """
        ...

    def drain(self) -> List[Dict[str, Any]]:
        """Drain notification queue.

        Returns:
            List of notification dictionaries
        """
        ...


class MessageBus(Protocol):
    """Interface for inter-agent messaging."""

    def send(
        self,
        sender: str,
        to: str,
        content: str,
        msg_type: str = "message",
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send message to an agent.

        Args:
            sender: Sender name
            to: Recipient name
            content: Message content
            msg_type: Message type
            extra: Optional extra data

        Returns:
            Confirmation message
        """
        ...

    def read_inbox(self, name: str) -> List[Dict[str, Any]]:
        """Read and drain inbox for an agent.

        Args:
            name: Agent name

        Returns:
            List of messages
        """
        ...

    def broadcast(self, sender: str, content: str, names: List[str]) -> str:
        """Broadcast message to multiple agents.

        Args:
            sender: Sender name
            content: Message content
            names: List of recipient names

        Returns:
            Confirmation message with count
        """
        ...


class SkillLoader(Protocol):
    """Interface for skill loading."""

    def load(self, name: str) -> str:
        """Load a skill by name.

        Args:
            name: Skill name

        Returns:
            Skill content
        """
        ...

    def descriptions(self) -> str:
        """Get descriptions of all available skills.

        Returns:
            Formatted skill descriptions
        """
        ...


class TeammateManager(Protocol):
    """Interface for teammate management."""

    def spawn(self, name: str, role: str, prompt: str) -> str:
        """Spawn a new teammate.

        Args:
            name: Teammate name
            role: Teammate role
            prompt: System prompt

        Returns:
            Confirmation message
        """
        ...

    def list_all(self) -> str:
        """List all teammates.

        Returns:
            Formatted teammate list
        """
        ...

    def member_names(self) -> List[str]:
        """Get list of teammate names.

        Returns:
            List of names
        """
        ...


# Note: The following are placeholder type hints for the actual model classes
# These are used in the Protocol definitions below to avoid circular imports
class _ProjectMetadata(Protocol):
    """Placeholder for ProjectMetadata model."""
    project_id: str
    original_path: str
    session_count: int


class _SessionMetadata(Protocol):
    """Placeholder for SessionMetadata model."""
    session_id: str
    project_id: str
    message_count: int
    status: str


class _SessionMessage(Protocol):
    """Placeholder for SessionMessage model."""
    role: str
    content: str
    timestamp: float


class _SubagentMetadata(Protocol):
    """Placeholder for SubagentMetadata model."""
    agent_id: str
    session_id: str
    agent_type: str


class ProjectManager(Protocol):
    """Interface for project management."""

    def get_or_create_project(self, workdir: Path) -> "_ProjectMetadata":
        """Get an existing project or create a new one.

        Args:
            workdir: Working directory path for the project

        Returns:
            ProjectMetadata instance
        """
        ...

    def get_project(self, project_id: str) -> "Optional[_ProjectMetadata]":
        """Get a project by ID.

        Args:
            project_id: Project ID to retrieve

        Returns:
            ProjectMetadata if found, None otherwise
        """
        ...

    def list_projects(self, limit: "Optional[int]" = None) -> "List[_ProjectMetadata]":
        """List all projects.

        Args:
            limit: Optional maximum number of projects to return

        Returns:
            List of ProjectMetadata instances
        """
        ...

    def get_current_project(self) -> "Optional[_ProjectMetadata]":
        """Get the currently active project.

        Returns:
            Current ProjectMetadata or None
        """
        ...

    def set_current_project(self, project: "_ProjectMetadata") -> None:
        """Set the currently active project.

        Args:
            project: Project to set as current
        """
        ...


class SessionManager(Protocol):
    """Interface for session management."""

    def create_session(
        self,
        project_id: str,
        parent_session_id: "Optional[str]" = None,
        title: "Optional[str]" = None,
    ) -> "_SessionMetadata":
        """Create a new session.

        Args:
            project_id: Project ID to create session under
            parent_session_id: Optional parent session ID for branching
            title: Optional session title

        Returns:
            SessionMetadata for the new session
        """
        ...

    def get_session(
        self,
        project_id: str,
        session_id: str,
    ) -> "Optional[_SessionMetadata]":
        """Get session metadata by ID.

        Args:
            project_id: Project ID
            session_id: Session ID

        Returns:
            SessionMetadata if found, None otherwise
        """
        ...

    def append_message(
        self,
        project_id: str,
        session_id: str,
        message: "_SessionMessage",
    ) -> None:
        """Append a message to a session.

        Args:
            project_id: Project ID
            session_id: Session ID
            message: Message to append
        """
        ...

    def read_messages(
        self,
        project_id: str,
        session_id: str,
        limit: "Optional[int]" = None,
    ) -> "List[_SessionMessage]":
        """Read messages from a session.

        Args:
            project_id: Project ID
            session_id: Session ID
            limit: Optional maximum number of messages to return

        Returns:
            List of SessionMessage instances
        """
        ...

    def stream_messages(
        self,
        project_id: str,
        session_id: str,
    ) -> "Generator[_SessionMessage, None, None]":
        """Stream messages from a session (memory-efficient).

        Args:
            project_id: Project ID
            session_id: Session ID

        Yields:
            SessionMessage instances one at a time
        """
        ...

    def save_subagent(
        self,
        project_id: str,
        session_id: str,
        agent_id: str,
        metadata: "_SubagentMetadata",
    ) -> None:
        """Save subagent metadata.

        Args:
            project_id: Project ID
            session_id: Session ID
            agent_id: Subagent ID
            metadata: Subagent metadata to save
        """
        ...

    def list_sessions(
        self,
        project_id: str,
        include_archived: bool = False,
        limit: "Optional[int]" = None,
    ) -> "List[_SessionMetadata]":
        """List sessions for a project.

        Args:
            project_id: Project ID
            include_archived: Whether to include archived sessions
            limit: Optional maximum number of sessions to return

        Returns:
            List of SessionMetadata instances
        """
        ...

    def archive_session(
        self,
        project_id: str,
        session_id: str,
    ) -> "Optional[_SessionMetadata]":
        """Archive a session.

        Args:
            project_id: Project ID
            session_id: Session ID to archive

        Returns:
            Updated SessionMetadata or None if session not found
        """
        ...

    def get_current_session(self) -> "Optional[_SessionMetadata]":
        """Get the currently active session.

        Returns:
            Current SessionMetadata or None
        """
        ...

    def set_current_session(self, session: "_SessionMetadata") -> None:
        """Set the currently active session.

        Args:
            session: Session to set as current
        """
        ...


# Memory system placeholder types
class _MemoryMetadata(Protocol):
    """Placeholder for MemoryMetadata model."""
    entry_id: str
    entry_type: str
    importance: str
    confidence: float
    embedding: "Optional[List[float]]"
    version: int


class _MemoryEntry(Protocol):
    """Placeholder for MemoryEntry model."""
    content: str
    metadata: "_MemoryMetadata"


class _MemoryQuery(Protocol):
    """Placeholder for MemoryQuery model."""
    query_text: str
    limit: int
    threshold: float


class _MemoryResult(Protocol):
    """Placeholder for MemoryResult model."""
    entries: "List[_MemoryEntry]"
    total_found: int


class MemoryEncoder(Protocol):
    """Interface for encoding text to vector embeddings."""

    def encode(self, text: str) -> "List[float]":
        """Encode text to vector embedding.

        Args:
            text: Text to encode

        Returns:
            Vector embedding as list of floats
        """
        ...

    def encode_batch(self, texts: "List[str]") -> "List[List[float]]":
        """Encode multiple texts to vector embeddings.

        Args:
            texts: List of texts to encode

        Returns:
            List of vector embeddings
        """
        ...


class MemoryBackend(Protocol):
    """Interface for memory storage backends."""

    def store(self, entry: "_MemoryEntry") -> bool:
        """Store a memory entry.

        Args:
            entry: Entry to store

        Returns:
            True if successful
        """
        ...

    def load(self, entry_id: str) -> "Optional[_MemoryEntry]":
        """Load a memory entry by ID.

        Args:
            entry_id: Entry ID to load

        Returns:
            MemoryEntry if found, None otherwise
        """
        ...

    def search(
        self,
        query_vector: "List[float]",
        limit: int,
        threshold: float
    ) -> "List[_MemoryEntry]":
        """Search for similar entries by vector.

        Args:
            query_vector: Query embedding vector
            limit: Maximum results
            threshold: Minimum similarity threshold

        Returns:
            List of similar MemoryEntry instances
        """
        ...

    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: Entry ID to delete

        Returns:
            True if deleted
        """
        ...


class MemoryManager(Protocol):
    """Interface for memory management and retrieval.

    This interface matches the IMemory abstract class from
    simple_agent.managers.memory.
    """

    def write(
        self,
        content: str,
        entry_type: str,
        **kwargs
    ) -> "_MemoryEntry":
        """Write a new memory entry.

        Args:
            content: Memory content
            entry_type: Type of memory (episodic, semantic, procedural)
            **kwargs: Additional metadata fields

        Returns:
            Created MemoryEntry
        """
        ...

    def retrieve(self, query: "_MemoryQuery") -> "_MemoryResult":
        """Retrieve relevant memories based on query.

        Args:
            query: Memory query with search parameters

        Returns:
            MemoryResult with matching entries
        """
        ...

    def update(
        self,
        entry_id: str,
        content: "Optional[str]" = None,
        **metadata_updates
    ) -> "Optional[_MemoryEntry]":
        """Update an existing memory entry.

        Handles conflict resolution based on version/timestamp.

        Args:
            entry_id: ID of entry to update
            content: New content (if None, keeps existing)
            **metadata_updates: Metadata fields to update

        Returns:
            Updated MemoryEntry or None if not found
        """
        ...

    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: ID of entry to delete

        Returns:
            True if deleted, False if not found
        """
        ...

    def forget(self, policy: "Dict[str, Any]") -> int:
        """Apply forgetting policy to clean up old/unimportant memories.

        Args:
            policy: Forgetting policy configuration

        Returns:
            Number of entries deleted
        """
        ...

    def get_entry(self, entry_id: str) -> "Optional[_MemoryEntry]":
        """Get a specific memory entry by ID.

        Args:
            entry_id: Entry ID to retrieve

        Returns:
            MemoryEntry if found, None otherwise
        """
        ...

    def list_entries(
        self,
        project_id: "Optional[str]" = None,
        entry_type: "Optional[str]" = None,
        limit: "Optional[int]" = None,
    ) -> "List[_MemoryEntry]":
        """List memory entries with optional filters.

        Args:
            project_id: Filter by project ID
            entry_type: Filter by entry type
            limit: Maximum number of entries to return

        Returns:
            List of MemoryEntry instances
        """
        ...

    def clear(self) -> int:
        """Clear all memory entries.

        Returns:
            Number of entries cleared
        """
        ...

    def count(self) -> int:
        """Get total number of memory entries.

        Returns:
            Total count of entries
        """
        ...

    def get_info(self) -> "Dict[str, Any]":
        """Get memory system information.

        Returns:
            Dictionary with memory system info (type, backend, config, etc.)
        """
        ...
