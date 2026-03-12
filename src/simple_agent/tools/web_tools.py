"""Web tools for fetching and searching web content.

This module provides web_fetch and web_search tools similar to Claude Code's capabilities.
The web_search tool supports multiple search APIs configurable via environment variables.
"""

from typing import TYPE_CHECKING, Dict, Optional

from simple_agent.utils.constants import MAX_WEB_CONTENT_LENGTH
from simple_agent.utils.error_handling import handle_tool_errors

if TYPE_CHECKING:
    from simple_agent.models.config import Settings


class SearchAPIConfig:
    """Configuration for different search APIs.

    This class follows the Single Responsibility Principle (SRP) by
    solely being responsible for managing search API configurations.

    Supported APIs:
    - duckduckgo: Free, no API key required
    - google: Requires API key and Custom Search Engine ID
    - bing: Requires API key
    - serpapi: Requires API key
    """

    # API endpoints and required parameters
    API_CONFIGS: Dict[str, Dict[str, str]] = {
        "duckduckgo": {
            "name": "DuckDuckGo",
            "url": "https://api.duckduckgo.com/",
            "requires_key": False,
        },
        "google": {
            "name": "Google Custom Search",
            "url": "https://www.googleapis.com/customsearch/v1",
            "requires_key": True,
            "key_env": "GOOGLE_SEARCH_API_KEY",
            "cx_env": "GOOGLE_SEARCH_ENGINE_ID",
        },
        "bing": {
            "name": "Bing Search",
            "url": "https://api.bing.microsoft.com/v7.0/search",
            "requires_key": True,
            "key_env": "BING_SEARCH_API_KEY",
            "header_key": "Ocp-Apim-Subscription-Key",
        },
        "serpapi": {
            "name": "SerpAPI",
            "url": "https://serpapi.com/search",
            "requires_key": True,
            "key_env": "SERPAPI_API_KEY",
        },
    }

    @classmethod
    def get_supported_apis(cls) -> list:
        """Get list of supported search API names."""
        return list(cls.API_CONFIGS.keys())

    @classmethod
    def validate_config(cls, settings: "Settings") -> tuple[bool, str]:
        """Validate search API configuration.

        Args:
            settings: Application settings

        Returns:
            Tuple of (is_valid, error_message)
        """
        api_name = settings.search_api.lower()

        if api_name not in cls.API_CONFIGS:
            available = ", ".join(cls.get_supported_apis())
            return False, f"Unsupported search API '{api_name}'. Supported: {available}"

        config = cls.API_CONFIGS[api_name]

        if config["requires_key"]:
            # Check for required API key
            if api_name == "google":
                if not settings.google_search_api_key:
                    return False, "Google Search requires GOOGLE_SEARCH_API_KEY environment variable"
                if not settings.google_search_engine_id:
                    return False, "Google Search requires GOOGLE_SEARCH_ENGINE_ID environment variable"
            elif api_name == "bing":
                if not settings.bing_search_api_key:
                    return False, "Bing Search requires BING_SEARCH_API_KEY environment variable"
            elif api_name == "serpapi":
                if not settings.serpapi_api_key:
                    return False, "SerpAPI requires SERPAPI_API_KEY environment variable"

        return True, ""

    @classmethod
    def get_api_key(cls, settings: "Settings", api_name: str) -> Optional[str]:
        """Get API key for a specific search API.

        Args:
            settings: Application settings
            api_name: Name of the search API

        Returns:
            API key if available, None otherwise
        """
        if api_name == "google":
            return settings.google_search_api_key
        elif api_name == "bing":
            return settings.bing_search_api_key
        elif api_name == "serpapi":
            return settings.serpapi_api_key
        return None

    @classmethod
    def get_search_engine_id(cls, settings: "Settings", api_name: str) -> Optional[str]:
        """Get search engine ID for APIs that require it (e.g., Google).

        Args:
            settings: Application settings
            api_name: Name of the search API

        Returns:
            Search engine ID if available, None otherwise
        """
        if api_name == "google":
            return settings.google_search_engine_id
        return None


