"""Permission manager for dangerous operations.

This module implements the permission manager following SOLID principles:
- Single Responsibility Principle (SRP): Only manages permission logic
- Open/Closed Principle (OCP): New permission types can be added
- Dependency Inversion Principle (DIP): Uses protocol for user interaction
"""

from typing import Callable, Dict, List, Optional, Protocol

from loguru import logger

from simple_agent.permissions.models import PermissionPolicy, PermissionRequest, PermissionResponse

# Flag to control whether to use prompt_toolkit for prompts
USE_PROMPT_TOOLKIT = True


class StatusController(Protocol):
    """Protocol for controlling status display during permission requests.

    This allows the permission manager to pause/resume status displays
    when user interaction is needed.
    """

    def pause(self) -> None:
        """Pause the status display."""
        ...

    def resume(self) -> None:
        """Resume the status display."""
        ...


class NoOpStatusController:
    """No-op status controller for when status control is not needed."""

    def pause(self) -> None:
        """No-op pause."""
        pass

    def resume(self) -> None:
        """No-op resume."""
        pass


class PermissionRule:
    """Rule for when permission is required.

    This class follows the Single Responsibility Principle (SRP) by
    solely being responsible for defining when a tool requires permission.

    Attributes:
        tool_pattern: Glob pattern for tool name matching
        risk_level: Minimum risk level to trigger this rule
        reason: Human-readable reason for permission
    """

    def __init__(
        self,
        tool_pattern: str,
        risk_level: str = "medium",
        reason: str = "Tool execution requires confirmation",
    ):
        self.tool_pattern = tool_pattern
        self.risk_level = risk_level
        self.reason = reason

    def matches(self, tool: str, _risk_level: str) -> bool:
        """Check if this rule matches the given tool and risk level.

        Note: This method only checks tool pattern matching, not risk level.
        The risk_level parameter is accepted for interface consistency but
        not used in matching logic (risk level is handled by PermissionManager).

        Args:
            tool: Tool name
            risk_level: Risk level of the operation (not used in matching)

        Returns:
            True if rule matches
        """
        # Simple glob matching (can be enhanced with fnmatch)
        if self.tool_pattern == "*":
            return True
        if self.tool_pattern == tool:
            return True
        if self.tool_pattern.endswith("*"):
            prefix = self.tool_pattern[:-1]
            return tool.startswith(prefix)
        return False


