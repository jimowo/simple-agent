"""Teammate manager for multi-agent collaboration."""

import json
import threading
import time

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
        self.settings = settings or Settings()
        self.bus = bus
        self.task_mgr = task_mgr
        self.team_dir = self.settings.team_dir
        self.team_dir.mkdir(exist_ok=True)
        self.config_path = self.team_dir / "config.json"
        self.config = self._load()
        self.threads = {}

    def _load(self) -> dict:
        """Load team configuration."""
        if self.config_path.exists():
            return json.loads(self.config_path.read_text())
        return {"team_name": "default", "members": []}

    def _save(self):
        """Save team configuration."""
        self.config_path.write_text(json.dumps(self.config, indent=2))

    def _find(self, name: str) -> dict:
        """Find member by name."""
        for m in self.config["members"]:
            if m["name"] == name:
                return m
        return None

    def _create_provider(self):
        """Create provider instance for teammates."""
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
        """Spawn a new teammate."""
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
        """Set member status."""
        member = self._find(name)
        if member:
            member["status"] = status
            self._save()

    def _loop(self, name: str, role: str, prompt: str, provider):
        """Main loop for teammate agent."""
        team_name = self.config["team_name"]
        sys_prompt = (
            f"You are '{name}', role: {role}, team: {team_name}, at {self.settings.workdir}. "
            f"Use idle when done with current work. You may auto-claim tasks."
        )
        messages = [{"role": "user", "content": prompt}]
        tools = [
            {
                "name": "bash",
                "description": "Run command.",
                "input_schema": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
            {
                "name": "read_file",
                "description": "Read file.",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write file.",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["path", "content"],
                },
            },
            {
                "name": "edit_file",
                "description": "Edit file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old_text": {"type": "string"},
                        "new_text": {"type": "string"},
                    },
                    "required": ["path", "old_text", "new_text"],
                },
            },
            {
                "name": "send_message",
                "description": "Send message.",
                "input_schema": {
                    "type": "object",
                    "properties": {"to": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["to", "content"],
                },
            },
            {
                "name": "idle",
                "description": "Signal no more work.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "claim_task",
                "description": "Claim task by ID.",
                "input_schema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "integer"}},
                    "required": ["task_id"],
                },
            },
        ]

        while True:
            # -- WORK PHASE --
            for _ in range(50):
                inbox = self.bus.read_inbox(name)
                for msg in inbox:
                    if msg.get("type") == "shutdown_request":
                        self._set_status(name, "shutdown")
                        return
                    messages.append({"role": "user", "content": json.dumps(msg)})
                try:
                    response = provider.create_message(
                        messages=messages,
                        tools=tools,
                        system=sys_prompt,
                        max_tokens=8000,
                    )
                except Exception:
                    self._set_status(name, "shutdown")
                    return

                messages.append({"role": "assistant", "content": response.content})
                if response.stop_reason != "tool_use":
                    break

                results = []
                idle_requested = False
                for tc in response.tool_calls:
                    if tc.name == "idle":
                        idle_requested = True
                        output = "Entering idle phase."
                    elif tc.name == "claim_task":
                        output = self.task_mgr.claim(tc.input["task_id"], name)
                    elif tc.name == "send_message":
                        output = self.bus.send(name, tc.input["to"], tc.input["content"])
                    else:
                        dispatch = {
                            "bash": lambda **kw: run_bash(kw["command"]),
                            "read_file": lambda **kw: read_file(kw["path"]),
                            "write_file": lambda **kw: write_file(kw["path"], kw["content"]),
                            "edit_file": lambda **kw: edit_file(
                                kw["path"], kw["old_text"], kw["new_text"]
                            ),
                        }
                        output = dispatch.get(tc.name, lambda **kw: "Unknown")(**tc.input)
                    print(f"  [{name}] {tc.name}: {str(output)[:120]}")
                    results.append(
                        {"type": "tool_result", "tool_use_id": tc.id, "content": str(output)}
                    )
                messages.append({"role": "user", "content": results})
                if idle_requested:
                    break

            # -- IDLE PHASE --
            self._set_status(name, "idle")
            resume = False
            for _ in range(self.settings.idle_timeout // max(self.settings.poll_interval, 1)):
                time.sleep(self.settings.poll_interval)
                inbox = self.bus.read_inbox(name)
                if inbox:
                    for msg in inbox:
                        if msg.get("type") == "shutdown_request":
                            self._set_status(name, "shutdown")
                            return
                        messages.append({"role": "user", "content": json.dumps(msg)})
                    resume = True
                    break
                unclaimed = []
                for f in sorted(self.settings.tasks_dir.glob("task_*.json")):
                    t = json.loads(f.read_text())
                    if (
                        t.get("status") == "pending"
                        and not t.get("owner")
                        and not t.get("blockedBy")
                    ):
                        unclaimed.append(t)
                if unclaimed:
                    task = unclaimed[0]
                    self.task_mgr.claim(task["id"], name)
                    if len(messages) <= 3:
                        messages.insert(
                            0,
                            {
                                "role": "user",
                                "content": f"<identity>You are '{name}', role: {role}, team: {team_name}.</identity>",
                            },
                        )
                        messages.insert(
                            1, {"role": "assistant", "content": f"I am {name}. Continuing."}
                        )
                    messages.append(
                        {
                            "role": "user",
                            "content": f"<auto-claimed>Task #{task['id']}: {task['subject']}\n{task.get('description', '')}</auto-claimed>",
                        }
                    )
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"Claimed task #{task['id']}. Working on it.",
                        }
                    )
                    resume = True
                    break
            if not resume:
                self._set_status(name, "shutdown")
                return
            self._set_status(name, "working")

    def list_all(self) -> str:
        """List all teammates."""
        if not self.config["members"]:
            return "No teammates."
        lines = [f"Team: {self.config['team_name']}"]
        for m in self.config["members"]:
            lines.append(f"  {m['name']} ({m['role']}): {m['status']}")
        return "\n".join(lines)

    def member_names(self) -> list:
        """Get list of member names."""
        return [m["name"] for m in self.config["members"]]
