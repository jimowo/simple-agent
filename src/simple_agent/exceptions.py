"""Unified exception hierarchy for simple-agent.

This module defines a structured exception hierarchy that follows the
Single Responsibility Principle (SRP) by providing specific exceptions
for different domains of the application.

Exception Hierarchy:
    SimpleAgentError (base)
    ├── ConfigurationError
    │   ├── InvalidProviderError
    │   ├── MissingApiKeyError
    │   └── InvalidModelError
    ├── SecurityError
    │   ├── PathTraversalError
    │   ├── CommandInjectionError
    │   └── UnsafeCommandError
    ├── ToolError
    │   ├── ToolExecutionError
    │   ├── ToolTimeoutError
    │   └── ToolNotFoundError
    ├── ProviderError
    │   ├── ProviderConnectionError
    │   ├── ProviderResponseError
    │   └── RateLimitError
    ├── TaskError
    │   ├── TaskNotFoundError
    │   ├── TaskValidationError
    │   └── TodoLimitError
    ├── PermissionError
    │   ├── PermissionDeniedError
    │   └── InvalidPolicyError
    └── ContainerError
        ├── ServiceNotFoundError
        └── ServiceValidationError
"""

from typing import Optional


class SimpleAgentError(Exception):
    """Base exception for all simple-agent errors.

    All application-specific exceptions inherit from this class,
    allowing users to catch all application errors with a single
    except clause.

    Attributes:
        message: Human-readable error message
        details: Optional dictionary with additional error context
    """

    def __init__(self, message: str, details: Optional[dict] = None):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            details: Optional additional context for debugging
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Get string representation."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


# ============================================================================
# Configuration Errors
# ============================================================================

class ConfigurationError(SimpleAgentError):
    """Base exception for configuration-related errors."""

    pass


class InvalidProviderError(ConfigurationError):
    """Raised when an invalid provider is specified."""

    def __init__(self, provider: str, available: Optional[list] = None):
        """Initialize the exception.

        Args:
            provider: The invalid provider name
            available: List of available providers
        """
        details = {"provider": provider}
        if available:
            details["available"] = ", ".join(available)
        super().__init__(
            f"Unknown provider: '{provider}'",
            details=details
        )


class MissingApiKeyError(ConfigurationError):
    """Raised when required API key is missing."""

    def __init__(self, provider: str):
        """Initialize the exception.

        Args:
            provider: The provider missing the API key
        """
        super().__init__(
            f"API key not found for provider '{provider}'. "
            f"Set the {provider.upper()}_API_KEY environment variable.",
            details={"provider": provider}
        )


class InvalidModelError(ConfigurationError):
    """Raised when an invalid model is specified."""

    def __init__(self, model: str, provider: str):
        """Initialize the exception.

        Args:
            model: The invalid model name
            provider: The provider
        """
        super().__init__(
            f"Invalid model '{model}' for provider '{provider}'",
            details={"model": model, "provider": provider}
        )


# ============================================================================
# Security Errors
# ============================================================================

class SecurityError(SimpleAgentError):
    """Base exception for security-related errors."""

    pass


class PathTraversalError(SecurityError):
    """Raised when a path traversal attempt is detected."""

    def __init__(self, path: str, workspace: str):
        """Initialize the exception.

        Args:
            path: The suspicious path
            workspace: The workspace root
        """
        super().__init__(
            f"Path escapes workspace: '{path}'",
            details={"path": path, "workspace": workspace}
        )


class CommandInjectionError(SecurityError):
    """Raised when a command injection attempt is detected."""

    def __init__(self, command: str, reason: str):
        """Initialize the exception.

        Args:
            command: The suspicious command
            reason: Why it was blocked
        """
        super().__init__(
            f"Command blocked: {reason}",
            details={"command": command}
        )


class UnsafeCommandError(SecurityError):
    """Raised when a potentially unsafe command is executed."""

    def __init__(self, command: str, risk_level: str):
        """Initialize the exception.

        Args:
            command: The unsafe command
            risk_level: The detected risk level
        """
        super().__init__(
            f"Unsafe command (risk: {risk_level}): '{command[:60]}...'",
            details={"command": command, "risk_level": risk_level}
        )


