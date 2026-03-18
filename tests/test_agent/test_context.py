"""Test Agent context and dependency injection."""

from unittest.mock import Mock, patch

from simple_agent.agent.context import AgentContext
from simple_agent.models.config import Settings
from simple_agent.providers.base import BaseProvider


class TestAgentContext:
    """Test AgentContext dataclass."""

    def test_create_context(self, mock_settings, mock_provider):
        """Test creating an AgentContext."""
        from simple_agent.managers.background import BackgroundManager
        from simple_agent.managers.message import MessageBus
        from simple_agent.managers.project import ProjectManager
        from simple_agent.managers.session import SessionManager
        from simple_agent.managers.skill import SkillLoader
        from simple_agent.managers.task import TaskManager
        from simple_agent.managers.teammate import TeammateManager
        from simple_agent.managers.todo import TodoManager

        todo = TodoManager()
        task = TaskManager(mock_settings)
        bg = BackgroundManager(mock_settings)
        bus = MessageBus(mock_settings)
        skill = SkillLoader(settings=mock_settings)
        teammate = TeammateManager(bus, task, mock_settings)
        project = ProjectManager(mock_settings)
        session = SessionManager(mock_settings)

        context = AgentContext(
            settings=mock_settings,
            todo=todo,
            task_mgr=task,
            bg=bg,
            bus=bus,
            skill_loader=skill,
            teammate=teammate,
            project_mgr=project,
            session_mgr=session,
            memory_mgr=None,
            provider=mock_provider,
        )

        assert context.settings is mock_settings
        assert context.todo is todo
        assert context.task_mgr is task
        assert context.bg is bg
        assert context.bus is bus
        assert context.skill_loader is skill
        assert context.teammate is teammate
        assert context.project_mgr is project
        assert context.session_mgr is session
        assert context.provider is mock_provider

    def test_system_prompt_property(self, initialized_context):
        """Test system_prompt property."""
        prompt = initialized_context.system_prompt

        assert isinstance(prompt, str)
        assert str(initialized_context.settings.workdir) in prompt
        assert "TodoWrite" in prompt
        assert "load_skill" in prompt

    def test_system_prompt_includes_skills(self, initialized_context):
        """Test that system prompt includes available skills."""
        prompt = initialized_context.system_prompt

        assert "Skills available" in prompt

    def test_from_components(self, mock_settings, mock_provider):
        """Test creating context from already-resolved dependencies."""
        from simple_agent.managers.background import BackgroundManager
        from simple_agent.managers.message import MessageBus
        from simple_agent.managers.project import ProjectManager
        from simple_agent.managers.session import SessionManager
        from simple_agent.managers.skill import SkillLoader
        from simple_agent.managers.task import TaskManager
        from simple_agent.managers.teammate import TeammateManager
        from simple_agent.managers.todo import TodoManager

        todo = TodoManager()
        task = TaskManager(mock_settings)
        bg = BackgroundManager(mock_settings)
        bus = MessageBus(mock_settings)
        skill = SkillLoader(settings=mock_settings)
        teammate = TeammateManager(bus, task, mock_settings)
        project = ProjectManager(mock_settings)
        session = SessionManager(mock_settings)

        context = AgentContext.from_components(
            settings=mock_settings,
            provider=mock_provider,
            todo=todo,
            task_mgr=task,
            bg=bg,
            bus=bus,
            skill_loader=skill,
            teammate=teammate,
            project_mgr=project,
            session_mgr=session,
            memory_mgr=None,
        )

        assert context.settings is mock_settings
        assert context.provider is mock_provider
        assert context.project_mgr is project
        assert context.session_mgr is session

    def test_from_container(self, temp_workspace):
        """Test creating context from service container."""
        from simple_agent.core.container import reset_container

        # Reset to ensure clean state
        reset_container()

        settings = Settings(
            workdir=temp_workspace,
            tasks_dir=temp_workspace / "tasks",
            inbox_dir=temp_workspace / "inbox",
            skills_dir=temp_workspace / "skills",
            team_dir=temp_workspace / "team",
            transcript_dir=temp_workspace / "transcripts",
        )

        # Mock the provider creation
        with patch('simple_agent.core.service_registration._create_provider') as mock_create_provider:
            mock_provider = Mock(spec=BaseProvider)
            mock_create_provider.return_value = mock_provider

            context = AgentContext.from_container(settings)

            assert context.settings is settings
            assert context.provider is mock_provider
            assert context.todo is not None
            assert context.task_mgr is not None
            assert context.bg is not None
            assert context.bus is not None
            assert context.skill_loader is not None
            assert context.teammate is not None
            assert context.project_mgr is not None
            assert context.session_mgr is not None

    def test_from_container_respects_manager_overrides(self, temp_workspace):
        """Test creating context with caller-provided stateful manager instances."""
        from simple_agent.core.container import reset_container
        from simple_agent.managers.project import ProjectManager
        from simple_agent.managers.session import SessionManager

        reset_container()
        settings = Settings(workdir=temp_workspace)
        project_mgr = ProjectManager(settings)
        session_mgr = SessionManager(settings)

        with patch('simple_agent.core.service_registration._create_provider') as mock_create_provider:
            mock_provider = Mock(spec=BaseProvider)
            mock_create_provider.return_value = mock_provider

            context = AgentContext.from_container(
                settings,
                project_mgr=project_mgr,
                session_mgr=session_mgr,
            )

        assert context.project_mgr is project_mgr
        assert context.session_mgr is session_mgr


class TestContextIntegration:
    """Test AgentContext integration with other components."""

    def test_context_dependencies_are_consistent(self, initialized_context):
        """Test that context dependencies are properly wired."""
        # The same Settings instance should be used throughout
        assert initialized_context.task_mgr.settings is initialized_context.settings
        assert initialized_context.bg.settings is initialized_context.settings

    def test_context_managers_are_unique_instances(self, initialized_context):
        """Test that each manager is a unique instance."""
        # Different managers should be different instances
        assert initialized_context.todo is not initialized_context.task_mgr
        assert initialized_context.bg is not initialized_context.bus
        assert initialized_context.teammate is not initialized_context.skill_loader
