"""Permission system for dangerous operations.

This module implements a permission confirmation system following SOLID principles:
- Single Responsibility Principle (SRP): Each class has one clear responsibility
- Open/Closed Principle (OCP): New permission types can be added without modification
- Dependency Inversion Principle (DIP): Uses protocols for interfaces
"""

from simple_agent.permissions.manager import PermissionManager
from simple_agent.permissions.models import PermissionPolicy, PermissionRequest

__all__ = [
    "PermissionManager",
    "PermissionPolicy",
    "PermissionRequest",
]
