"""Tests for permission wrapper exception handling."""

import pytest

from simple_agent.exceptions import InvalidPolicyError, PermissionDeniedError
from simple_agent.permissions.manager import PermissionManager
from simple_agent.permissions.models import PermissionResponse
from simple_agent.permissions.wrapper import wrap_with_permission


class TestPermissionWrapperExceptions:
    """Test unified permission exception behavior."""

    def test_denied_permission_raises_shared_exception(self):
        """Permission denial should raise the shared PermissionDeniedError."""
        manager = PermissionManager(
            user_callback=lambda request: PermissionResponse(allowed=False)
        )
        wrapped = wrap_with_permission(
            "bash",
            lambda **kwargs: "ok",
            manager,
            risk_level="medium",
        )

        with pytest.raises(PermissionDeniedError, match="Permission denied"):
            wrapped(command="ls")

    def test_invalid_session_policy_raises_shared_exception(self):
        """Invalid policies should raise InvalidPolicyError."""
        manager = PermissionManager(
            user_callback=lambda request: PermissionResponse(allowed=True)
        )

        with pytest.raises(InvalidPolicyError, match="Invalid policy"):
            manager.set_session_policy("bash", "always")
