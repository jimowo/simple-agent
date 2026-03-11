"""Teammate manager for multi-agent collaboration."""

import json
import threading
import time
from typing import Any, Dict, List

from simple_agent.managers.message import MessageBus
from simple_agent.managers.task import TaskManager
from simple_agent.models.config import Settings
from simple_agent.providers import ProviderFactory
from simple_agent.tools.bash_tools import run_bash
from simple_agent.tools.file_tools import edit_file, read_file, write_file

# Global shutdown and plan tracking
shutdown_requests = {}
plan_requests = {}


class TeammateManager:
    """Manager for autonomous teammate agents."""

    def __init__(self, bus: MessageBus, task_mgr: TaskManager, settings: Settings = None):
        """Initialize the teammate manager.

        Args:
            bus: Message bus for communication
            task_mgr: Task manager instance
            settings: Optional settings
        """
        self.settings = settings or Settings()
        self.bus = bus
        self.task_mgr = task_mgr
        self.team_dir = self.settings.team_dir
        self.team_dir.mkdir(exist_ok=True)
        self.config_path = self.team_dir / "config.json"
        self.config = self._load()
        self.threads = {}

    def _load(self) -> dict:
        """Load team configuration.

        Returns:
            Team configuration dict
        """
        if self.config_path.exists():
            return json.loads(self.config_path.read_text())
        return {"team_name": "default", "members": []}

    def _save(self):
        """Save team configuration."""
        self.config_path.write_text(json.dumps(self.config, indent=2))

    def _find(self, name: str) -> dict:
        """Find member by name.

        Args:
            name: Member name

        Returns:
            Member dict or None
        """
        for m in self.config["members"]:
            if m["name"] == name:
                return m
        return None

    def _create_provider(self):
        """Create provider instance for teammates.

        Returns:
            Provider instance
        """
        provider_name = self.settings.get_active_provider()
        provider_config = self.settings.get_provider_config(provider_name)

        # Get API key from config or environment
        api_key = provider_config.api_key
        if not api_key:
            # Try environment variable fallback
            env_key_map = {
                "anthropic": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
                "gemini": "GEMINI_API_KEY",
                "groq": "GROQ_API_KEY",
                "local": "dummy",
            }
            import os

            api_key = os.getenv(env_key_map.get(provider_name, ""))

        if not api_key and provider_name != "local":
            raise ValueError(f"API key not found for provider '{provider_name}'.")

        return ProviderFactory.create(
            provider_name=provider_name,
            api_key=api_key or "dummy",
            base_url=provider_config.base_url,
            model=self.settings.model_id or None,
        )

    def spawn(self, name: str, role: str, prompt: str) -> str:
        """Spawn a new teammate.

        Args:
            name: Teammate name
            role: Teammate role
            prompt: Initial prompt

        Returns:
            Success message
        """
        member = self._find(name)
        if member:
            if member["status"] not in ("idle", "shutdown"):
                return f"Error: '{name}' is currently {member['status']}"
            member["status"] = "working"
            member["role"] = role
        else:
            member = {"name": name, "role": role, "status": "working"}
            self.config["members"].append(member)
        self._save()

        provider = self._create_provider()

        threading.Thread(
            target=self._loop,
            args=(name, role, prompt, provider),
            daemon=True,
        ).start()
        return f"Spawned '{name}' (role: {role})"

    def _set_status(self, name: str, status: str):
        """Set member status.

        Args:
            name: Member name
            status: New status
        """
        member = self._find(name)
        if member:
            member["status"] = status
            self._save()

    def _execute_tool_call(self, name: str, tool_call: Any) -> str:
        """Execute a single tool call.

        Args:
            name: Teammate name
            tool_call: Tool call object

        Returns:
            Tool output
        """
        if tool_call.name == "idle":
            return "Entering idle phase."
        elif tool_call.name == "claim_task":
            return self.task_mgr.claim(tool_call.input["task_id"], name)
        elif tool_call.name == "send_message":
            return self.bus.send(name, tool_call.input["to"], tool_call.input["content"])
        else:
            # File and bash tools
            dispatch = {
                "bash": lambda **kw: run_bash(kw["command"]),
                "read_file": lambda **kw: read_file(kw["path"]),
                "write_file": lambda **kw: write_file(kw["path"], kw["content"]),
                "edit_file": lambda **kw: edit_file(kw["path"], kw["old_text"], kw["new_text"]),
            }
            return dispatch.get(tool_call.name, lambda **kw: "Unknown")(**tool_call.input)

    def _process_inbox_messages(
        self, name: str, inbox: List[Dict], messages: List[Dict]
    ) -> bool:
        """Process inbox messages and check for shutdown.

        Args:
            name: Teammate name
            inbox: List of inbox messages
            messages: Message list to append to

        Returns:
            True if shutdown was requested, False otherwise
        """
        for msg in inbox:
            if msg.get("type") == "shutdown_request":
                self._set_status(name, "shutdown")
                return True
            messages.append({"role": "user", "content": json.dumps(msg)})
        return False

    def _work_phase(
        self, name: str, role: str, team_name: str, messages: List[Dict], tools: List[Dict], provider
    ) -> bool:
        """Execute work phase with multiple iterations.

        Args:
            name: Teammate name
            role: Teammate role
            team_name: Team name
            messages: Message history
            tools: Available tools
            provider: AI provider

        Returns:
            True if idle was requested, False otherwise
        """
        sys_prompt = (
            f"You are '{name}', role: {role}, team: {team_name}, at {self.settings.workdir}. "
            f"Use idle when done with current work. You may auto-claim tasks."
        )

        for _ in range(50):
            # Check inbox
            inbox = self.bus.read_inbox(name)
            if self._process_inbox_messages(name, inbox, messages):
                return True  # Shutdown requested

            # Generate response
            try:
                response = provider.create_message(
                    messages=messages, tools=tools, system=sys_prompt, max_tokens=8000
                )
            except Exception:
                self._set_status(name, "shutdown")
                return True

            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                break

            # Execute tools
            results = []
            idle_requested = False
            for tc in response.tool_calls:
                if tc.name == "idle":
                    idle_requested = True
                output = self._execute_tool_call(name, tc)
                print(f"  [{name}] {tc.name}: {str(output)[:120]}")
                results.append({"type": "tool_result", "tool_use_id": tc.id, "content": str(output)})

            messages.append({"role": "user", "content": results})
            if idle_requested:
                return True

        return False

    def _check_unclaimed_tasks(self, name: str) -> Any:
        """Check for unclaimed tasks and claim one.

        Args:
            name: Teammate name

        Returns:
            Task dict if claimed, None otherwise
        """
        unclaimed = []
        for f in sorted(self.settings.tasks_dir.glob("task_*.json")):
            t = json.loads(f.read_text())
            if t.get("status") == "pending" and not t.get("owner") and not t.get("blockedBy"):
                unclaimed.append(t)

        if unclaimed:
            task = unclaimed[0]
            self.task_mgr.claim(task["id"], name)
            return task
        return None

    def _add_task_to_messages(
        self, task: Dict, name: str, role: str, team_name: str, messages: List[Dict]
    ):
        """Add claimed task to message history.

        Args:
            task: Task dict
            name: Teammate name
            role: Teammate role
            team_name: Team name
            messages: Message list to modify
        """
        if len(messages) <= 3:
            messages.insert(
                0,
                {
                    "role": "user",
                    "content": f"<identity>You are '{name}', role: {role}, team: {team_name}.</identity>",
                },
            )
            messages.insert(1, {"role": "assistant", "content": f"I am {name}. Continuing."})

        messages.append(
            {
                "role": "user",
                "content": f"<auto-claimed>Task #{task['id']}: {task['subject']}\n{task.get('description', '')}</auto-claimed>",
            }
        )
        messages.append(
            {"role": "assistant", "content": f"Claimed task #{task['id']}. Working on it."}
        )

    def _idle_phase(
        self, name: str, role: str, team_name: str, messages: List[Dict]
    ) -> bool:
        """Execute idle phase, checking for messages and tasks.

        Args:
            name: Teammate name
            role: Teammate role
            team_name: Team name
            messages: Message history

        Returns:
            True if should resume work, False if should shutdown
        """
        self._set_status(name, "idle")
        max_iterations = self.settings.idle_timeout // max(self.settings.poll_interval, 1)

        for _ in range(max_iterations):
            time.sleep(self.settings.poll_interval)

            # Check inbox
            inbox = self.bus.read_inbox(name)
            if inbox:
                if self._process_inbox_messages(name, inbox, messages):
                    return False  # Shutdown requested
                return True  # Resume work

            # Check for unclaimed tasks
            task = self._check_unclaimed_tasks(name)
            if task:
                self._add_task_to_messages(task, name, role, team_name, messages)
                return True  # Resume work

        # No activity, shutdown
        return False

    def _loop(self, name: str, role: str, prompt: str, provider):
        """Main loop for teammate agent.

        Args:
            name: Teammate name
            role: Teammate role
            prompt: Initial prompt
            provider: AI provider
        """
        from simple_agent.tools.tool_definitions import get_teammate_tools

        team_name = self.config["team_name"]
        messages = [{"role": "user", "content": prompt}]
        tools = get_teammate_tools()

        while True:
            # Work phase
            should_idle = self._work_phase(name, role, team_name, messages, tools, provider)
            if not should_idle:
                # Work phase requested shutdown
                return

            # Idle phase
            should_resume = self._idle_phase(name, role, team_name, messages)
            if not should_resume:
                self._set_status(name, "shutdown")
                return

            # Resume working
            self._set_status(name, "working")

    def list_all(self) -> str:
        """List all teammates.

        Returns:
            Formatted list of teammates
        """
        if not self.config["members"]:
            return "No teammates."
        lines = [f"Team: {self.config['team_name']}"]
        for m in self.config["members"]:
            lines.append(f"  {m['name']} ({m['role']}): {m['status']}")
        return "\n".join(lines)

    def member_names(self) -> list:
        """Get list of member names.

        Returns:
            List of member names
        """
        return [m["name"] for m in self.config["members"]]
