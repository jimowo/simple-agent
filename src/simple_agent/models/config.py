"""Configuration models using Pydantic BaseSettings.

This module follows SOLID principles:
- Single Responsibility Principle (SRP): Settings holds config, ProviderConfigFactory creates configs
- Open/Closed Principle (OCP): New providers can be added without modifying Settings
"""

import os
from pathlib import Path
from typing import Dict, Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback for minimal environments
    def load_dotenv(*args, **kwargs) -> bool:
        """Fallback no-op when python-dotenv is unavailable."""
        return False
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings

from simple_agent.exceptions import InvalidProviderError

# Global flag to track if initialization has been done
_config_initialized = False


def initialize_config(load_dotenv_override: bool = True) -> None:
    """Initialize configuration by loading environment variables.

    This function should be called explicitly at application startup
    rather than having side effects at module import time.

    Args:
        load_dotenv_override: Whether to override existing environment variables
            with values from .env file. Defaults to True.

    Example:
        >>> from simple_agent.models.config import initialize_config
        >>> initialize_config()
        >>> settings = Settings()
    """
    global _config_initialized

    # Load .env file
    load_dotenv(override=load_dotenv_override)

    # Handle Anthropic-specific environment variable conflict
    # When ANTHROPIC_BASE_URL is set, remove ANTHROPIC_AUTH_TOKEN to avoid conflicts
    if os.getenv("ANTHROPIC_BASE_URL"):
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

    _config_initialized = True


def _ensure_config_initialized() -> None:
    """Ensure configuration is initialized (for backward compatibility).

    This function is called internally to maintain backward compatibility
    with code that doesn't explicitly call initialize_config().

    DEPRECATED: New code should call initialize_config() explicitly.
    """
    global _config_initialized
    if not _config_initialized:
        initialize_config()


class ProviderConfig(BaseModel):
    """Configuration for a single AI provider.

    This class follows the Single Responsibility Principle (SRP)
    by solely holding provider configuration data.
    """

    api_key: Optional[str] = None
    base_url: Optional[str] = None
    models: list = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class Settings(BaseSettings):
    """Application settings with environment variable support.

    This class follows the Single Responsibility Principle (SRP)
    by solely being responsible for holding configuration data.
    All factory logic has been moved to ProviderConfigFactory.
    """

    # Directory paths
    workdir: Path = Field(default_factory=lambda: Path.cwd())
    team_dir: Path = Field(default_factory=lambda: Path.cwd() / ".team")
    inbox_dir: Path = Field(default_factory=lambda: Path.cwd() / ".team" / "inbox")
    tasks_dir: Path = Field(default_factory=lambda: Path.cwd() / ".tasks")
    skills_dir: Path = Field(default_factory=lambda: Path.cwd() / "skills")
    transcript_dir: Path = Field(default_factory=lambda: Path.cwd() / ".transcripts")
    logs_dir: Path = Field(default_factory=lambda: Path.cwd() / ".logs")

    # Project and session configuration
    projects_root: Path = Field(
        default_factory=lambda: Path.cwd() / ".simple" / "projects",
        alias="PROJECTS_ROOT"
    )
    auto_archive_days: int = Field(
        default=30,
        alias="AUTO_ARCHIVE_DAYS"
    )
    max_sessions_per_project: int = Field(
        default=100,
        alias="MAX_SESSIONS_PER_PROJECT"
    )

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

    # Memory system settings
    memory_enabled: bool = Field(default=True, alias="MEMORY_ENABLED")
    memory_backend: str = Field(default="chroma", alias="MEMORY_BACKEND")
    memory_dir: Path = Field(
        default_factory=lambda: Path.cwd() / ".simple" / "memory",
        alias="MEMORY_DIR"
    )
    # OpenAI Embeddings configuration
    memory_encoder: str = Field(default="openai", alias="MEMORY_ENCODER")
    memory_openai_base_url: Optional[str] = Field(default=None, alias="MEMORY_OPENAI_BASE_URL")
    memory_openai_api_key: Optional[str] = Field(default=None, alias="MEMORY_OPENAI_API_KEY")
    memory_openai_model: str = Field(default="text-embedding-3-small", alias="MEMORY_OPENAI_MODEL")
    memory_openai_embedding_dim: int = Field(default=1536, alias="MEMORY_OPENAI_EMBEDDING_DIM")
    # Forgetting policy
    memory_max_entries: int = Field(default=10000, ge=1, alias="MEMORY_MAX_ENTRIES")
    memory_forget_policy: str = Field(default="lru", alias="MEMORY_FORGET_POLICY")

    # Search API settings
    search_api: str = Field(default="duckduckgo", alias="SEARCH_API")
    google_search_api_key: Optional[str] = Field(default=None, alias="GOOGLE_SEARCH_API_KEY")
    google_search_engine_id: Optional[str] = Field(default=None, alias="GOOGLE_SEARCH_ENGINE_ID")
    bing_search_api_key: Optional[str] = Field(default=None, alias="BING_SEARCH_API_KEY")
    serpapi_api_key: Optional[str] = Field(default=None, alias="SERPAPI_API_KEY")
    web_timeout: int = Field(default=20, alias="WEB_TIMEOUT")

    model_config = ConfigDict(extra="allow", env_file=".env")

    def get_active_provider(self) -> str:
        """Get the active provider name (runtime override or default).

        Returns:
            Provider name string
        """
        return self.provider or self.default_provider


