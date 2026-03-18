"""Skill loader for specialized knowledge."""

import re
from pathlib import Path

from simple_agent.exceptions import SkillNotFoundError
from simple_agent.managers.base import BaseManager


class SkillLoader(BaseManager):
    """Loader for skill files."""

    def __init__(self, skills_dir: Path = None, settings=None):
        """Initialize the skill loader.

        Args:
            skills_dir: Optional path to skills directory
            settings: Optional Settings instance
        """
        super().__init__(settings)
        self.skills_dir = skills_dir or self.settings.skills_dir
        self.skills = {}
        self._load_skills()

    def _load_skills(self):
        """Load all skill files from directory.

        Supports two directory structures:
        1. Flat: skills/*.md
        2. Nested: skills/<skill-name>/SKILL.md
        """
        if not self.skills_dir.exists():
            return

        # First, look for SKILL.md files in subdirectories
        for skill_dir in sorted(self.skills_dir.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    self._load_skill_file(skill_file, skill_dir.name)
                    continue

                # Also check for lowercase skill.md
                skill_file_lower = skill_dir / "skill.md"
                if skill_file_lower.exists():
                    self._load_skill_file(skill_file_lower, skill_dir.name)
                    continue

        # Then, load any .md files directly in skills directory
        for f in sorted(self.skills_dir.glob("*.md")):
            self._load_skill_file(f, f.stem)

    def _load_skill_file(self, file_path: Path, skill_name: str) -> None:
        """Load a single skill file.

        Args:
            file_path: Path to the skill file
            skill_name: Name to use for the skill
        """
        text = file_path.read_text()
        meta, body = {}, text
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if match:
            for line in match.group(1).strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = match.group(2).strip()
        self.skills[skill_name] = {"meta": meta, "body": body}

    def descriptions(self) -> str:
        """Get descriptions of all skills."""
        if not self.skills:
            return "(no skills)"
        return "\n".join(
            f"  - {n}: {s['meta'].get('description', '-')}" for n, s in self.skills.items()
        )

    def load(self, name: str) -> str:
        """Load a skill by name."""
        s = self.skills.get(name)
        if not s:
            raise SkillNotFoundError(name, sorted(self.skills.keys()))
        return f'<skill name="{name}">\n{s["body"]}\n</skill>'
