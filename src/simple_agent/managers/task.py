"""File-based task manager."""

import json

from simple_agent.managers.base import BaseManager


class TaskManager(BaseManager):
    """Manager for persistent file-based tasks."""

    def __init__(self, settings=None):
        """Initialize the task manager.

        Args:
            settings: Optional Settings instance
        """
        super().__init__(settings)
        self.tasks_dir = self._ensure_dir(self.settings.tasks_dir)

    def _next_id(self) -> int:
        """Get next available task ID."""
        ids = [int(f.stem.split("_")[1]) for f in self.tasks_dir.glob("task_*.json")]
        return max(ids, default=0) + 1

    def _load(self, tid: int) -> dict:
        """Load task by ID."""
        p = self.tasks_dir / f"task_{tid}.json"
        if not p.exists():
            raise ValueError(f"Task {tid} not found")
        return json.loads(p.read_text())

    def _save(self, task: dict):
        """Save task to file."""
        (self.tasks_dir / f"task_{task['id']}.json").write_text(json.dumps(task, indent=2))

    def create(self, subject: str, description: str = "") -> str:
        """Create a new task."""
        task = {
            "id": self._next_id(),
            "subject": subject,
            "description": description,
            "status": "pending",
            "owner": None,
            "blockedBy": [],
            "blocks": [],
        }
        self._save(task)
        return json.dumps(task, indent=2)

    def get(self, tid: int) -> str:
        """Get task by ID."""
        return json.dumps(self._load(tid), indent=2)

    def update(
        self, tid: int, status: str = None, add_blocked_by: list = None, add_blocks: list = None
    ) -> str:
        """Update task."""
        task = self._load(tid)
        if status:
            task["status"] = status
            if status == "completed":
                for f in self.tasks_dir.glob("task_*.json"):
                    t = json.loads(f.read_text())
                    if tid in t.get("blockedBy", []):
                        t["blockedBy"].remove(tid)
                        self._save(t)
            if status == "deleted":
                (self.tasks_dir / f"task_{tid}.json").unlink(missing_ok=True)
                return f"Task {tid} deleted"
        if add_blocked_by:
            task["blockedBy"] = list(set(task["blockedBy"] + add_blocked_by))
        if add_blocks:
            task["blocks"] = list(set(task["blocks"] + add_blocks))
        self._save(task)
        return json.dumps(task, indent=2)

    def list_all(self) -> str:
        """List all tasks."""
        tasks = [json.loads(f.read_text()) for f in sorted(self.tasks_dir.glob("task_*.json"))]
        if not tasks:
            return "No tasks."

        lines = []
        for t in tasks:
            m = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}.get(t["status"], "[?]")
            owner = f" @{t['owner']}" if t.get("owner") else ""
            blocked = f" (blocked by: {t['blockedBy']})" if t.get("blockedBy") else ""
            lines.append(f"{m} #{t['id']}: {t['subject']}{owner}{blocked}")
        return "\n".join(lines)

    def claim(self, tid: int, owner: str) -> str:
        """Claim a task."""
        task = self._load(tid)
        task["owner"] = owner
        task["status"] = "in_progress"
        self._save(task)
        return f"Claimed task #{tid} for {owner}"
