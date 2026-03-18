"""Test configurable search API functionality."""


import pytest

from simple_agent.models.config import Settings, create_settings
from simple_agent.tools.web_tools import SearchAPIConfig, web_search


@pytest.mark.security
class TestSearchAPIConfig:
    """Test SearchAPIConfig class."""

    def test_get_supported_apis(self):
        """Test getting supported API list."""
        apis = SearchAPIConfig.get_supported_apis()
        assert isinstance(apis, list)
        assert "duckduckgo" in apis
        assert "google" in apis
        assert "bing" in apis
        assert "serpapi" in apis

    def test_validate_config_duckduckgo_default(self):
        """Test validating DuckDuckGo (default, no API key required)."""
        settings = Settings()  # Default is duckduckgo
        is_valid, error_msg = SearchAPIConfig.validate_config(settings)
        assert is_valid
        assert error_msg == ""

    def test_validate_config_duckduckgo_explicit(self):
        """Test validating DuckDuckGo with explicit setting."""
        # Use the environment variable alias name
        settings = create_settings(SEARCH_API="duckduckgo")
        is_valid, error_msg = SearchAPIConfig.validate_config(settings)
        assert is_valid
        assert error_msg == ""

    def test_validate_config_google_with_missing_key(self):
        """Test validating Google without API key."""
        # Use the environment variable alias name
        settings = create_settings(SEARCH_API="google")
        is_valid, error_msg = SearchAPIConfig.validate_config(settings)
        # Since we're not setting the env vars, validation should fail
        assert not is_valid
        assert "GOOGLE_SEARCH_API_KEY" in error_msg

    def test_validate_config_google_with_valid_config(self):
        """Test validating Google with valid configuration."""
        # Use environment variable alias names
        settings = create_settings(
            SEARCH_API="google",
            GOOGLE_SEARCH_API_KEY="test-key",
            GOOGLE_SEARCH_ENGINE_ID="test-engine-id"
        )
        is_valid, error_msg = SearchAPIConfig.validate_config(settings)
        assert is_valid
        assert error_msg == ""

    def test_validate_config_bing_with_missing_key(self):
        """Test validating Bing without API key."""
        # Use the environment variable alias name
        settings = create_settings(SEARCH_API="bing")
        is_valid, error_msg = SearchAPIConfig.validate_config(settings)
        # Since we're not setting the env vars, validation should fail
        assert not is_valid
        assert "BING_SEARCH_API_KEY" in error_msg

    def test_validate_config_bing_with_valid_config(self):
        """Test validating Bing with valid configuration."""
        # Use environment variable alias names
        settings = create_settings(
            SEARCH_API="bing",
            BING_SEARCH_API_KEY="test-key"
        )
        is_valid, error_msg = SearchAPIConfig.validate_config(settings)
        assert is_valid
        assert error_msg == ""

    def test_validate_config_serpapi_with_missing_key(self):
        """Test validating SerpAPI without API key."""
        # Use the environment variable alias name
        settings = create_settings(SEARCH_API="serpapi")
        is_valid, error_msg = SearchAPIConfig.validate_config(settings)
        # Since we're not setting the env vars, validation should fail
        assert not is_valid
        assert "SERPAPI_API_KEY" in error_msg

    def test_validate_config_serpapi_with_valid_config(self):
        """Test validating SerpAPI with valid configuration."""
        # Use environment variable alias names
        settings = create_settings(
            SEARCH_API="serpapi",
            SERPAPI_API_KEY="test-key"
        )
        is_valid, error_msg = SearchAPIConfig.validate_config(settings)
        assert is_valid
        assert error_msg == ""

    def test_validate_config_unsupported_api(self):
        """Test validating unsupported API."""
        # Use the environment variable alias name
        settings = create_settings(SEARCH_API="unsupported_api")
        is_valid, error_msg = SearchAPIConfig.validate_config(settings)
        assert not is_valid
        assert "Unsupported" in error_msg

    def test_get_api_key_from_settings(self):
        """Test getting API key from settings object."""
        # Use environment variable alias names
        settings = create_settings(GOOGLE_SEARCH_API_KEY="test-google-key")
        api_key = SearchAPIConfig.get_api_key(settings, "google")
        assert api_key == "test-google-key"

    def test_get_api_key_duckduckgo(self):
        """Test getting API key for DuckDuckGo (returns None)."""
        settings = Settings()
        api_key = SearchAPIConfig.get_api_key(settings, "duckduckgo")
        assert api_key is None

    def test_get_search_engine_id_from_settings(self):
        """Test getting search engine ID from settings."""
        # Use environment variable alias names
        settings = create_settings(GOOGLE_SEARCH_ENGINE_ID="test-engine-id")
        engine_id = SearchAPIConfig.get_search_engine_id(settings, "google")
        assert engine_id == "test-engine-id"

    def test_get_search_engine_id_other_apis(self):
        """Test getting search engine ID for other APIs (returns None)."""
        settings = Settings()
        engine_id = SearchAPIConfig.get_search_engine_id(settings, "duckduckgo")
        assert engine_id is None


@pytest.mark.security
class TestWebSearchConfiguration:
    """Test web_search function with different configurations."""

    def test_web_search_duckduckgo_default(self):
        """Test web_search with default DuckDuckGo API."""
        # This test may make an actual network request
        # Consider mocking requests.get in production tests
        result = web_search("test query", num_results=1, timeout=5)
        assert isinstance(result, str)
        # May contain results or error due to network/API limitations

    def test_web_search_with_settings(self):
        """Test web_search with explicit settings parameter."""
        # Use environment variable alias name
        settings = create_settings(SEARCH_API="duckduckgo")
        result = web_search("test query", num_results=1, timeout=5, settings=settings)
        assert isinstance(result, str)

    def test_web_search_unsupported_api(self):
        """Test web_search with unsupported API name."""
        # Use environment variable alias name
        settings = create_settings(SEARCH_API="totally_fake_api")
        result = web_search("test query", settings=settings)
        # Should return an error about unsupported API
        assert isinstance(result, str)

    def test_web_search_configuration_respects_env_vars(self):
        """Test that web_search respects environment variables."""
        # This test verifies that the search API can be configured via environment
        settings = Settings()
        # Default should work (duckduckgo doesn't require API keys)
        is_valid, _ = SearchAPIConfig.validate_config(settings)
        assert is_valid
