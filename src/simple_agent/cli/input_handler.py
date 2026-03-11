"""Interactive prompt handler with history and tab completion.

This module provides an enhanced input experience with:
- Up/Down arrow keys for history navigation (like bash HISTSIZE)
- Tab key for auto-completion of commands
- Persistent history across sessions
"""

import os
from pathlib import Path
from typing import List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.keys import Keys


class CommandCompleter(Completer):
    """Auto-completer for common commands."""

    def __init__(self) -> None:
        """Initialize with common command suggestions."""
        self.commands = [
            "exit",
            "quit",
            "help",
            "clear",
            "history",
            # Add more commands as needed
        ]

    def get_completions(self, document, complete_event):
        """Get completions for the current input.

        Args:
            document: The current document state
            complete_event: The complete event

        Yields:
            Completion suggestions
        """
        word_before_cursor = document.get_word_before_cursor(Word())
        text = document.text_before_cursor

        # If input is empty, show all commands
        if not text.strip():
            for cmd in self.commands:
                yield Completion(
                    cmd,
                    start_position=0,
                    display=cmd,
                    display_meta=f"Command: {cmd}",
                )
            return

        # Filter commands based on input
        for cmd in self.commands:
            if cmd.startswith(text.lower()):
                yield Completion(
                    cmd,
                    start_position=-len(text),
                    display=cmd,
                    display_meta=f"Command: {cmd}",
                )


class InteractivePrompt:
    """Interactive prompt with history and completion support.

    This class provides a readline-like interface with:
    - Persistent history stored in a file
    - Up/Down arrows for history navigation
    - Tab for auto-completion
    - History search with Ctrl+R
    """

    def __init__(
        self,
        history_file: Optional[Path] = None,
        history_size: int = 1000,
        enable_completion: bool = True,
    ) -> None:
        """Initialize the interactive prompt.

        Args:
            history_file: Path to history file. Defaults to ~/.simple-agent_history
            history_size: Maximum number of history entries to keep
            enable_completion: Whether to enable tab completion
        """
        # Set default history file path
        if history_file is None:
            home = Path.home()
            history_file = home / ".simple-agent_history"

        self.history_file = history_file
        self.history_size = history_size
        self.enable_completion = enable_completion

        # Ensure history directory exists
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # Create prompt session
        self.session: PromptSession = self._create_session()

    def _create_session(self) -> PromptSession:
        """Create a prompt session with all features enabled.

        Returns:
            Configured PromptSession
        """
        # File-based history for persistence
        history = FileHistory(str(self.history_file))

        # Create prompt session
        session = PromptSession(
            history=history,
            auto_suggest=AutoSuggestFromHistory(),
            enable_history_search=True,
            key_bindings=self._create_key_bindings(),
        )

        return session

    def _create_key_bindings(self) -> KeyBindings:
        """Create custom key bindings.

        Returns:
            KeyBindings object
        """
        kb = KeyBindings()

        @kb.add(Keys.ControlC)
        def _(event):
            """Handle Ctrl+C - exit gracefully."""
            event.app.exit(exception=KeyboardInterrupt)

        @kb.add(Keys.ControlD)
        def _(event):
            """Handle Ctrl+D - exit gracefully."""
            event.app.exit(exception=EOFError)

        return kb

    def prompt(self, message: str = "> ") -> str:
        """Get user input with history and completion support.

        Args:
            message: Prompt message to display

        Returns:
            User input string

        Raises:
            KeyboardInterrupt: If user presses Ctrl+C
            EOFError: If user presses Ctrl+D
        """
        completer = CommandCompleter() if self.enable_completion else None

        try:
            user_input = self.session.prompt(
                message,
                completer=completer,
                complete_while_typing=True,
            )
            return user_input
        except KeyboardInterrupt:
            raise
        except EOFError:
            raise

    def get_history(self, limit: Optional[int] = None) -> List[str]:
        """Get command history.

        Args:
            limit: Maximum number of entries to return. None for all.

        Returns:
            List of history entries
        """
        if not self.history_file.exists():
            return []

        with open(self.history_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        if limit:
            return lines[-limit:]
        return lines

    def clear_history(self) -> None:
        """Clear command history file."""
        if self.history_file.exists():
            self.history_file.unlink()

    def search_history(self, pattern: str) -> List[str]:
        """Search history for entries matching pattern.

        Args:
            pattern: Search pattern (substring match)

        Returns:
            List of matching history entries
        """
        history = self.get_history()
        return [entry for entry in history if pattern.lower() in entry.lower()]


# Word class for completion
class Word:
    """Word boundary definition for completion."""

    def __init__(self):
        """Initialize word boundaries."""
        pass

    def __call__(self, text):
        """Get word before cursor position.

        Args:
            text: Input text

        Returns:
            Word string before cursor
        """
        # Simple implementation: split by whitespace
        words = text.split()
        if words:
            return words[-1]
        return ""
