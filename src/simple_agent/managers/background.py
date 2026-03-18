"""Background task manager."""

import subprocess
import threading
import uuid
from queue import Queue

from simple_agent.exceptions import BackgroundTaskError
from simple_agent.managers.base import BaseManager
from simple_agent.utils.constants import MAX_BASH_OUTPUT
from simple_agent.utils.error_handling import format_tool_error
from simple_agent.utils.logger import LoggerMixin


class BackgroundManager(BaseManager, LoggerMixin):
    """Manager for background task execution."""

    def __init__(self, settings=None):
        """Initialize the background manager.

        Args:
            settings: Optional Settings instance
        """
        super().__init__(settings)
        self.tasks = {}
        self.notifications = Queue()

    def run(self, command: str, timeout: int = 120) -> str:
        """Run a command in background."""
        if not command.strip():
            raise BackgroundTaskError("command cannot be empty")
        tid = str(uuid.uuid4())[:8]
        self.tasks[tid] = {"status": "running", "command": command, "result": None}
        self.logger.info("Starting background task {}: {}", tid, command[:80])
        threading.Thread(target=self._exec, args=(tid, command, timeout), daemon=True).start()
        return f"Background task {tid} started: {command[:80]}"

    def _exec(self, tid: str, command: str, timeout: int):
        """Execute background task."""
        self.logger.debug("Executing task {}: {}", tid, command[:60])
        try:
            r = subprocess.run(
                command,
                shell=True,
                cwd=self.settings.workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = (r.stdout + r.stderr).strip()[:MAX_BASH_OUTPUT]
            self.tasks[tid].update({"status": "completed", "result": output or "(no output)"})
            self.logger.success("Task {} completed: {}", tid, tid)
        except subprocess.TimeoutExpired as e:
            error = BackgroundTaskError(f"timed out after {timeout} seconds", task_id=tid)
            self.tasks[tid].update({"status": "error", "result": str(error)})
            self.logger.error("Task {} failed: {}", tid, str(e))
        except Exception as e:
            self.tasks[tid].update({"status": "error", "result": format_tool_error("background_run", e)})
            self.logger.error("Task {} failed: {}", tid, str(e))

        self.notifications.put(
            {
                "task_id": tid,
                "status": self.tasks[tid]["status"],
                "result": self.tasks[tid]["result"][:500],
            }
        )

    def check(self, tid: str = None) -> str:
        """Check background task status."""
        if tid:
            task = self.tasks.get(tid)
            if task is None:
                raise BackgroundTaskError(f"unknown task id '{tid}'", task_id=tid)
            return f"[{task['status']}] {task.get('result', '(running)')}"
        return (
            "\n".join(f"{k}: [{v['status']}] {v['command'][:60]}" for k, v in self.tasks.items())
            or "No bg tasks."
        )

    def drain(self) -> list:
        """Drain notification queue."""
        notifs = []
        while not self.notifications.empty():
            notifs.append(self.notifications.get_nowait())
        return notifs
