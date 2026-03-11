"""Test permission models and policies."""

import pytest

from simple_agent.permissions.models import (
    PermissionPolicy,
    PermissionRequest,
    PermissionResponse,
)


@pytest.mark.security
class TestPermissionPolicy:
    """Test PermissionPolicy enum."""

    def test_policy_values(self):
        """Test that all expected policies exist."""
        assert PermissionPolicy.ASK == "ask"
        assert PermissionPolicy.ALWAYS == "always"
        assert PermissionPolicy.NEVER == "never"
        assert PermissionPolicy.SESSION == "session"

    def test_policy_is_string(self):
        """Test that policies can be compared to strings."""
        assert PermissionPolicy.ALWAYS == "always"
        assert "never" == PermissionPolicy.NEVER


@pytest.mark.security
class TestPermissionRequest:
    """Test PermissionRequest dataclass."""

    def test_create_request(self):
        """Test creating a permission request."""
        request = PermissionRequest(
            tool="bash",
            params={"command": "ls"},
            risk_level="medium",
            reason="Command execution may have system-wide effects",
        )

        assert request.tool == "bash"
        assert request.params == {"command": "ls"}
        assert request.risk_level == "medium"
        assert request.reason == "Command execution may have system-wide effects"

    def test_str_representation(self):
        """Test string representation of request."""
        request = PermissionRequest(
            tool="write_file",
            params={"path": "test.txt", "content": "hello"},
            risk_level="high",
            reason="Writing to a file may modify important data",
        )

        result = str(request)
        assert "write_file" in result
        assert "test.txt" in result

    def test_format_params_empty(self):
        """Test formatting empty parameters."""
        request = PermissionRequest(
            tool="test",
            params={},
            risk_level="low",
            reason="Test",
        )

        assert request._format_params() == "(none)"

    def test_format_params_with_values(self):
        """Test formatting parameters with values."""
        request = PermissionRequest(
            tool="test",
            params={"path": "file.txt", "content": "data"},
            risk_level="low",
            reason="Test",
        )

        result = request._format_params()
        assert "path=file.txt" in result
        assert "content=data" in result

    def test_format_params_truncates_long_values(self):
        """Test that long parameter values are truncated."""
        long_value = "x" * 200
        request = PermissionRequest(
            tool="test",
            params={"data": long_value},
            risk_level="low",
            reason="Test",
        )

        result = request._format_params()
        assert "data=" in result
        assert "..." in result
        assert len(result) < 200  # Should be truncated


@pytest.mark.security
class TestPermissionResponse:
    """Test PermissionResponse dataclass."""

    def test_create_response_allowed(self):
        """Test creating an allowed response."""
        response = PermissionResponse(allowed=True)

        assert response.allowed is True
        assert response.policy is None
        assert response.remember is False

    def test_create_response_denied(self):
        """Test creating a denied response."""
        response = PermissionResponse(allowed=False)

        assert response.allowed is False

    def test_create_response_with_policy(self):
        """Test creating response with session policy."""
        response = PermissionResponse(
            allowed=True,
            policy=PermissionPolicy.ALWAYS,
            remember=True,
        )

        assert response.allowed is True
        assert response.policy == PermissionPolicy.ALWAYS
        assert response.remember is True

    def test_create_response_with_never_policy(self):
        """Test creating response with never policy."""
        response = PermissionResponse(
            allowed=False,
            policy=PermissionPolicy.NEVER,
            remember=True,
        )

        assert response.allowed is False
        assert response.policy == PermissionPolicy.NEVER
        assert response.remember is True