class PermissionManager:
    """Manager for tool execution permissions.

    This class follows the Single Responsibility Principle (SRP) by
    solely being responsible for managing permission logic. It delegates
    user interaction to a callback function.

    Attributes:
        rules: List of permission rules
        session_policies: Session-level permission policies
        user_callback: Function to request user permission
    """

    # Default risk levels for tools
    RISK_LEVELS = {
        "write_file": "high",
        "edit_file": "medium",
        "bash": "medium",
        "delete_file": "high",
        "run_command": "high",
    }

    def __init__(
        self,
        user_callback: Optional[Callable[[PermissionRequest], PermissionResponse]] = None,
        status_controller: Optional[StatusController] = None,
    ):
        """Initialize the permission manager.

        Args:
            user_callback: Optional function to request user permission.
                If None, uses default CLI callback.
            status_controller: Optional controller for pausing/resuming status
                displays during permission requests.
        """
        self.rules = self._default_rules()
        self.session_policies: Dict[str, PermissionPolicy] = {}
        self.status_controller = status_controller or NoOpStatusController()

        # Wrap user callback to handle status control
        if user_callback is None:
            self.user_callback = self._wrap_callback_with_status_control(self._default_user_callback)
            logger.debug("[PERMISSION_MANAGER] Initialized with default user callback")
        else:
            self.user_callback = self._wrap_callback_with_status_control(user_callback)
            logger.debug("[PERMISSION_MANAGER] Initialized with custom user callback")

        logger.debug(f"[PERMISSION_MANAGER] Configured {len(self.rules)} permission rules")
        for idx, rule in enumerate(self.rules):
            logger.debug(f"[PERMISSION_MANAGER] Rule {idx+1}: pattern='{rule.tool_pattern}', risk='{rule.risk_level}', reason='{rule.reason}'")

    def _wrap_callback_with_status_control(
        self, callback: Callable[[PermissionRequest], PermissionResponse]
    ) -> Callable[[PermissionRequest], PermissionResponse]:
        """Wrap a callback to automatically pause/resume status.

        Args:
            callback: Original callback function

        Returns:
            Wrapped callback function
        """
        def wrapped(request: PermissionRequest) -> PermissionResponse:
            self.status_controller.pause()
            try:
                return callback(request)
            finally:
                self.status_controller.resume()
        return wrapped

    def _default_rules(self) -> List[PermissionRule]:
        """Get default permission rules.

        Returns:
            List of default permission rules
        """
        return [
            # High-risk operations
            PermissionRule(
                "write_file",
                risk_level="high",
                reason="Writing to a file may modify important data",
            ),
            PermissionRule(
                "bash",
                risk_level="high",
                reason="Dangerous command execution may have system-wide effects",
            ),
            # Medium-risk operations
            PermissionRule(
                "bash",
                risk_level="medium",
                reason="Command execution may have system-wide effects",
            ),
            PermissionRule(
                "edit_file",
                risk_level="medium",
                reason="Editing files changes existing content",
            ),
        ]

    def set_session_policy(self, tool: str, policy: PermissionPolicy) -> None:
        """Set session-level policy for a tool.

        Args:
            tool: Tool name (supports glob patterns)
            policy: Policy to apply (always/ask/never/session)
        """
        self.session_policies[tool] = policy

    def get_session_policy(self, tool: str) -> Optional[PermissionPolicy]:
        """Get session-level policy for a tool.

        Args:
            tool: Tool name

        Returns:
            Policy if set, None otherwise
        """
        # Check exact match first
        if tool in self.session_policies:
            return self.session_policies[tool]

        # Check glob patterns
        for pattern, policy in self.session_policies.items():
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if tool.startswith(prefix):
                    return policy

        return None

    def check_permission(
        self,
        tool: str,
        params: Dict[str, any],
        risk_level_override: Optional[str] = None,
    ) -> PermissionResponse:
        """Check if permission is required and request it if needed.

        Args:
            tool: Tool name
            params: Tool parameters
            risk_level_override: Optional override for risk level

        Returns:
            Permission response indicating if allowed
        """
        # Get risk level
        risk_level = risk_level_override or self.RISK_LEVELS.get(tool, "low")

        logger.debug(f"[PERMISSION_CHECK] Starting permission check for tool='{tool}', risk_level='{risk_level}'")
        logger.debug(f"[PERMISSION_CHECK] Parameters: {params}")

        # Check session policy
        session_policy = self.get_session_policy(tool)
        logger.debug(f"[PERMISSION_CHECK] Session policy for '{tool}': {session_policy}")

        if session_policy == PermissionPolicy.ALWAYS:
            logger.info(f"[PERMISSION_CHECK] Permission ALLOWED by session policy (ALWAYS): {tool}")
            return PermissionResponse(allowed=True, policy=session_policy)
        elif session_policy == PermissionPolicy.NEVER:
            logger.warning(f"[PERMISSION_CHECK] Permission DENIED by session policy (NEVER): {tool}")
            return PermissionResponse(allowed=False, policy=session_policy)

        # Special handling for bash tool: use is_dangerous_command() for dynamic risk assessment
        if tool == "bash" and "command" in params:
            from simple_agent.utils.safety import is_dangerous_command
            command = params.get("command", "")
            if is_dangerous_command(command):
                # Dangerous command requires higher risk level
                risk_level = "high"
                logger.debug(f"[PERMISSION_CHECK] Bash command detected as DANGEROUS: {command[:100]}...")
            else:
                # Safe command uses default/medium risk level
                logger.debug(f"[PERMISSION_CHECK] Bash command detected as SAFE: {command[:100]}...")
            # Continue to permission request regardless (don't return early)

        # Check if permission is required based on rules
        requires_permission = self._requires_permission(tool, risk_level)
        logger.debug(f"[PERMISSION_CHECK] Requires permission for '{tool}' (risk: {risk_level}): {requires_permission}")

        if not requires_permission:
            logger.debug(f"[PERMISSION_CHECK] Permission NOT required, auto-allowing '{tool}'")
            return PermissionResponse(allowed=True)

        # Create permission request
        request = PermissionRequest(
            tool=tool,
            params=params,
            risk_level=risk_level,
            reason=self._get_reason(tool, risk_level),
        )

        logger.info(f"[PERMISSION_CHECK] Requesting user permission for '{tool}' (risk: {risk_level})")
        logger.debug(f"[PERMISSION_CHECK] Permission request reason: {request.reason}")

        # Request permission from user
        response = self.user_callback(request)

        logger.info(f"[PERMISSION_CHECK] Permission decision for '{tool}': allowed={response.allowed}, policy={response.policy}")

        return response

    def _requires_permission(self, tool: str, risk_level: str) -> bool:
        """Check if permission is required for this tool/risk level.

        Args:
            tool: Tool name
            risk_level: Risk level

        Returns:
            True if permission is required
        """
        logger.debug(f"[PERMISSION_RULES] Checking if '{tool}' (risk: {risk_level}) requires permission")
        logger.debug(f"[PERMISSION_RULES] Total rules configured: {len(self.rules)}")

        for idx, rule in enumerate(self.rules):
            matches = rule.matches(tool, risk_level)
            logger.debug(f"[PERMISSION_RULES] Rule {idx+1}/{len(self.rules)}: pattern='{rule.tool_pattern}', matches={matches}")
            if matches:
                logger.debug(f"[PERMISSION_RULES] Rule matched for '{tool}', permission required")
                return True

        logger.debug(f"[PERMISSION_RULES] No rules matched for '{tool}', permission NOT required")
        return False

    def _get_reason(self, tool: str, risk_level: str) -> str:
        """Get human-readable reason for permission request.

        Args:
            tool: Tool name
            risk_level: Risk level

        Returns:
            Reason string
        """
        for rule in self.rules:
            if rule.matches(tool, risk_level):
                return rule.reason
        return f"Tool '{tool}' execution requires confirmation"

    def _default_user_callback(self, request: PermissionRequest) -> PermissionResponse:
        """Default CLI-based user callback.

        This method can be overridden for different UI environments.
        Uses prompt_toolkit when available for better UX.

        Args:
            request: Permission request

        Returns:
            Permission response
        """
        # Try to use prompt_toolkit for enhanced UX
        if USE_PROMPT_TOOLKIT:
            try:
                return self._prompt_with_prompt_toolkit(request)
            except Exception:
                # Fall back to basic implementation
                return self._prompt_basic(request)
        else:
            return self._prompt_basic(request)

    def _prompt_with_prompt_toolkit(self, request: PermissionRequest) -> PermissionResponse:
        """Use prompt_toolkit for enhanced user interaction.

        Args:
            request: Permission request

        Returns:
            Permission response
        """
        from prompt_toolkit import HTML, PromptSession
        from prompt_toolkit.completion import WordCompleter
        from prompt_toolkit.validation import ValidationError, Validator
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console()

        # Display permission request with Rich
        console.line()
        console.line()

        panel_content = Text()
        panel_content.append("Permission Required\n", style="bold yellow")
        panel_content.append(f"Reason: {request.reason}\n", style="default")
        panel_content.append(f"Tool: {request.tool}\n", style="cyan")
        panel_content.append(f"Risk: {request.risk_level}\n", style="red")

        if request.params:
            panel_content.append(f"Parameters: {request._format_params()}\n", style="dim")

        console.print(Panel(panel_content, title="[yellow]WARNING[/yellow]", border_style="yellow"))
        console.line()

        class ChoiceValidator(Validator):
            """Validate permission response choices."""

            def __init__(self):
                self.valid_choices = ["y", "yes", "n", "no", "a", "always", "d", "deny", "s", "skip", ""]

            def validate(self, document):
                text = document.text.strip().lower()
                if text in self.valid_choices:
                    return True
                if text in ["h", "help"]:
                    return True
                raise ValidationError(
                    message="Invalid choice. Enter Y, n, a, d, s, or h for help",
                    cursor_position=len(document.text)
                )

        # Create prompt session with completer
        choices = ["yes", "no", "always", "deny", "skip", "help"]
        completer = WordCompleter(choices, ignore_case=True)

        session = PromptSession(
            completer=completer,
            complete_while_typing=True,
            validator=ChoiceValidator(),
            validate_while_typing=False,
        )

        # Interactive prompt loop
        while True:
            try:
                response = session.prompt(
                    HTML("<ansiyellow>Allow?</ansiyellow> [Y/n/a(llow)/d(eny)/s(kip)/h(elp)]: <ansireset>")
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                # User cancelled, deny by default
                return PermissionResponse(allowed=False)

            # Handle empty response (default to yes)
            if not response or response == "":
                return PermissionResponse(allowed=True)

            # Handle help
            if response in ("h", "help"):
                self._show_permission_help()
                continue

            # Handle choices
            if response in ("y", "yes"):
                return PermissionResponse(allowed=True)
            elif response in ("n", "no"):
                return PermissionResponse(allowed=False)
            elif response in ("a", "always"):
                self.set_session_policy(request.tool, PermissionPolicy.ALWAYS)
                console.print("[green]✓[/green] Session policy set: Always allow for this tool")
                return PermissionResponse(allowed=True, policy=PermissionPolicy.ALWAYS, remember=True)
            elif response in ("d", "deny"):
                self.set_session_policy(request.tool, PermissionPolicy.NEVER)
                console.print("[red]✓[/red] Session policy set: Never allow for this tool")
                return PermissionResponse(allowed=False, policy=PermissionPolicy.NEVER, remember=True)
            elif response in ("s", "skip"):
                return PermissionResponse(allowed=False)
            else:
                # Should not reach here due to validator, but just in case
                console.print("[red]Invalid response. Please enter Y, n, a, d, s, or h.[/red]")

    def _prompt_basic(self, request: PermissionRequest) -> PermissionResponse:
        """Basic fallback prompt without prompt_toolkit.

        Args:
            request: Permission request

        Returns:
            Permission response
        """
        # Try to use Rich for better display (handles encoding better)
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.text import Text

            console = Console()

            # Add visual separation before panel
            console.line()  # Add blank line
            console.line()  # Add another blank line

            # Build permission request panel
            panel_content = Text()
            panel_content.append("Permission Required\n", style="bold yellow")
            panel_content.append(f"Reason: {request.reason}\n", style="default")
            panel_content.append(f"Tool: {request.tool}\n", style="cyan")
            panel_content.append(f"Risk: {request.risk_level}\n", style="red")

            if request.params:
                panel_content.append(f"Parameters: {request._format_params()}\n", style="dim")

            console.print(Panel(panel_content, title="[yellow]WARNING[/yellow]", border_style="yellow"))
            console.line()  # Add blank line after panel

        except Exception:
            # Fallback to simple print (may have encoding issues)
            try:
                print("\n")
                print(f"[PERMISSION] {request.reason}")
                print(f"  Tool: {request.tool}")
                print(f"  Risk: {request.risk_level}")
            except Exception:
                print("\n")
                print(f"[PERMISSION] Tool: {request.tool} Risk: {request.risk_level}")

        # Get user response
        while True:
            try:
                response = input(
                    "Allow? [Y/n/a(llow for session)/d(eny for session)/s(kip once)]: "
                ).strip().lower()
            except Exception:
                # Fallback for encoding issues
                response = input("Allow? [Y/n/a/d/s]: ").strip().lower()

            if response in ("y", "yes", ""):
                return PermissionResponse(allowed=True)
            elif response in ("n", "no"):
                return PermissionResponse(allowed=False)
            elif response in ("a", "always"):
                self.set_session_policy(request.tool, PermissionPolicy.ALWAYS)
                return PermissionResponse(allowed=True, policy=PermissionPolicy.ALWAYS, remember=True)
            elif response in ("d", "deny"):
                self.set_session_policy(request.tool, PermissionPolicy.NEVER)
                return PermissionResponse(allowed=False, policy=PermissionPolicy.NEVER, remember=True)
            elif response in ("s", "skip"):
                return PermissionResponse(allowed=False)
            else:
                print("Invalid response. Please enter Y, n, a, d, or s.")

    def _show_permission_help(self):
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

    def clear_session_policies(self) -> None:
        """Clear all session-level policies."""
        self.session_policies.clear()

    def list_session_policies(self) -> Dict[str, PermissionPolicy]:
        """List all active session policies.

        Returns:
            Dictionary of tool -> policy mappings
        """
        return self.session_policies.copy()

    def get_permission_required_tools(self) -> Dict[str, str]:
        """Get tools that require permission with their risk levels.

        This method provides a centralized location for managing which tools
        require permission checking and at what risk level.

        Returns:
            Dictionary mapping tool names to their risk levels
        """
        return {
            "write_file": "high",
            "bash": "medium",
            "edit_file": "medium",
        }
