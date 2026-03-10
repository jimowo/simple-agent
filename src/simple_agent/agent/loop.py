"""Agent loop utilities."""

import json

from simple_agent.tools.tool_handlers import TOOL_HANDLERS, TOOLS
from simple_agent.utils.compression import auto_compact, estimate_tokens, microcompact


def agent_loop(messages: list, agent) -> None:
    """
    Run agent loop for conversation history.

    Args:
        messages: Message history list (modified in-place)
        agent: Agent instance
    """
    rounds_without_todo = 0

    while True:
        # Compression pipeline
        microcompact(messages)
        if estimate_tokens(messages) > agent.settings.token_threshold:
            print("[auto-compact triggered]")
            messages[:] = auto_compact(
                messages, agent.provider, agent.settings.model_id or "default", agent.settings.transcript_dir
            )

        # Drain background notifications
        notifs = agent.bg.drain()
        if notifs:
            txt = "\n".join(f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs)
            messages.append(
                {"role": "user", "content": f"<background-results>\n{txt}\n</background-results>"}
            )
            messages.append({"role": "assistant", "content": "Noted background results."})

        # Check lead inbox
        inbox = agent.bus.read_inbox("lead")
        if inbox:
            messages.append(
                {"role": "user", "content": f"<inbox>{json.dumps(inbox, indent=2)}</inbox>"}
            )
            messages.append({"role": "assistant", "content": "Noted inbox messages."})

        # LLM call
        response = agent.provider.create_message(
            messages=messages,
            tools=TOOLS,
            system=agent.system_prompt,
            max_tokens=agent.settings.max_tokens,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return

        # Tool execution
        results = []
        used_todo = False
        manual_compress = False
        for tc in response.tool_calls:
            if tc.name == "compress":
                manual_compress = True
            handler = TOOL_HANDLERS.get(tc.name)
            try:
                output = handler(**tc.input) if handler else f"Unknown tool: {tc.name}"
            except Exception as e:
                output = f"Error: {e}"
            print(f"> {tc.name}: {str(output)[:200]}")
            results.append(
                {"type": "tool_result", "tool_use_id": tc.id, "content": str(output)}
            )
            if tc.name == "TodoWrite":
                used_todo = True

        # Nag reminder
        rounds_without_todo = 0 if used_todo else rounds_without_todo + 1
        if rounds_without_todo >= 3:
            results.insert(0, {"type": "text", "text": "<reminder>Update your todos.</reminder>"})

        messages.append({"role": "user", "content": results})

        # Manual compress
        if manual_compress:
            print("[manual compact]")
            messages[:] = auto_compact(
                messages, agent.provider, agent.settings.model_id or "default", agent.settings.transcript_dir
            )
