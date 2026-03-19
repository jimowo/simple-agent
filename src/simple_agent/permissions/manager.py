"""Permission manager for dangerous operations."""

from typing import Any, Callable, Dict, List, Optional, Protocol

from loguru import logger

from simple_agent.exceptions import InvalidPolicyError
from simple_agent.permissions.models import (
    PermissionPolicy,
    PermissionRequest,
    PermissionResponse,
)
from simple_agent.tools.tool_definitions import TOOL_RISK_LEVELS

USE_PROMPT_TOOLKIT = True


def _render_permission_panel(request: PermissionRequest) -> None:
    """Render the permission warning panel once."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    console = Console()
    console.line()
    console.line()

    panel_content = Text()
    panel_content.append("Permission Required\n", style="bold yellow")
    panel_content.append(f"Reason: {request.reason}\n")
    panel_content.append(f"Tool: {request.tool}\n", style="cyan")
    panel_content.append(f"Risk: {request.risk_level}\n", style="red")
    if request.params:
        panel_content.append(f"Parameters: {request._format_params()}\n", style="dim")

    console.print(Panel(panel_content, title="[yellow]WARNING[/yellow]", border_style="yellow"))
    console.line()


def show_permission_help() -> None:
    """Show help for permission choices."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Permission Choices", show_header=True, header_style="bold cyan")
    table.add_column("Choice", style="cyan", width=10)
    table.add_column("Action", style="green")
    table.add_column("Description", style="dim")
    table.add_row("Y/yes", "Allow once", "Allow this operation for this time only")
    table.add_row("n/no", "Deny", "Deny this operation")
    table.add_row("a/always", "Allow for session", "Always allow this tool (remembered)")
    table.add_row("d/deny", "Deny for session", "Never allow this tool (remembered)")
    table.add_row("s/skip", "Skip", "Skip this operation (same as deny)")
    table.add_row("h/help", "Show help", "Display this help message")
    console.print()
    console.print(table)
    console.print()