# ============================================================================
# Tool Errors
# ============================================================================

class ToolError(SimpleAgentError):
    """Base exception for tool-related errors."""

    pass


class ToolExecutionError(ToolError):
    """Raised when a tool execution fails."""

    def __init__(self, tool: str, reason: str):
        """Initialize the exception.

        Args:
            tool: The tool name
            reason: Why execution failed
        """
        super().__init__(
            f"Tool '{tool}' execution failed: {reason}",
            details={"tool": tool}
        )


class ToolTimeoutError(ToolError):
    """Raised when a tool execution times out."""

    def __init__(self, tool: str, timeout: int):
        """Initialize the exception.

        Args:
            tool: The tool name
            timeout: The timeout duration in seconds
        """
        super().__init__(
            f"Tool '{tool}' timed out after {timeout} seconds",
            details={"tool": tool, "timeout": timeout}
        )


class ToolNotFoundError(ToolError):
    """Raised when a requested tool doesn't exist."""

    def __init__(self, tool: str):
        """Initialize the exception.

        Args:
            tool: The missing tool name
        """
        super().__init__(
            f"Tool '{tool}' not found",
            details={"tool": tool}
        )


# ============================================================================
# Provider Errors
# ============================================================================

class ProviderError(SimpleAgentError):
    """Base exception for provider-related errors."""

    pass


class ProviderConnectionError(ProviderError):
    """Raised when provider connection fails."""

    def __init__(self, provider: str, reason: str):
        """Initialize the exception.

        Args:
            provider: The provider name
            reason: Connection failure reason
        """
        super().__init__(
            f"Failed to connect to {provider}: {reason}",
            details={"provider": provider}
        )


class ProviderResponseError(ProviderError):
    """Raised when provider returns an invalid response."""

    def __init__(self, provider: str, reason: str):
        """Initialize the exception.

        Args:
            provider: The provider name
            reason: What was wrong with the response
        """
        super().__init__(
            f"Invalid response from {provider}: {reason}",
            details={"provider": provider}
        )


