"""Test dependency injection container."""

import pytest

from simple_agent.core.container import (
    ServiceContainer,
    ServiceDescriptor,
    get_container,
    reset_container,
)


class SimpleService:
    """A simple service for testing."""

    def __init__(self, value: str = "default"):
        self.value = value


class AnotherService:
    """Another service for testing."""

    def __init__(self):
        self.count = 0


class TestServiceContainer:
    """Test ServiceContainer class."""

    def test_register_singleton(self):
        """Test registering a singleton service."""
        container = ServiceContainer()

        container.register_singleton(
            SimpleService,
            lambda c: SimpleService("singleton")
        )

        assert container.has(SimpleService)

    def test_register_transient(self):
        """Test registering a transient service."""
        container = ServiceContainer()

        container.register_transient(
            SimpleService,
            lambda c: SimpleService("transient")
        )

        assert container.has(SimpleService)

    def test_register_instance(self):
        """Test registering an existing instance."""
        container = ServiceContainer()
        instance = SimpleService("instance")

        container.register_instance(SimpleService, instance)

        assert container.has(SimpleService)

    def test_resolve_singleton_same_instance(self):
        """Test that singleton returns the same instance."""
        container = ServiceContainer()

        container.register_singleton(
            SimpleService,
            lambda c: SimpleService("singleton")
        )

        service1 = container.resolve(SimpleService)
        service2 = container.resolve(SimpleService)

        assert service1 is service2
        assert service1.value == "singleton"

    def test_resolve_transient_new_instance(self):
        """Test that transient creates a new instance each time."""
        container = ServiceContainer()

        container.register_transient(
            SimpleService,
            lambda c: SimpleService(f"instance_{id(c)}")
        )

        service1 = container.resolve(SimpleService)
        service2 = container.resolve(SimpleService)

        assert service1 is not service2

    def test_resolve_instance_returns_same(self):
        """Test that registered instance is returned as-is."""
        container = ServiceContainer()
        instance = SimpleService("original")

        container.register_instance(SimpleService, instance)

        resolved = container.resolve(SimpleService)

        assert resolved is instance
        assert resolved.value == "original"

    def test_resolve_unregistered_raises_error(self):
        """Test that resolving unregistered service raises error."""
        container = ServiceContainer()

        with pytest.raises(ValueError, match="not registered"):
            container.resolve(SimpleService)

    def test_resolve_unregistered_shows_available(self):
        """Test error message shows available services."""
        container = ServiceContainer()

        container.register_singleton(SimpleService, lambda c: SimpleService())
        container.register_singleton(AnotherService, lambda c: AnotherService())

        with pytest.raises(ValueError) as exc_info:
            class UnregisteredService:
                pass
            container.resolve(UnregisteredService)

        error_msg = str(exc_info.value)
        assert "not registered" in error_msg
        assert "SimpleService" in error_msg or "AnotherService" in error_msg

    def test_has_returns_true_for_registered(self):
        """Test has() returns True for registered services."""
        container = ServiceContainer()

        container.register_singleton(SimpleService, lambda c: SimpleService())

        assert container.has(SimpleService) is True

    def test_has_returns_false_for_unregistered(self):
        """Test has() returns False for unregistered services."""
        container = ServiceContainer()

        assert container.has(SimpleService) is False

    def test_clear_removes_all_services(self):
        """Test that clear() removes all services."""
        container = ServiceContainer()

        container.register_singleton(SimpleService, lambda c: SimpleService())
        container.register_singleton(AnotherService, lambda c: AnotherService())

        assert container.has(SimpleService)
        assert container.has(AnotherService)

        container.clear()

        assert not container.has(SimpleService)
        assert not container.has(AnotherService)

    def test_factory_receives_container(self):
        """Test that factory receives container as parameter."""
        container = ServiceContainer()
        received_container = {"value": None}

        def factory(c):
            received_container["value"] = c
            return SimpleService()

        container.register_singleton(SimpleService, factory)
        container.resolve(SimpleService)

        assert received_container["value"] is container


class TestGlobalContainer:
    """Test global container functions."""

    def test_get_container_returns_same_instance(self):
        """Test that get_container returns the same instance."""
        reset_container()

        container1 = get_container()
        container2 = get_container()

        assert container1 is container2

    def test_reset_container(self):
        """Test that reset_container creates a new instance."""
        container1 = get_container()

        reset_container()

        container2 = get_container()

        assert container1 is not container2

    def test_get_container_has_default_services(self):
        """Test that global container has default services registered."""
        reset_container()

        container = get_container()

        # Container should have some services registered
        # (The exact services depend on _register_default_services)
        assert len(container._services) > 0


class TestServiceDescriptor:
    """Test ServiceDescriptor dataclass."""

    def test_singleton_descriptor(self):
        """Test creating a singleton descriptor."""
        descriptor = ServiceDescriptor(
            factory=lambda c: SimpleService(),
            singleton=True
        )

        assert descriptor.singleton is True
        assert descriptor.instance is None

    def test_transient_descriptor(self):
        """Test creating a transient descriptor."""
        descriptor = ServiceDescriptor(
            factory=lambda c: SimpleService(),
            singleton=False
        )

        assert descriptor.singleton is False

    def test_post_init_clears_instance(self):
        """Test that __post_init__ clears instance."""
        descriptor = ServiceDescriptor(
            factory=lambda c: SimpleService(),
            singleton=True,
        )
        # Manually set instance to test __post_init__ behavior
        object.__setattr__(descriptor, "instance", "test_value")
        # Now call post_init (it should be called automatically but let's verify the behavior)
        descriptor.__post_init__()

        # __post_init__ should have cleared the instance
        assert descriptor.instance is None
