"""Context compression utilities."""

import json
import time
from pathlib import Path
from typing import Any, List

from simple_agent.models.config import Settings
from simple_agent.models.projects import SessionMessage


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


def auto_compact(messages: List[Any], provider, model: str, transcript_dir: Path = None) -> List[Any]:
    """
    Compress conversation by saving transcript and generating summary.

    Args:
        messages: Current message history
        provider: AI provider instance
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
    resp = provider.create_message(
        messages=[{"role": "user", "content": f"Summarize for continuity:\n{conv_text}"}],
        tools=[],
        max_tokens=2000,
    )

    # Extract text from response content
    summary = ""
    for c in resp.content:
        if isinstance(c, dict) and c.get("type") == "text":
            summary = c.get("text", "")
            break

    return [
        {"role": "user", "content": f"[Compressed. Transcript: {path}]\n{summary}"},
        {"role": "assistant", "content": "Understood. Continuing with summary context."},
    ]


def save_session_transcript(
    messages: List[Any],
    project_id: str,
    session_id: str,
    session_mgr,
) -> Path:
    """
    Save full message history to session file.

    This saves the complete conversation to the session's JSONL file,
    which serves as both the active conversation history and a permanent
    transcript archive.

    Args:
        messages: Current message history
        project_id: Project ID
        session_id: Session ID
        session_mgr: SessionManager instance

    Returns:
        Path to the session file
    """

    project_dir = session_mgr.settings.workdir / ".simple" / "projects" / project_id
    session_file = project_dir / f"{session_id}.jsonl"

    # Ensure directory exists
    session_file.parent.mkdir(parents=True, exist_ok=True)

    # Save all messages to session file
    with open(session_file, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")

    return session_file


def session_aware_compact(
    messages: List[Any],
    provider,
    model: str,
    project_id: str,
    session_id: str,
    session_mgr,
    create_branch: bool = False,
) -> List[Any]:
    """
    Compress conversation and save to session, optionally creating a branch.

    This function:
    1. Saves the full conversation to the session JSONL file (transcript)
    2. Generates an AI summary
    3. Optionally creates a new session branch for the compressed conversation
    4. Returns compressed messages with summary

    Args:
        messages: Current message history
        provider: AI provider instance
        model: Model ID for summarization
        project_id: Project ID
        session_id: Current session ID
        session_mgr: SessionManager instance
        create_branch: If True, create a new session branch for compressed conversation

    Returns:
        New message list with summary
    """
    import time

    # 1. Save full transcript to session
    transcript_path = save_session_transcript(messages, project_id, session_id, session_mgr)

    # 2. Generate summary
    conv_text = json.dumps(messages, default=str)[:80000]
    resp = provider.create_message(
        messages=[{"role": "user", "content": f"Summarize for continuity:\n{conv_text}"}],
        tools=[],
        max_tokens=2000,
    )

    # Extract text from response
    summary = ""
    for c in resp.content:
        if isinstance(c, dict) and c.get("type") == "text":
            summary = c.get("text", "")
            break

    # 3. Optionally create a branch session
    if create_branch:
        # Get current session to use as parent
        current_session = session_mgr.get_session(project_id, session_id)
        if current_session:
            # Create new session branch
            branch_title = f"{current_session.title} (compressed)" if current_session.title else "Compressed Session"
            new_session = session_mgr.create_session(
                project_id,
                parent_session_id=session_id,
                title=branch_title,
            )
            # Save summary note to branch
            note_msg = SessionMessage(
                role="system",
                content=f"[Compressed from {session_id[:8]}...]\nSummary: {summary}",
                timestamp=time.time(),
            )
            session_mgr.append_message(project_id, new_session.session_id, note_msg)
            print(f"[Created branch: {new_session.session_id[:8]}...]")

    # 4. Return compressed messages
    return [
        {"role": "user", "content": f"[Compressed. Transcript: {transcript_path}]\n{summary}"},
        {"role": "assistant", "content": "Understood. Continuing with summary context."},
    ]


def get_session_history(project_id: str, session_id: str, session_mgr) -> List[Any]:
    """
    Load message history from session file.

    Args:
        project_id: Project ID
        session_id: Session ID
        session_mgr: SessionManager instance

    Returns:
        List of message dictionaries
    """

    project_dir = session_mgr.settings.workdir / ".simple" / "projects" / project_id
    session_file = project_dir / f"{session_id}.jsonl"

    if not session_file.exists():
        return []

    messages = []
    with open(session_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue

    return messages
