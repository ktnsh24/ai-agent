"""Web search tool — uses Tavily or mock for testing."""

from __future__ import annotations

import logging

from langchain_core.tools import tool

from src.config import Settings

logger = logging.getLogger(__name__)


def create_web_search_tool(settings: Settings):
    """Factory: create web search tool with Tavily or mock fallback."""
    if settings.tavily_api_key:
        return _create_tavily_tool(settings)
    return _create_mock_search_tool()


def _create_tavily_tool(settings: Settings):
    """Create a Tavily-powered web search tool."""
    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)

    @tool
    def web_search(query: str) -> str:
        """Search the web for current information using Tavily.

        Args:
            query: The search query string.

        Returns:
            A summary of search results.
        """
        try:
            response = client.search(query, max_results=5)
            results = []
            for result in response.get("results", []):
                title = result.get("title", "")
                content = result.get("content", "")
                url = result.get("url", "")
                results.append(f"**{title}**\n{content}\nSource: {url}")
            return "\n\n---\n\n".join(results) if results else "No results found."
        except Exception as e:
            logger.error("Tavily search failed: %s", e)
            return f"Search failed: {str(e)}"

    return web_search


def _create_mock_search_tool():
    """Create a mock web search tool for development/testing."""

    @tool
    def web_search(query: str) -> str:
        """Search the web for current information (mock — no API key configured).

        Args:
            query: The search query string.

        Returns:
            Mock search results for development.
        """
        mock_results = {
            "weather": "Current weather: 18°C, partly cloudy. Mock result — configure TAVILY_API_KEY for real search.",
            "news": "Latest news: AI continues to advance rapidly. Mock result — configure TAVILY_API_KEY.",
            "default": f"Mock search results for '{query}'. Configure TAVILY_API_KEY for real web search.",
        }
        query_lower = query.lower()
        for keyword, response in mock_results.items():
            if keyword in query_lower:
                return response
        return mock_results["default"]

    return web_search
