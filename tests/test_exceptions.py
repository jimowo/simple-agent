"""Test unified exception hierarchy."""

import pytest

from simple_agent.exceptions import (
    CommandInjectionError,
    # Configuration
    ConfigurationError,
    # Container
    ContainerError,
    InvalidModelError,
    InvalidPolicyError,
    InvalidProviderError,
    MissingApiKeyError,
    PathTraversalError,
    PermissionDeniedError,
    # Permissions
    PermissionError,
    ProviderConnectionError,
    # Providers
    ProviderError,
    ProviderResponseError,
    RateLimitError,
    # Security
    SecurityError,
    ServiceNotFoundError,
    ServiceValidationError,
    # Base
    SimpleAgentError,
    # Tasks
    TaskError,
    TaskNotFoundError,
    TaskValidationError,
    TodoLimitError,
    # Tools
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
    UnsafeCommandError,
)


@pytest.mark.security
class TestSimpleAgentError:
    """Test base exception class."""

    def test_create_simple_error(self):
        """Test creating a simple error."""
        error = SimpleAgentError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details == {}

    def test_error_with_details(self):
        """Test error with additional details."""
        error = SimpleAgentError(
            "Error occurred",
            details={"code": 500, "field": "username"}
        )

        assert "code=500" in str(error)
        assert "field=username" in str(error)
        assert error.details["code"] == 500

    def test_error_inheritance(self):
        """Test that all custom exceptions inherit from SimpleAgentError."""
        exceptions = [
            ConfigurationError, SecurityError, ToolError, ProviderError,
            TaskError, PermissionError, ContainerError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, SimpleAgentError)


class TestConfigurationErrors:
    """Test configuration-related exceptions."""

    def test_invalid_provider_error(self):
        """Test InvalidProviderError."""
        error = InvalidProviderError("unknown_provider")

        assert "unknown_provider" in str(error)
        assert error.details["provider"] == "unknown_provider"

    def test_invalid_provider_with_available(self):
        """Test InvalidProviderError with available providers."""
        error = InvalidProviderError("bad", ["anthropic", "openai"])

        assert "bad" in str(error)
        assert error.details["available"] == "anthropic, openai"

    def test_missing_api_key_error(self):
        """Test MissingApiKeyError."""
        error = MissingApiKeyError("openai")

        assert "openai" in str(error)
        assert "OPENAI_API_KEY" in str(error)
        assert error.details["provider"] == "openai"

    def test_invalid_model_error(self):
        """Test InvalidModelError."""
        error = InvalidModelError("gpt-5", "openai")

        assert "gpt-5" in str(error)
        assert "openai" in str(error)
        assert error.details["model"] == "gpt-5"


class TestSecurityErrors:
    """Test security-related exceptions."""

    def test_path_traversal_error(self):
        """Test PathTraversalError."""
        error = PathTraversalError("../../../etc/passwd", "/workspace")

        assert "escapes workspace" in str(error)
        assert error.details["path"] == "../../../etc/passwd"

    def test_command_injection_error(self):
        """Test CommandInjectionError."""
        error = CommandInjectionError("rm -rf /", "Dangerous command")

        assert "blocked" in str(error)
        assert error.details["command"] == "rm -rf /"

    def test_unsafe_command_error(self):
        """Test UnsafeCommandError."""
        error = UnsafeCommandError("sudo rm", "high")

        assert "high" in str(error)
        assert "Unsafe" in str(error)


class TestToolErrors:
    """Test tool-related exceptions."""

    def test_tool_execution_error(self):
        """Test ToolExecutionError."""
        error = ToolExecutionError("bash", "Command not found")

        assert "bash" in str(error)
        assert "Command not found" in str(error)

    def test_tool_timeout_error(self):
        """Test ToolTimeoutError."""
        error = ToolTimeoutError("python", 120)

        assert "python" in str(error)
        assert "120" in str(error)
        assert error.details["timeout"] == 120

    def test_tool_not_found_error(self):
        """Test ToolNotFoundError."""
        error = ToolNotFoundError("missing_tool")

        assert "missing_tool" in str(error)
        assert "not found" in str(error)


