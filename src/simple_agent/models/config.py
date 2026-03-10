"""Configuration models using Pydantic BaseSettings."""

import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)


class ProviderConfig(BaseModel):
    """Configuration for a single AI provider."""

    api_key: Optional[str] = None
    base_url: Optional[str] = None
    models: list = Field(default_factory=list)

    class Config:
        extra = "allow"


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Directory paths
    workdir: Path = Field(default_factory=lambda: Path.cwd())
    team_dir: Path = Field(default_factory=lambda: Path.cwd() / ".team")
    inbox_dir: Path = Field(default_factory=lambda: Path.cwd() / ".team" / "inbox")
    tasks_dir: Path = Field(default_factory=lambda: Path.cwd() / ".tasks")
    skills_dir: Path = Field(default_factory=lambda: Path.cwd() / "skills")
    transcript_dir: Path = Field(default_factory=lambda: Path.cwd() / ".transcripts")

    # Provider settings
    default_provider: str = Field(default="anthropic", alias="DEFAULT_PROVIDER")
    provider: str = Field(default="anthropic", alias="PROVIDER")  # Runtime override

    # API Keys (environment variable fallback)
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")

    # Provider configurations (from config file)
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)

    # Legacy Anthropic settings (for backward compatibility)
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

    def get_provider_config(self, provider_name: str) -> ProviderConfig:
        """Get configuration for a specific provider."""
        if provider_name in self.providers:
            return self.providers[provider_name]

        # Create default config from environment variables
        config = ProviderConfig()
        if provider_name == "anthropic":
            config.api_key = self.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
            config.base_url = self.anthropic_base_url
            config.models = ["claude-sonnet-4-20250514"]
        elif provider_name == "openai":
            config.api_key = self.openai_api_key or os.getenv("OPENAI_API_KEY")
            config.models = ["gpt-4o"]
        elif provider_name == "gemini":
            config.api_key = self.gemini_api_key or os.getenv("GEMINI_API_KEY")
            config.models = ["gemini-2.5-flash-preview-04-17"]
        elif provider_name == "groq":
            config.api_key = self.groq_api_key or os.getenv("GROQ_API_KEY")
            config.models = ["llama-3.3-70b-versatile"]
        elif provider_name == "local":
            config.api_key = "dummy"  # Local models don't need real API key
            config.base_url = "http://localhost:11434/v1"
            config.models = ["llama3.2"]

        return config

    def get_active_provider(self) -> str:
        """Get the active provider name (runtime override or default)."""
        return self.provider or self.default_provider


def create_settings(**kwargs) -> Settings:
    """Create Settings instance with optional overrides."""
    return Settings(**kwargs)
