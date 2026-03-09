"""Skill loader for specialized knowledge."""

import re
from pathlib import Path
from simple_agent.models.config import Settings


class SkillLoader:
    """Loader for skill files."""

    def __init__(self, skills_dir: Path = None, settings: Settings = None):
        self.settings = settings or Settings()
        self.skills_dir = skills_dir or self.settings.skills_dir
        self.skills = {}
        self._load_skills()

    def _load_skills(self):
        """Load all skill files from directory."""
        if self.skills_dir.exists():
            for f in sorted(self.skills_dir.glob("*.md")):
                text = f.read_text()
                meta, body = {}, text
                match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
                if match:
                    for line in match.group(1).strip().splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            meta[k.strip()] = v.strip()
                    body = match.group(2).strip()
                self.skills[f.stem] = {"meta": meta, "body": body}

    def descriptions(self) -> str:
        """Get descriptions of all skills."""
        if not self.skills:
            return "(no skills)"
        return "\n".join(f"  - {n}: {s['meta'].get('description', '-')}" for n, s in self.skills.items())

    def load(self, name: str) -> str:
        """Load a skill by name."""
        s = self.skills.get(name)
        if not s:
            return f"Error: Unknown skill '{name}'. Available: {', '.join(self.skills.keys())}"
        return f"<skill name=\"{name}\">\n{s['body']}\n</skill>"