class TestProviderErrors:
    """Test provider-related exceptions."""

    def test_provider_connection_error(self):
        """Test ProviderConnectionError."""
        error = ProviderConnectionError("anthropic", "Network timeout")

        assert "anthropic" in str(error)
        assert "Network timeout" in str(error)

    def test_provider_response_error(self):
        """Test ProviderResponseError."""
        error = ProviderResponseError("openai", "Invalid JSON")

        assert "openai" in str(error)
        assert "Invalid JSON" in str(error)

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError("groq", retry_after=60)

        assert "groq" in str(error)
        assert "60" in str(error)
        assert error.details["retry_after"] == 60

    def test_rate_limit_error_without_retry(self):
        """Test RateLimitError without retry time."""
        error = RateLimitError("anthropic")

        assert "anthropic" in str(error)
        assert error.details["retry_after"] is None


class TestTaskErrors:
    """Test task-related exceptions."""

    def test_task_not_found_error(self):
        """Test TaskNotFoundError."""
        error = TaskNotFoundError(42)

        assert "42" in str(error)
        assert "not found" in str(error)
        assert error.details["task_id"] == 42

    def test_task_validation_error(self):
        """Test TaskValidationError."""
        error = TaskValidationError("Invalid status", "status")

        assert "validation failed" in str(error)
        assert "Invalid status" in str(error)
        assert error.details["field"] == "status"

    def test_todo_limit_error(self):
        """Test TodoLimitError."""
        error = TodoLimitError(25, 20)

        assert "25" in str(error)
        assert "20" in str(error)
        assert "exceeded" in str(error)
        assert error.details["count"] == 25


class TestPermissionErrors:
    """Test permission-related exceptions."""

    def test_permission_denied_error(self):
        """Test PermissionDeniedError."""
        error = PermissionDeniedError("bash", "High risk operation")

        assert "bash" in str(error)
        assert "denied" in str(error)
        assert "High risk operation" in str(error)

    def test_invalid_policy_error(self):
        """Test InvalidPolicyError."""
        error = InvalidPolicyError("always", "Not a valid policy")

        assert "always" in str(error)
        assert "valid policy" in str(error)


class TestContainerErrors:
    """Test DI container exceptions."""

    def test_service_not_found_error(self):
        """Test ServiceNotFoundError."""
        error = ServiceNotFoundError("MyService")

        assert "MyService" in str(error)
        assert "not registered" in str(error)

    def test_service_not_found_with_available(self):
        """Test ServiceNotFoundError with available services."""
        error = ServiceNotFoundError("Foo", ["Bar", "Baz"])

        assert "Foo" in str(error)
        assert "Bar, Baz" in str(error)

    def test_service_validation_error(self):
        """Test ServiceValidationError."""
        error = ServiceValidationError("MyService", "Wrong type")

        assert "MyService" in str(error)
        assert "validation failed" in str(error)
        assert "Wrong type" in str(error)


@pytest.mark.integration
class TestExceptionIntegration:
    """Test exceptions in actual usage."""

    def test_catch_base_exception(self):
        """Test catching all custom exceptions via base class."""
        errors = [
            InvalidProviderError("bad"),
            PathTraversalError("..", "/workspace"),
            ToolExecutionError("bash", "failed"),
            TaskNotFoundError(1),
            PermissionDeniedError("write", "denied"),
        ]

        for error in errors:
            assert isinstance(error, SimpleAgentError)
            # Should be catchable by base class
            try:
                raise error
            except SimpleAgentError as e:
                assert e.message

    def test_exception_chaining(self):
        """Test that exceptions can be chained."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise SimpleAgentError("Wrapped error") from e
        except SimpleAgentError as caught:
            assert caught.__cause__ is not None
            assert isinstance(caught.__cause__, ValueError)