class ProviderConfigFactory:
    """Factory for creating provider configurations.

    This class follows the Single Responsibility Principle (SRP) by
    solely being responsible for creating provider configurations.
    It supports the Open/Closed Principle (OCP) by allowing new
    providers to be registered without modifying the class.

    The factory encapsulates knowledge about default models and
    environment variable mappings for each provider.
    """

    # Default models for each provider
    DEFAULT_MODELS: Dict[str, list] = {
        "anthropic": ["claude-sonnet-4-20250514"],
        "openai": ["gpt-4o"],
        "gemini": ["gemini-2.5-flash-preview-04-17"],
        "groq": ["llama-3.3-70b-versatile"],
        "local": ["llama3.2"],
    }

    # Environment variable names for API keys
    ENV_KEY_MAP: Dict[str, Optional[str]] = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "local": None,  # Local models don't need API keys
    }

    # Default base URLs
    DEFAULT_BASE_URLS: Dict[str, Optional[str]] = {
        "local": "http://localhost:11434/v1",
        # Other providers use their default URLs
    }

    @classmethod
    def create_config(cls, settings: Settings, provider_name: str) -> ProviderConfig:
        """Create provider configuration from settings.

        This method follows the Open/Closed Principle (OCP) by
        allowing new providers to be added to the class-level
        dictionaries without modifying this method.

        Args:
            settings: Application settings
            provider_name: Name of the provider

        Returns:
            ProviderConfig instance

        Raises:
            ValueError: If provider is unknown
        """
        # Check if provider has explicit config in settings
        if provider_name in settings.providers:
            return settings.providers[provider_name]

        # Validate provider name
        if provider_name not in cls.DEFAULT_MODELS:
            available = list(cls.DEFAULT_MODELS.keys())
            raise InvalidProviderError(provider_name, available)

        # Create default configuration
        config = ProviderConfig()

        # Set models
        config.models = cls.DEFAULT_MODELS.get(provider_name, [])

        # Set API key from environment
        env_key = cls.ENV_KEY_MAP.get(provider_name)
        if env_key:
            config.api_key = os.getenv(env_key)

        # Set base URL if provider has a custom default
        if provider_name in cls.DEFAULT_BASE_URLS:
            config.base_url = cls.DEFAULT_BASE_URLS[provider_name]

        # Handle special Anthropic base URL setting
        if provider_name == "anthropic" and settings.anthropic_base_url:
            config.base_url = settings.anthropic_base_url

        return config

    @classmethod
    def register_provider(
        cls,
        name: str,
        models: list,
        env_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """Register a new provider.

        This method supports the Open/Closed Principle (OCP) by
        allowing new providers to be added at runtime without
        modifying the source code.

        Args:
            name: Provider name
            models: List of default models
            env_key: Environment variable name for API key (optional)
            base_url: Default base URL (optional)

        Example:
            ProviderConfigFactory.register_provider(
                "custom",
                models=["custom-model-1"],
                env_key="CUSTOM_API_KEY",
                base_url="https://api.example.com"
            )
        """
        cls.DEFAULT_MODELS[name] = models
        cls.ENV_KEY_MAP[name] = env_key
        if base_url:
            cls.DEFAULT_BASE_URLS[name] = base_url


def create_settings(**kwargs) -> Settings:
    """Create Settings instance with optional overrides.

    This is a convenience factory function for creating Settings
    with runtime overrides. It ensures configuration is initialized
    before creating the Settings instance.

    Args:
        **kwargs: Settings overrides

    Returns:
        Settings instance

    Example:
        >>> from simple_agent.models.config import create_settings
        >>> settings = create_settings(workdir=Path("/custom/path"))
    """
    # Ensure config is initialized (for backward compatibility)
    _ensure_config_initialized()
    return Settings(**kwargs)


# Public API exports
__all__ = [
    "ProviderConfig",
    "Settings",
    "ProviderConfigFactory",
    "create_settings",
    "initialize_config",
]
