"""Tests for SkillLoader exception handling."""

import pytest

from simple_agent.exceptions import SkillNotFoundError
from simple_agent.managers.skill import SkillLoader


class TestSkillLoaderExceptions:
    """Test standardized skill exceptions."""

    def test_load_missing_skill_raises_not_found(self, mock_settings):
        """Missing skills should raise SkillNotFoundError."""
        loader = SkillLoader(settings=mock_settings)

        with pytest.raises(SkillNotFoundError):
            loader.load("missing-skill")
