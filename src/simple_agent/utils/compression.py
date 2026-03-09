"""Context compression utilities."""

import json
import time
from pathlib import Path
from typing import Any, List

from simple_agent.models.config import Settings


def estimate_tokens(messages: List[Any]) -> int:
    """
    Estimate token count from messages.

    Args:
        messages: List of message objects

    Returns:
        Estimated token count
    """
    return len(json.dumps(messages, default=str)) // 4


def microcompact(messages: List[Any]) -> None:
    """
    Clear old tool results keeping only the 3 most recent.

    Args:
        messages: List of messages to compact in-place
    """
    indices = []
    for i, msg in enumerate(messages):
        if msg["role"] == "user" and isinstance(msg.get("content"), list):
            for part in msg["content"]:
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    indices.append(part)
    if len(indices) <= 3:
        return
    for part in indices[:-3]:
        if isinstance(part.get("content"), str) and len(part["content"]) > 100:
            part["content"] = "[cleared]"


def auto_compact(messages: List[Any], client, model: str, transcript_dir: Path = None) -> List[Any]:
    """
    Compress conversation by saving transcript and generating summary.

    Args:
        messages: Current message history
        client: Anthropic client instance
        model: Model ID to use for summarization
        transcript_dir: Directory for transcripts (uses Settings.transcript_dir if None)

    Returns:
        New message list with summary
    """
    if transcript_dir is None:
        transcript_dir = Settings().transcript_dir
    transcript_dir.mkdir(exist_ok=True)

    path = transcript_dir / f"transcript_{int(time.time())}.jsonl"
    with open(path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")

    conv_text = json.dumps(messages, default=str)[:80000]
    resp = client.messages.create(
        model=model,
        messages=[{"role": "user", "content": f"Summarize for continuity:\n{conv_text}"}],
        max_tokens=2000,
    )
    summary = resp.content[0].text
    return [
        {"role": "user", "content": f"[Compressed. Transcript: {path}]\n{summary}"},
        {"role": "assistant", "content": "Understood. Continuing with summary context."},
    ]
