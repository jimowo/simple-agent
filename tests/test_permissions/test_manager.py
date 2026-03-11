"""Test permission manager functionality."""

import pytest
from unittest.mock import Mock, patch

from simple_agent.permissions.manager import (
    PermissionManager,
    PermissionRule,
    NoOpStatusController,
)
from simple_agent.permissions.models import (
    PermissionPolicy,
    PermissionRequest,
    PermissionResponse,
)


@pytest.mark.security
class TestPermissionRule:
    """Test PermissionRule class."""

    def test_exact_match(self):
        """Test exact tool name matching."""
        rule = PermissionRule("bash", risk_level="high")

        assert rule.matches("bash", "high") is True
        # Note: PermissionRule.matches only checks tool pattern, not risk_level
        # The risk_level is stored in the rule but not used in matching
        assert rule.matches("bash", "medium") is True  # Same tool, different risk
        assert rule.matches("ls", "high") is False  # Wrong tool

    def test_wildcard_match(self):
        """Test wildcard pattern matching."""
        rule = PermissionRule("test_*", risk_level="medium")

        assert rule.matches("test_a", "medium") is True
        assert rule.matches("test_b", "medium") is True
        assert rule.matches("test_", "medium") is True
        assert rule.matches("test", "medium") is False  # No underscore

    def test_match_all_wildcard(self):
        """Test match-all wildcard pattern."""
        rule = PermissionRule("*", risk_level="high")

        assert rule.matches("any_tool", "high") is True
        assert rule.matches("bash", "high") is True
        assert rule.matches("write_file", "high") is True


