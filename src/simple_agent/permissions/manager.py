"""Permission manager for dangerous operations.

This module implements the permission manager following SOLID principles:
- Single Responsibility Principle (SRP): Only manages permission logic
- Open/Closed Principle (OCP): New permission types can be added
- Dependency Inversion Principle (DIP): Uses protocol for user interaction
"""

from typing import Callable, Dict, List, Optional

from simple_agent.permissions.models import PermissionPolicy, PermissionRequest, PermissionResponse


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

    def matches(self, tool: str, risk_level: str) -> bool:
        """Check if this rule matches the given tool and risk level.

        Args:
            tool: Tool name
            risk_level: Risk level of the operation

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

    def __init__(self, user_callback: Optional[Callable[[PermissionRequest], PermissionResponse]] = None):
        """Initialize the permission manager.

        Args:
            user_callback: Optional function to request user permission.
                If None, uses default CLI callback.
        """
        self.rules = self._default_rules()
        self.session_policies: Dict[str, PermissionPolicy] = {}
        self.user_callback = user_callback or self._default_user_callback

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
                reason="Command execution may have system-wide effects",
            ),
            # Medium-risk operations
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

        # Check session policy
        session_policy = self.get_session_policy(tool)
        if session_policy == PermissionPolicy.ALWAYS:
            return PermissionResponse(allowed=True, policy=session_policy)
        elif session_policy == PermissionPolicy.NEVER:
            return PermissionResponse(allowed=False, policy=session_policy)

        # Check if permission is required based on rules
        requires_permission = self._requires_permission(tool, risk_level)
        if not requires_permission:
            return PermissionResponse(allowed=True)

        # Create permission request
        request = PermissionRequest(
            tool=tool,
            params=params,
            risk_level=risk_level,
            reason=self._get_reason(tool, risk_level),
        )

        # Request permission from user
        return self.user_callback(request)

    def _requires_permission(self, tool: str, risk_level: str) -> bool:
        """Check if permission is required for this tool/risk level.

        Args:
            tool: Tool name
            risk_level: Risk level

        Returns:
            True if permission is required
        """
        for rule in self.rules:
            if rule.matches(tool, risk_level):
                return True
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

        Args:
            request: Permission request

        Returns:
            Permission response
        """
        print(f"\n⚠️  Permission required: {request.reason}")
        print(f"   Tool: {request.tool}")
        print(f"   Risk: {request.risk_level}")

        if request.params:
            print(f"   Parameters: {request._format_params()}")

        while True:
            response = input(
                "Allow? [Y/n/a(llow for session)/d(eny for session)/s(kip once)]: "
            ).strip().lower()

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

    def clear_session_policies(self) -> None:
        """Clear all session-level policies."""
        self.session_policies.clear()

    def list_session_policies(self) -> Dict[str, PermissionPolicy]:
        """List all active session policies.

        Returns:
            Dictionary of tool -> policy mappings
        """
        return self.session_policies.copy()
