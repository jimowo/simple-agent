"""Tests for Settings path derivation behavior."""

from pathlib import Path

from simple_agent.models.config import create_settings


class TestSettingsPathDerivation:
    """Ensure derived directories stay aligned with workdir."""

    def test_workdir_override_updates_all_default_directories(self, temp_workspace):
        """Default directories should derive from the overridden workdir."""
        settings = create_settings(workdir=temp_workspace)

        assert settings.workdir == temp_workspace
        assert settings.team_dir == temp_workspace / ".team"
        assert settings.inbox_dir == temp_workspace / ".team" / "inbox"
        assert settings.tasks_dir == temp_workspace / ".tasks"
        assert settings.skills_dir == temp_workspace / "skills"
        assert settings.transcript_dir == temp_workspace / ".transcripts"
        assert settings.logs_dir == temp_workspace / ".logs"
        assert settings.projects_root == temp_workspace / ".simple" / "projects"
        assert settings.memory_dir == temp_workspace / ".simple" / "memory"

    def test_explicit_directory_overrides_are_preserved(self, temp_workspace):
        """Caller-provided directories should not be replaced by derived defaults."""
        custom_logs = temp_workspace / "custom-logs"
        settings = create_settings(
            workdir=temp_workspace,
            logs_dir=custom_logs,
            projects_root=Path("relative-projects"),
        )

        assert settings.logs_dir == custom_logs
        assert settings.projects_root == Path("relative-projects")