@handle_tool_errors
def web_fetch(url: str, timeout: int = 20) -> str:
    """
    Fetch content from a URL.

    Args:
        url: The URL to fetch content from
        timeout: Request timeout in seconds (default 20)

    Returns:
        The fetched content as text, or error message
    """
    try:
        import requests
    except ImportError:
        return "Error: requests library not installed. Install with: pip install requests"

    try:
        response = requests.get(url, timeout=timeout, allow_redirects=True)
        response.raise_for_status()

        # Try to decode as text
        try:
            content = response.text
        except UnicodeDecodeError:
            # Fallback to common encodings
            for encoding in ["utf-8", "gbk", "latin1"]:
                try:
                    content = response.content.decode(encoding)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                content = str(response.content)

        # Truncate if too long
        if len(content) > MAX_WEB_CONTENT_LENGTH:
            content = content[:MAX_WEB_CONTENT_LENGTH]
            content += f"\n\n... (Content truncated, total length: {len(response.text)} chars)"

        return content

    except requests.Timeout:
        return f"Error: Request timed out after {timeout} seconds"
    except requests.RequestException as e:
        return f"Error: Failed to fetch URL: {e}"
    except Exception as e:
        return f"Error: {e}"


@handle_tool_errors
def web_search(
    query: str,
    num_results: int = 10,
    timeout: int = 10,
    settings: Optional["Settings"] = None,
) -> str:
    """
    Search the web using a configurable search engine.

    The search API can be configured via the SEARCH_API environment variable.
    Supported APIs: duckduckgo (default), google, bing, serpapi.

    Args:
        query: Search query string
        num_results: Number of results to return (default 10)
        timeout: Request timeout in seconds (default 10)
        settings: Optional application settings for API configuration

    Returns:
        Search results as formatted text
    """
    try:
        import requests
    except ImportError:
        return "Error: requests library not installed. Install with: pip install requests"

    # Load settings if not provided
    if settings is None:
        from simple_agent.models.config import Settings
        settings = Settings()

    # Get search API configuration
    api_name = settings.search_api.lower()

    # Validate configuration
    is_valid, error_msg = SearchAPIConfig.validate_config(settings)
    if not is_valid:
        return f"Error: {error_msg}"

    # Route to appropriate search implementation
    if api_name == "duckduckgo":
        return _search_duckduckgo(query, num_results, timeout)
    elif api_name == "google":
        return _search_google(query, num_results, timeout, settings)
    elif api_name == "bing":
        return _search_bing(query, num_results, timeout, settings)
    elif api_name == "serpapi":
        return _search_serpapi(query, num_results, timeout, settings)
    else:
        return f"Error: Unsupported search API '{api_name}'"


def _search_duckduckgo(query: str, num_results: int, timeout: int) -> str:
    """Search using DuckDuckGo Instant Answer API (free, no API key)."""
    try:
        import requests
    except ImportError:
        return "Error: requests library not installed. Install with: pip install requests"

    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
        }

        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        results.append(f"Search results for: {query}\n")

        # Add abstract if available
        if "Abstract" in data and data["Abstract"]:
            results.append(f"Abstract: {data['Abstract']}\n")

        if "AbstractText" in data and data["AbstractText"]:
            results.append(f"{data['AbstractText']}\n")

        if "AbstractURL" in data and data["AbstractURL"]:
            results.append(f"Source: {data['AbstractURL']}\n")

        # Add related topics
        if "RelatedTopics" in data and data["RelatedTopics"]:
            results.append("\nTop results:")
            for i, topic in enumerate(data["RelatedTopics"][:num_results], 1):
                if "Text" in topic and "FirstURL" in topic:
                    results.append(f"{i}. {topic['Text']}")
                    results.append(f"   {topic['FirstURL']}\n")

        if not results or len(results) == 1:
            return f"No results found for: {query}"

        return "\n".join(results)

    except requests.Timeout:
        return f"Error: Search timed out after {timeout} seconds"
    except requests.RequestException as e:
        return f"Error: Search failed: {e}"
    except Exception as e:
        return f"Error: {e}"


def _search_google(query: str, num_results: int, timeout: int, settings: "Settings") -> str:
    """Search using Google Custom Search API."""
    try:
        import requests
    except ImportError:
        return "Error: requests library not installed. Install with: pip install requests"

    try:
        api_key = settings.google_search_api_key
        search_engine_id = settings.google_search_engine_id

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": search_engine_id,
            "q": query,
            "num": min(num_results, 10),  # Google limits to 10 per request
        }

        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        results.append(f"Search results for: {query}\n")

        if "items" in data:
            for i, item in enumerate(data["items"], 1):
                results.append(f"{i}. {item.get('title', 'No title')}")
                results.append(f"   {item.get('link', '')}")
                if "snippet" in item:
                    results.append(f"   {item['snippet'][:200]}...")
                results.append("")

        if len(results) == 1:
            return f"No results found for: {query}"

        return "\n".join(results)

    except requests.Timeout:
        return f"Error: Search timed out after {timeout} seconds"
    except requests.RequestException as e:
        return f"Error: Search failed: {e}"
    except Exception as e:
        return f"Error: {e}"