class RateLimitError(ProviderError):
    """Raised when provider rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: Optional[int] = None):
        """Initialize the exception.

        Args:
            provider: The provider name
            retry_after: Optional seconds to wait before retry
        """
        message = f"Rate limit exceeded for {provider}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(
            message,
            details={"provider": provider, "retry_after": retry_after}
        )


# ============================================================================
# Task Errors
# ============================================================================

class TaskError(SimpleAgentError):
    """Base exception for task-related errors."""

    pass


class TaskNotFoundError(TaskError):
    """Raised when a task is not found."""

    def __init__(self, task_id: int):
        """Initialize the exception.

        Args:
            task_id: The missing task ID
        """
        super().__init__(
            f"Task {task_id} not found",
            details={"task_id": task_id}
        )


class TaskValidationError(TaskError):
    """Raised when task validation fails."""

    def __init__(self, reason: str, field: Optional[str] = None):
        """Initialize the exception.

        Args:
            reason: Validation failure reason
            field: Optional field that failed validation
        """
        details = {"reason": reason}
        if field:
            details["field"] = field
        super().__init__(
            f"Task validation failed: {reason}",
            details=details
        )


class TodoLimitError(TaskError):
    """Raised when todo limit is exceeded."""

    def __init__(self, count: int, limit: int):
        """Initialize the exception.

        Args:
            count: Current todo count
            limit: Maximum allowed
        """
        super().__init__(
            f"Todo limit exceeded: {count} > {limit}",
            details={"count": count, "limit": limit}
        )


# ============================================================================
# Permission Errors
# ============================================================================

class PermissionError(SimpleAgentError):
    """Base exception for permission-related errors."""

    pass


class PermissionDeniedError(PermissionError):
    """Raised when permission is denied."""

    def __init__(self, tool: str, reason: str):
        """Initialize the exception.

        Args:
            tool: The tool that was denied
            reason: Why permission was denied
        """
        super().__init__(
            f"Permission denied for '{tool}': {reason}",
            details={"tool": tool, "reason": reason}
        )


class InvalidPolicyError(PermissionError):
    """Raised when an invalid permission policy is used."""

    def __init__(self, policy: str, reason: str):
        """Initialize the exception.

        Args:
            policy: The invalid policy
            reason: Why it's invalid
        """
        super().__init__(
            f"Invalid policy '{policy}': {reason}",
            details={"policy": policy}
        )


# ============================================================================
# Container Errors
# ============================================================================

class ContainerError(SimpleAgentError):
    """Base exception for DI container errors."""

    pass


class ServiceNotFoundError(ContainerError):
    """Raised when a service is not found in the container."""

    def __init__(self, service: str, available: Optional[list] = None):
        """Initialize the exception.

        Args:
            service: The missing service name
            available: Optional list of available services
        """
        details = {"service": service}
        if available:
            details["available"] = ", ".join(available)
        super().__init__(
            f"Service '{service}' not registered",
            details=details
        )


class ServiceValidationError(ContainerError):
    """Raised when service validation fails."""

    def __init__(self, service: str, reason: str):
        """Initialize the exception.

        Args:
            service: The service name
            reason: Validation failure reason
        """
        super().__init__(
            f"Service '{service}' validation failed: {reason}",
            details={"service": service}
        )


# ============================================================================
# Project Errors
# ============================================================================

class ProjectError(SimpleAgentError):
    """Base exception for project-related errors."""

    pass


class ProjectNotFoundError(ProjectError):
    """Raised when a project is not found."""

    def __init__(self, project_id: str):
        """Initialize the exception.

        Args:
            project_id: The missing project ID
        """
        super().__init__(
            f"Project '{project_id}' not found",
            details={"project_id": project_id}
        )


class ProjectValidationError(ProjectError):
    """Raised when project validation fails."""

    def __init__(self, reason: str, project_id: Optional[str] = None):
        """Initialize the exception.

        Args:
            reason: Validation failure reason
            project_id: Optional project ID that failed validation
        """
        details = {"reason": reason}
        if project_id:
            details["project_id"] = project_id
        super().__init__(
            f"Project validation failed: {reason}",
            details=details
        )


# ============================================================================
# Session Errors
# ============================================================================

class SessionError(SimpleAgentError):
    """Base exception for session-related errors."""

    pass


class SessionNotFoundError(SessionError):
    """Raised when a session is not found."""

    def __init__(self, session_id: str, project_id: Optional[str] = None):
        """Initialize the exception.

        Args:
            session_id: The missing session ID
            project_id: Optional project ID
        """
        details = {"session_id": session_id}
        if project_id:
            details["project_id"] = project_id
        message = f"Session '{session_id}' not found"
        if project_id:
            message += f" in project '{project_id}'"
        super().__init__(message, details=details)


class SessionValidationError(SessionError):
    """Raised when session validation fails."""

    def __init__(self, reason: str, session_id: Optional[str] = None):
        """Initialize the exception.

        Args:
            reason: Validation failure reason
            session_id: Optional session ID that failed validation
        """
        details = {"reason": reason}
        if session_id:
            details["session_id"] = session_id
        super().__init__(
            f"Session validation failed: {reason}",
            details=details
        )


# ============================================================================
# Convenience exports
# ============================================================================

__all__ = [
    # Base
    "SimpleAgentError",

    # Configuration
    "ConfigurationError",
    "InvalidProviderError",
    "MissingApiKeyError",
    "InvalidModelError",

    # Security
    "SecurityError",
    "PathTraversalError",
    "CommandInjectionError",
    "UnsafeCommandError",

    # Tools
    "ToolError",
    "ToolExecutionError",
    "ToolTimeoutError",
    "ToolNotFoundError",

    # Providers
    "ProviderError",
    "ProviderConnectionError",
    "ProviderResponseError",
    "RateLimitError",

    # Tasks
    "TaskError",
    "TaskNotFoundError",
    "TaskValidationError",
    "TodoLimitError",

    # Permissions
    "PermissionError",
    "PermissionDeniedError",
    "InvalidPolicyError",

    # Container
    "ContainerError",
    "ServiceNotFoundError",
    "ServiceValidationError",

    # Projects
    "ProjectError",
    "ProjectNotFoundError",
    "ProjectValidationError",

    # Sessions
    "SessionError",
    "SessionNotFoundError",
    "SessionValidationError",
]
