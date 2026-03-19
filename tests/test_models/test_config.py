"""Tests for Settings path derivation behavior."""

from pathlib import Path

from simple_agent.models.config import create_settings
from simple_agent.utils.path_utils import path_to_project_id


class TestSettingsPathDerivation:
    """Ensure derived directories stay aligned with workdir."""

    def test_workdir_override_updates_all_default_directories(self, temp_workspace):
        """Default directories should derive from the overridden workdir."""
        settings = create_settings(workdir=temp_workspace)
        project_id = path_to_project_id(temp_workspace.resolve())
        workspace_state_dir = settings.simple_home / "workspaces" / project_id

        assert settings.workdir == temp_workspace
        assert settings.simple_home == Path.home() / ".simple"
        assert settings.team_dir == workspace_state_dir / "team"
        assert settings.inbox_dir == workspace_state_dir / "team" / "inbox"
        assert settings.tasks_dir == workspace_state_dir / "tasks"
        assert settings.skills_dir == temp_workspace / "skills"
        assert settings.transcript_dir == workspace_state_dir / "transcripts"
        assert settings.logs_dir == settings.simple_home / "logs"
        assert settings.projects_root == settings.simple_home / "projects"
        assert settings.memory_dir == settings.simple_home / "memory"

    def test_explicit_directory_overrides_are_preserved(self, temp_workspace):
        """Caller-provided directories should not be replaced by derived defaults."""
        custom_logs = temp_workspace / "custom-logs"
        custom_home = temp_workspace / "simple-home"
        settings = create_settings(
            workdir=temp_workspace,
            simple_home=custom_home,
            logs_dir=custom_logs,
            projects_root=Path("relative-projects"),
        )

        assert settings.simple_home == custom_home
        assert settings.logs_dir == custom_logs
        assert settings.projects_root == Path("relative-projects")