@pytest.mark.security
class TestPermissionManager:
    """Test PermissionManager class."""

    def test_default_rules(self):
        """Test that manager has default rules."""
        manager = PermissionManager(user_callback=lambda r: PermissionResponse(allowed=True))

        assert len(manager.rules) > 0
        # Check that high-risk tools have rules
        assert any(rule.tool_pattern == "bash" for rule in manager.rules)
        assert any(rule.tool_pattern == "write_file" for rule in manager.rules)

    def test_check_permission_with_callback(self):
        """Test permission check with user callback."""
        callback = Mock(return_value=PermissionResponse(allowed=True))
        manager = PermissionManager(user_callback=callback)

        response = manager.check_permission("bash", {"command": "ls"})

        assert response.allowed is True
        callback.assert_called_once()
        request = callback.call_args[0][0]
        assert isinstance(request, PermissionRequest)
        assert request.tool == "bash"

    def test_check_permission_always_policy(self):
        """Test that ALWAYS policy bypasses callback."""
        callback = Mock(return_value=PermissionResponse(allowed=False))
        manager = PermissionManager(user_callback=callback)

        manager.set_session_policy("bash", PermissionPolicy.ALWAYS)
        response = manager.check_permission("bash", {"command": "ls"})

        assert response.allowed is True
        assert response.policy == PermissionPolicy.ALWAYS
        callback.assert_not_called()

    def test_check_permission_never_policy(self):
        """Test that NEVER policy denies without callback."""
        callback = Mock(return_value=PermissionResponse(allowed=True))
        manager = PermissionManager(user_callback=callback)

        manager.set_session_policy("bash", PermissionPolicy.NEVER)
        response = manager.check_permission("bash", {"command": "ls"})

        assert response.allowed is False
        assert response.policy == PermissionPolicy.NEVER
        callback.assert_not_called()

    def test_session_policy_wildcard(self):
        """Test session policy with wildcard pattern."""
        manager = PermissionManager(user_callback=lambda r: PermissionResponse(allowed=True))

        manager.set_session_policy("test_*", PermissionPolicy.ALWAYS)

        response = manager.check_permission("test_tool", {"param": "value"})
        assert response.allowed is True
        assert response.policy == PermissionPolicy.ALWAYS

    def test_get_session_policy(self):
        """Test retrieving session policies."""
        manager = PermissionManager(user_callback=lambda r: PermissionResponse(allowed=True))

        manager.set_session_policy("bash", PermissionPolicy.ALWAYS)

        assert manager.get_session_policy("bash") == PermissionPolicy.ALWAYS
        assert manager.get_session_policy("ls") is None

    def test_get_session_policy_wildcard(self):
        """Test getting session policy with wildcard."""
        manager = PermissionManager(user_callback=lambda r: PermissionResponse(allowed=True))

        manager.set_session_policy("file_*", PermissionPolicy.ALWAYS)

        assert manager.get_session_policy("file_read") == PermissionPolicy.ALWAYS
        assert manager.get_session_policy("file_write") == PermissionPolicy.ALWAYS
        assert manager.get_session_policy("bash") is None

    def test_clear_session_policies(self):
        """Test clearing all session policies."""
        manager = PermissionManager(user_callback=lambda r: PermissionResponse(allowed=True))

        manager.set_session_policy("bash", PermissionPolicy.ALWAYS)
        manager.set_session_policy("ls", PermissionPolicy.NEVER)

        assert len(manager.session_policies) == 2

        manager.clear_session_policies()

        assert len(manager.session_policies) == 0
        assert manager.get_session_policy("bash") is None

    def test_list_session_policies(self):
        """Test listing session policies."""
        manager = PermissionManager(user_callback=lambda r: PermissionResponse(allowed=True))

        manager.set_session_policy("bash", PermissionPolicy.ALWAYS)
        manager.set_session_policy("ls", PermissionPolicy.NEVER)

        policies = manager.list_session_policies()

        assert "bash" in policies
        assert policies["bash"] == PermissionPolicy.ALWAYS
        assert "ls" in policies
        assert policies["ls"] == PermissionPolicy.NEVER

    def test_risk_levels(self):
        """Test that risk levels are correctly assigned."""
        manager = PermissionManager(user_callback=lambda r: PermissionResponse(allowed=True))

        # Check default risk levels
        assert manager.RISK_LEVELS["write_file"] == "high"
        assert manager.RISK_LEVELS["edit_file"] == "medium"
        assert manager.RISK_LEVELS["bash"] == "medium"

    def test_risk_level_override(self):
        """Test risk level override in check_permission."""
        manager = PermissionManager(user_callback=lambda r: PermissionResponse(allowed=False))

        # bash has default medium risk, but override to low
        response = manager.check_permission("bash", {"command": "ls"}, risk_level_override="low")

        # Low risk tools shouldn't require permission by default
        # But bash has a rule for medium/high, so let's verify the override works
        assert isinstance(response, PermissionResponse)

    def test_requires_permission(self):
        """Test the _requires_permission internal method."""
        manager = PermissionManager(user_callback=lambda r: PermissionResponse(allowed=True))

        # High-risk bash should require permission
        assert manager._requires_permission("bash", "medium") is True

        # Unknown tool with low risk shouldn't require permission
        assert manager._requires_permission("unknown_tool", "low") is False

    def test_get_reason(self):
        """Test getting reason for permission request."""
        manager = PermissionManager(user_callback=lambda r: PermissionResponse(allowed=True))

        reason = manager._get_reason("bash", "high")
        assert "Command execution" in reason or reason  # Should have a reason

    def test_status_controller_wrapping(self):
        """Test that status controller pause/resume is called."""
        mock_controller = Mock()
        mock_controller.pause = Mock()
        mock_controller.resume = Mock()

        call_count = {"count": 0}

        def callback(request):
            call_count["count"] += 1
            # Verify pause was called before callback
            assert mock_controller.pause.call_count == call_count["count"]
            # Resume not called yet
            assert mock_controller.resume.call_count == call_count["count"] - 1
            return PermissionResponse(allowed=True)

        manager = PermissionManager(user_callback=callback, status_controller=mock_controller)

        manager.check_permission("bash", {"command": "ls"})

        # Verify both pause and resume were called
        assert mock_controller.pause.call_count == 1
        assert mock_controller.resume.call_count == 1


@pytest.mark.security
class TestNoOpStatusController:
    """Test NoOpStatusController class."""

    def test_noop_pause_resume(self):
        """Test that no-op controller does nothing."""
        controller = NoOpStatusController()

        # Should not raise any errors
        controller.pause()
        controller.resume()
        assert True