def prompt_with_prompt_toolkit(
    request: PermissionRequest,
    *,
    show_panel: bool = True,
    on_always: Optional[Callable[[], None]] = None,
    on_deny: Optional[Callable[[], None]] = None,
) -> PermissionResponse:
    """Prompt for permission using prompt_toolkit."""
    from prompt_toolkit import HTML, PromptSession
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.validation import ValidationError, Validator

    if show_panel:
        _render_permission_panel(request)

    class ChoiceValidator(Validator):
        def __init__(self) -> None:
            self.valid_choices = {"", "y", "yes", "n", "no", "a", "always", "d", "deny", "s", "skip", "h", "help"}

        def validate(self, document):
            text = document.text.strip().lower()
            if text in self.valid_choices:
                return True
            raise ValidationError(
                message="Invalid choice. Enter Y, n, a, d, s, or h for help",
                cursor_position=len(document.text),
            )

    session = PromptSession(
        completer=WordCompleter(["yes", "no", "always", "deny", "skip", "help"], ignore_case=True),
        complete_while_typing=True,
        validator=ChoiceValidator(),
        validate_while_typing=False,
    )

    while True:
        try:
            response = session.prompt(
                HTML("<ansiyellow>Allow?</ansiyellow> [Y/n/a(llow)/d(eny)/s(kip)/h(elp)]: <ansireset>")
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return PermissionResponse(allowed=False)

        if response in ("", "y", "yes"):
            return PermissionResponse(allowed=True)
        if response in ("n", "no"):
            return PermissionResponse(allowed=False)
        if response in ("h", "help"):
            show_permission_help()
            continue
        if response in ("a", "always"):
            if on_always:
                on_always()
            return PermissionResponse(allowed=True, policy=PermissionPolicy.ALWAYS, remember=True)
        if response in ("d", "deny"):
            if on_deny:
                on_deny()
            return PermissionResponse(allowed=False, policy=PermissionPolicy.NEVER, remember=True)
        if response in ("s", "skip"):
            return PermissionResponse(allowed=False)


def prompt_basic(
    request: PermissionRequest,
    *,
    show_panel: bool = True,
    on_always: Optional[Callable[[], None]] = None,
    on_deny: Optional[Callable[[], None]] = None,
) -> PermissionResponse:
    """Prompt for permission using basic console input."""
    try:
        if show_panel:
            _render_permission_panel(request)
    except Exception:
        if show_panel:
            print("\n")
            print(f"[PERMISSION] {request.reason}")
            print(f"  Tool: {request.tool}")
            print(f"  Risk: {request.risk_level}")

    while True:
        try:
            response = input(
                "Allow? [Y/n/a(llow for session)/d(eny for session)/s(kip once)]: "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return PermissionResponse(allowed=False)
        except Exception:
            response = input("Allow? [Y/n/a/d/s]: ").strip().lower()

        if response in ("", "y", "yes"):
            return PermissionResponse(allowed=True)
        if response in ("n", "no"):
            return PermissionResponse(allowed=False)
        if response in ("a", "always"):
            if on_always:
                on_always()
            return PermissionResponse(allowed=True, policy=PermissionPolicy.ALWAYS, remember=True)
        if response in ("d", "deny"):
            if on_deny:
                on_deny()
            return PermissionResponse(allowed=False, policy=PermissionPolicy.NEVER, remember=True)
        if response in ("s", "skip"):
            return PermissionResponse(allowed=False)
        print("Invalid response. Please enter Y, n, a, d, or s.")


def prompt_for_permission(
    request: PermissionRequest,
    *,
    on_always: Optional[Callable[[], None]] = None,
    on_deny: Optional[Callable[[], None]] = None,
) -> PermissionResponse:
    """Use the best available prompt implementation."""
    if USE_PROMPT_TOOLKIT:
        try:
            return prompt_with_prompt_toolkit(
                request,
                show_panel=True,
                on_always=on_always,
                on_deny=on_deny,
            )
        except Exception:
            return prompt_basic(
                request,
                show_panel=False,
                on_always=on_always,
                on_deny=on_deny,
            )
    return prompt_basic(
        request,
        show_panel=True,
        on_always=on_always,
        on_deny=on_deny,
    )


class StatusController(Protocol):
    """Protocol for controlling status display during permission requests."""

    def pause(self) -> None:
        ...

    def resume(self) -> None:
        ...


class NoOpStatusController:
    """No-op status controller for when status control is not needed."""

    def pause(self) -> None:
        pass

    def resume(self) -> None:
        pass


class PermissionRule:
    """Rule for when permission is required."""

    def __init__(
        self,
        tool_pattern: str,
        risk_level: str = "medium",
        reason: str = "Tool execution requires confirmation",
    ):
        self.tool_pattern = tool_pattern
        self.risk_level = risk_level
        self.reason = reason

    def matches(self, tool: str, risk_level: str) -> bool:
        tool_matches = False
        if self.tool_pattern == "*":
            tool_matches = True
        elif self.tool_pattern == tool:
            tool_matches = True
        elif self.tool_pattern.endswith("*"):
            tool_matches = tool.startswith(self.tool_pattern[:-1])

        return tool_matches and self.risk_level == risk_level


class PermissionManager:
    """Manager for tool execution permissions."""

    RISK_LEVELS = {**TOOL_RISK_LEVELS, "delete_file": "high", "run_command": "high"}

    def __init__(
        self,
        user_callback: Optional[Callable[[PermissionRequest], PermissionResponse]] = None,
        status_controller: Optional[StatusController] = None,
    ):
        self.rules = self._default_rules()
        self.session_policies: Dict[str, PermissionPolicy] = {}
        self.status_controller = status_controller or NoOpStatusController()
        callback = user_callback or self._default_user_callback
        self.user_callback = self._wrap_callback_with_status_control(callback)

    def _wrap_callback_with_status_control(
        self, callback: Callable[[PermissionRequest], PermissionResponse]
    ) -> Callable[[PermissionRequest], PermissionResponse]:
        def wrapped(request: PermissionRequest) -> PermissionResponse:
            self.status_controller.pause()
            try:
                return callback(request)
            finally:
                self.status_controller.resume()

        return wrapped

    def _default_rules(self) -> List[PermissionRule]:
        return [
            PermissionRule("write_file", risk_level="high", reason="Writing to a file may modify important data"),
            PermissionRule("bash", risk_level="high", reason="Dangerous command execution may have system-wide effects"),
            PermissionRule("bash", risk_level="medium", reason="Command execution may have system-wide effects"),
            PermissionRule("edit_file", risk_level="medium", reason="Editing files changes existing content"),
        ]

    def set_session_policy(self, tool: str, policy: PermissionPolicy) -> None:
        if not isinstance(policy, PermissionPolicy):
            raise InvalidPolicyError(str(policy), "policy must be a PermissionPolicy value")
        self.session_policies[tool] = policy

    def get_session_policy(self, tool: str) -> Optional[PermissionPolicy]:
        if tool in self.session_policies:
            return self.session_policies[tool]
        for pattern, policy in self.session_policies.items():
            if pattern.endswith("*") and tool.startswith(pattern[:-1]):
                return policy
        return None

    def check_permission(
        self,
        tool: str,
        params: Dict[str, Any],
        risk_level_override: Optional[str] = None,
    ) -> PermissionResponse:
        risk_level = risk_level_override or self.RISK_LEVELS.get(tool, "low")
        session_policy = self.get_session_policy(tool)

        if session_policy == PermissionPolicy.ALWAYS:
            return PermissionResponse(allowed=True, policy=session_policy)
        if session_policy == PermissionPolicy.NEVER:
            return PermissionResponse(allowed=False, policy=session_policy)

        if tool == "bash" and "command" in params:
            from simple_agent.utils.safety import is_dangerous_command

            if is_dangerous_command(params.get("command", "")):
                risk_level = "high"

        if not self._requires_permission(tool, risk_level):
            return PermissionResponse(allowed=True)

        request = PermissionRequest(
            tool=tool,
            params=params,
            risk_level=risk_level,
            reason=self._get_reason(tool, risk_level),
        )
        response = self.user_callback(request)
        logger.info(
            "[PERMISSION_CHECK] Permission decision for '{}': allowed={}, policy={}",
            tool,
            response.allowed,
            response.policy,
        )
        return response

    def _requires_permission(self, tool: str, risk_level: str) -> bool:
        return any(rule.matches(tool, risk_level) for rule in self.rules)

    def _get_reason(self, tool: str, risk_level: str) -> str:
        for rule in self.rules:
            if rule.matches(tool, risk_level):
                return rule.reason
        return f"Tool '{tool}' execution requires confirmation"

    def _default_user_callback(self, request: PermissionRequest) -> PermissionResponse:
        return prompt_for_permission(
            request,
            on_always=lambda: self.set_session_policy(request.tool, PermissionPolicy.ALWAYS),
            on_deny=lambda: self.set_session_policy(request.tool, PermissionPolicy.NEVER),
        )

    def _prompt_with_prompt_toolkit(self, request: PermissionRequest) -> PermissionResponse:
        return prompt_with_prompt_toolkit(
            request,
            on_always=lambda: self.set_session_policy(request.tool, PermissionPolicy.ALWAYS),
            on_deny=lambda: self.set_session_policy(request.tool, PermissionPolicy.NEVER),
        )

    def _prompt_basic(self, request: PermissionRequest) -> PermissionResponse:
        return prompt_basic(
            request,
            on_always=lambda: self.set_session_policy(request.tool, PermissionPolicy.ALWAYS),
            on_deny=lambda: self.set_session_policy(request.tool, PermissionPolicy.NEVER),
        )

    def _show_permission_help(self):
        show_permission_help()

    def clear_session_policies(self) -> None:
        self.session_policies.clear()

    def list_session_policies(self) -> Dict[str, PermissionPolicy]:
        return self.session_policies.copy()

    def get_permission_required_tools(self) -> Dict[str, str]:
        return dict(TOOL_RISK_LEVELS)
