"""Core Agent functionality."""

import json
import uuid
from anthropic import Anthropic
from simple_agent.models.config import Settings
from simple_agent.tools.bash_tools import run_bash
from simple_agent.tools.file_tools import read_file, write_file, edit_file
from simple_agent.utils.compression import auto_compact


def run_subagent(client: Anthropic, model: str, prompt: str, agent_type: str = "Explore") -> str:
    """
    Run a subagent for isolated exploration or work.

    Args:
        client: Anthropic client
        model: Model ID
        prompt: Prompt for subagent
        agent_type: Type of agent (Explore or general-purpose)

    Returns:
        Summary of subagent work
    """
    sub_tools = [
        {
            "name": "bash",
            "description": "Run command.",
            "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
        },
        {
            "name": "read_file",
            "description": "Read file.",
            "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        },
    ]
    if agent_type != "Explore":
        sub_tools += [
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
                    "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}},
                    "required": ["path", "old_text", "new_text"],
                },
            },
        ]

    sub_handlers = {
        "bash": lambda **kw: run_bash(kw["command"]),
        "read_file": lambda **kw: read_file(kw["path"]),
        "write_file": lambda **kw: write_file(kw["path"], kw["content"]),
        "edit_file": lambda **kw: edit_file(kw["path"], kw["old_text"], kw["new_text"]),
    }

    sub_msgs = [{"role": "user", "content": prompt}]
    resp = None
    for _ in range(30):
        resp = client.messages.create(model=model, messages=sub_msgs, tools=sub_tools, max_tokens=8000)
        sub_msgs.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            break
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                h = sub_handlers.get(b.name, lambda **kw: "Unknown tool")
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": str(h(**b.input))[:50000]})
        sub_msgs.append({"role": "user", "content": results})

    if resp:
        return "".join(b.text for b in resp.content if hasattr(b, "text")) or "(no summary)"
    return "(subagent failed)"


def handle_shutdown_request(bus, teammate: str) -> str:
    """Handle shutdown request for a teammate."""
    from simple_agent.managers.teammate import shutdown_requests

    req_id = str(uuid.uuid4())[:8]
    shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
    bus.send("lead", teammate, "Please shut down.", "shutdown_request", {"request_id": req_id})
    return f"Shutdown request {req_id} sent to '{teammate}'"


def handle_plan_review(bus, request_id: str, approve: bool, feedback: str = "") -> str:
    """Handle plan approval response."""
    from simple_agent.managers.teammate import plan_requests

    req = plan_requests.get(request_id)
    if not req:
        return f"Error: Unknown plan request_id '{request_id}'"
    req["status"] = "approved" if approve else "rejected"
    bus.send("lead", req["from"], feedback, "plan_approval_response", {
        "request_id": request_id,
        "approve": approve,
        "feedback": feedback,
    })
    return f"Plan {req['status']} for '{req['from']}'"


class Agent:
    """Main Agent class."""

    def __init__(
        self,
        settings: Settings = None,
        todo_manager=None,
        task_manager=None,
        background_manager=None,
        message_bus=None,
        teammate_manager=None,
        skill_loader=None,
    ):
        self.settings = settings or Settings()
        self.client = Anthropic(base_url=self.settings.anthropic_base_url) if self.settings.anthropic_base_url else Anthropic()

        # Managers
        from simple_agent.managers.todo import TodoManager
        from simple_agent.managers.task import TaskManager
        from simple_agent.managers.background import BackgroundManager
        from simple_agent.managers.message import MessageBus
        from simple_agent.managers.skill import SkillLoader
        from simple_agent.managers.teammate import TeammateManager

        self.todo = todo_manager or TodoManager()
        self.task_mgr = task_manager or TaskManager(self.settings)
        self.bg = background_manager or BackgroundManager(self.settings)
        self.bus = message_bus or MessageBus(self.settings)
        self.skill_loader = skill_loader or SkillLoader(settings=self.settings)
        self.teammate = teammate_manager or TeammateManager(self.bus, self.task_mgr, self.settings)

        # Initialize tool handlers
        from simple_agent.tools.tool_handlers import initialize_handlers
        initialize_handlers(
            self.todo,
            self.task_mgr,
            self.bg,
            self.bus,
            self.teammate,
            self.skill_loader,
            self.client,
            self.settings,
        )

    @property
    def system_prompt(self) -> str:
        """Get system prompt for the agent."""
        return f"""You are a coding agent at {self.settings.workdir}.
Use tools to solve tasks. Use TodoWrite for multi-step work.
Use task for subagent delegation. Use load_skill for specialized knowledge.

Skills available:
{self.skill_loader.descriptions()}"""

    def process_query(self, query: str, history: list = None) -> str:
        """
        Process a user query.

        Args:
            query: User query
            history: Optional message history

        Returns:
            Agent response
        """
        if history is None:
            history = []

        history.append({"role": "user", "content": query})
        self._agent_loop(history)

        # Get last assistant response
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                content = msg.get("content", [])
                if isinstance(content, list):
                    return "\n".join(getattr(c, "text", str(c)) for c in content if hasattr(c, "text") or c)
                return str(content)
        return "(no response)"

    def _agent_loop(self, messages: list):
        """Run agent loop until completion."""
        from simple_agent.utils.compression import estimate_tokens, microcompact
        from simple_agent.tools.tool_handlers import TOOL_HANDLERS, TOOLS

        rounds_without_todo = 0
        while True:
            # Compression pipeline
            microcompact(messages)
            if estimate_tokens(messages) > self.settings.token_threshold:
                print("[auto-compact triggered]")
                messages[:] = auto_compact(messages, self.client, self.settings.model_id, self.settings.transcript_dir)

            # Drain background notifications
            notifs = self.bg.drain()
            if notifs:
                txt = "\n".join(f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs)
                messages.append({"role": "user", "content": f"<background-results>\n{txt}\n</background-results>"})
                messages.append({"role": "assistant", "content": "Noted background results."})

            # Check lead inbox
            inbox = self.bus.read_inbox("lead")
            if inbox:
                messages.append({"role": "user", "content": f"<inbox>{json.dumps(inbox, indent=2)}</inbox>"})
                messages.append({"role": "assistant", "content": "Noted inbox messages."})

            # LLM call
            response = self.client.messages.create(
                model=self.settings.model_id,
                system=self.system_prompt,
                messages=messages,
                tools=TOOLS,
                max_tokens=self.settings.max_tokens,
            )
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                return

            # Tool execution
            results = []
            used_todo = False
            manual_compress = False
            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "compress":
                        manual_compress = True
                    handler = TOOL_HANDLERS.get(block.name)
                    try:
                        output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                    except Exception as e:
                        output = f"Error: {e}"
                    print(f"> {block.name}: {str(output)[:200]}")
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
                    if block.name == "TodoWrite":
                        used_todo = True

            # Nag reminder
            rounds_without_todo = 0 if used_todo else rounds_without_todo + 1
            if rounds_without_todo >= 3:
                results.insert(0, {"type": "text", "text": "<reminder>Update your todos.</reminder>"})

            messages.append({"role": "user", "content": results})

            # Manual compress
            if manual_compress:
                print("[manual compact]")
                messages[:] = auto_compact(messages, self.client, self.settings.model_id, self.settings.transcript_dir)
