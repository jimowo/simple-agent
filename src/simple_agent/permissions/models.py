"""Permission models and policies.

This module defines the data models for permission requests and policies,
following SOLID principles for maintainability.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class PermissionPolicy(str, Enum):
    """Permission policy for tool execution.

    This enum follows the Open/Closed Principle (OCP) by allowing
    new policies to be added without modifying existing code.
    """

    ASK = "ask"  # Always ask user for permission
    ALWAYS = "always"  # Always allow without asking
    NEVER = "never"  # Always deny without asking
    SESSION = "session"  # Ask once per session, then remember


@dataclass
class PermissionRequest:
    """Permission request data model.

    This class follows the Single Responsibility Principle (SRP) by
    solely being responsible for holding permission request data.

    Attributes:
        tool: Tool name being called
        params: Tool parameters
        risk_level: Risk level of the operation (low/medium/high)
        reason: Human-readable reason for the permission request
    """

    tool: str
    params: Dict[str, Any]
    risk_level: str
    reason: str

    def __str__(self) -> str:
        """Get human-readable representation of the request.

        Returns:
            Formatted permission request string
        """
        params_str = self._format_params()
        return f"{self.reason}\n  Tool: {self.tool}\n  Parameters: {params_str}"

    def _format_params(self) -> str:
        """Format parameters for display.

        Returns:
            Formatted parameters string
        """
        if not self.params:
            return "(none)"

        # Truncate long values for display
        formatted = []
        for k, v in self.params.items():
            v_str = str(v)
            if len(v_str) > 100:
                v_str = v_str[:97] + "..."
            formatted.append(f"{k}={v_str}")
        return ", ".join(formatted)


@dataclass
class PermissionResponse:
    """Permission response data model.

    This class follows the Single Responsibility Principle (SRP) by
    solely being responsible for holding permission response data.

    Attributes:
        allowed: Whether permission was granted
        policy: Policy that was applied (for session memory)
        remember: Whether to remember this decision for the session
    """

    allowed: bool
    policy: Optional[PermissionPolicy] = None
    remember: bool = False
