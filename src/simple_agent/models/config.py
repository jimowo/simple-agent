"""Configuration models using Pydantic BaseSettings."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Directory paths
    workdir: Path = Field(default_factory=lambda: Path.cwd())
    team_dir: Path = Field(default_factory=lambda: Path.cwd() / ".team")
    inbox_dir: Path = Field(default_factory=lambda: Path.cwd() / ".team" / "inbox")
    tasks_dir: Path = Field(default_factory=lambda: Path.cwd() / ".tasks")
    skills_dir: Path = Field(default_factory=lambda: Path.cwd() / "skills")
    transcript_dir: Path = Field(default_factory=lambda: Path.cwd() / ".transcripts")

    # Anthropic API
    anthropic_base_url: Optional[str] = Field(default=None, alias="ANTHROPIC_BASE_URL")
    model_id: str = Field(default="", alias="MODEL_ID")

    # Agent settings
    token_threshold: int = Field(default=100000, alias="TOKEN_THRESHOLD")
    max_tokens: int = Field(default=8000, alias="MAX_TOKENS")
    poll_interval: int = Field(default=5, alias="POLL_INTERVAL")
    idle_timeout: int = Field(default=60, alias="IDLE_TIMEOUT")

    # Bash settings
    bash_timeout: int = Field(default=120, alias="BASH_TIMEOUT")

    class Config:
        extra = "allow"
        env_file = ".env"


def create_settings(**kwargs) -> Settings:
    """Create Settings instance with optional overrides."""
    return Settings(**kwargs)
