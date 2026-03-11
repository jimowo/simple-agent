"""Todo manager for tracking multi-step work."""

from typing import List

from simple_agent.exceptions import TaskValidationError, TodoLimitError
from simple_agent.models.tasks import TodoItem
from simple_agent.utils.logger import LoggerMixin


class TodoManager(LoggerMixin):
    """Manager for todo items."""

    def __init__(self):
        self.items: List[dict] = []

    def update(self, items: List[dict]) -> str:
        """
        Update todo items with validation.

        Args:
            items: List of todo item dictionaries

        Returns:
            Rendered todo list
        """
        self.logger.debug("Updating todo items: {}", len(items))
        validated = []
        ip = 0
        for i, item in enumerate(items):
            todo_item = TodoItem(**item)
            if todo_item.status == "in_progress":
                ip += 1
            validated.append(
                {
                    "content": todo_item.content,
                    "status": todo_item.status,
                    "activeForm": todo_item.active_form,
                }
            )

        if len(validated) > 20:
            self.logger.error("Too many todo items: {}", len(validated))
            raise TodoLimitError(len(validated), 20)
        if ip > 1:
            self.logger.error("Multiple in_progress items: {}", ip)
            raise TaskValidationError("Only one in_progress allowed", field="status")

        self.items = validated
        self.logger.info("Updated todos: {} items", len(validated))
        return self.render()

    def render(self) -> str:
        """
        Render todo list as string.

        Returns:
            Formatted todo list
        """
        if not self.items:
            return "No todos."

        lines = []
        for item in self.items:
            m = {"completed": "[x]", "in_progress": "[>]", "pending": "[ ]"}.get(
                item["status"], "[?]"
            )
            suffix = f" <- {item['activeForm']}" if item["status"] == "in_progress" else ""
            lines.append(f"{m} {item['content']}{suffix}")

        done = sum(1 for t in self.items if t["status"] == "completed")
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines)
