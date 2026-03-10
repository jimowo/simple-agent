"""Manager interface definitions using Protocol.

These interfaces define the contracts that manager implementations must follow,
following the Dependency Inversion Principle (DIP) of SOLID.
"""

from typing import Any, Dict, List, Optional, Protocol


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
