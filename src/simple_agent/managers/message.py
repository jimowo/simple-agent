"""Message bus for inter-agent communication."""

import json
import time

from simple_agent.models.config import Settings


class MessageBus:
    """Message bus for agent communication."""

    VALID_MSG_TYPES = {
        "message",
        "broadcast",
        "shutdown_request",
        "shutdown_response",
        "plan_approval_response",
    }

    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.inbox_dir = self.settings.inbox_dir
        self.inbox_dir.mkdir(parents=True, exist_ok=True)

    def send(
        self, sender: str, to: str, content: str, msg_type: str = "message", extra: dict = None
    ) -> str:
        """Send a message to a specific agent."""
        msg = {
            "type": msg_type,
            "from": sender,
            "content": content,
            "timestamp": time.time(),
        }
        if extra:
            msg.update(extra)
        with open(self.inbox_dir / f"{to}.jsonl", "a") as f:
            f.write(json.dumps(msg) + "\n")
        return f"Sent {msg_type} to {to}"

    def read_inbox(self, name: str) -> list:
        """Read and drain inbox for an agent."""
        path = self.inbox_dir / f"{name}.jsonl"
        if not path.exists():
            return []
        msgs = [json.loads(line) for line in path.read_text().strip().splitlines() if line]
        path.write_text("")
        return msgs

    def broadcast(self, sender: str, content: str, names: list) -> str:
        """Broadcast message to all agents."""
        count = 0
        for n in names:
            if n != sender:
                self.send(sender, n, content, "broadcast")
                count += 1
        return f"Broadcast to {count} teammates"