def _search_bing(query: str, num_results: int, timeout: int, settings: "Settings") -> str:
    """Search using Bing Search API."""
    try:
        import requests
    except ImportError:
        return "Error: requests library not installed. Install with: pip install requests"

    try:
        api_key = settings.bing_search_api_key

        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {
            "q": query,
            "count": min(num_results, 50),  # Bing allows up to 50
        }

        response = requests.get(url, headers=headers, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        results.append(f"Search results for: {query}\n")

        if "webPages" in data and "value" in data["webPages"]:
            for i, item in enumerate(data["webPages"]["value"], 1):
                results.append(f"{i}. {item.get('name', 'No title')}")
                results.append(f"   {item.get('url', '')}")
                if "snippet" in item:
                    results.append(f"   {item['snippet'][:200]}...")
                results.append("")

        if len(results) == 1:
            return f"No results found for: {query}"

        return "\n".join(results)

    except requests.Timeout:
        return f"Error: Search timed out after {timeout} seconds"
    except requests.RequestException as e:
        return f"Error: Search failed: {e}"
    except Exception as e:
        return f"Error: {e}"


def _search_serpapi(query: str, num_results: int, timeout: int, settings: "Settings") -> str:
    """Search using SerpAPI (supports Google, Bing, etc.)."""
    try:
        import requests
    except ImportError:
        return "Error: requests library not installed. Install with: pip install requests"

    try:
        api_key = settings.serpapi_api_key

        url = "https://serpapi.com/search"
        params = {
            "engine": "google",
            "q": query,
            "num": min(num_results, 100),  # SerpAPI allows up to 100
            "api_key": api_key,
        }

        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        results.append(f"Search results for: {query}\n")

        if "organic_results" in data:
            for i, item in enumerate(data["organic_results"], 1):
                results.append(f"{i}. {item.get('title', 'No title')}")
                results.append(f"   {item.get('link', '')}")
                if "snippet" in item:
                    results.append(f"   {item['snippet'][:200]}...")
                results.append("")

        if len(results) == 1:
            return f"No results found for: {query}"

        return "\n".join(results)

    except requests.Timeout:
        return f"Error: Search timed out after {timeout} seconds"
    except requests.RequestException as e:
        return f"Error: Search failed: {e}"
    except Exception as e:
        return f"Error: {e}"


@handle_tool_errors
def web_search_html(
    query: str,
    num_results: int = 10,
    timeout: int = 10,
) -> str:
    """
    Search the web using DuckDuckGo HTML version (alternative implementation).

    This provides more detailed search results than the JSON API.

    Args:
        query: Search query string
        num_results: Number of results to return (default 10)
        timeout: Request timeout in seconds (default 10)

    Returns:
        Search results as formatted text
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return "Error: Required libraries not installed. Install with: pip install requests beautifulsoup4"

    try:
        # Use DuckDuckGo HTML search
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        results = []
        results.append(f"Search results for: {query}\n")

        # Parse search results
        search_results = soup.find_all("div", class_="result")
        for i, result in enumerate(search_results[:num_results], 1):
            title_elem = result.find("a", class_="result__a")
            snippet_elem = result.find("a", class_="result__snippet")

            if title_elem:
                title = title_elem.get_text(strip=True)
                url = title_elem.get("href", "")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                results.append(f"{i}. {title}")
                if url:
                    results.append(f"   {url}")
                if snippet:
                    # Truncate long snippets
                    snippet = snippet[:200] + "..." if len(snippet) > 200 else snippet
                    results.append(f"   {snippet}")
                results.append("")

        if len(results) == 1:
            return f"No results found for: {query}"

        return "\n".join(results)

    except requests.Timeout:
        return f"Error: Search timed out after {timeout} seconds"
    except requests.RequestException as e:
        return f"Error: Search failed: {e}"
    except Exception as e:
        return f"Error: {e}"


__all__ = [
    "web_fetch",
    "web_search",
    "web_search_html",
    "SearchAPIConfig",
]
