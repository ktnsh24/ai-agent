"""Tool registry — manages available tools for the agent."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from langchain_core.tools import BaseTool

from src.config import Settings
from src.models import ToolInfo

logger = logging.getLogger(__name__)


class BaseToolProvider(ABC):
    """Abstract base for tool providers."""

    @abstractmethod
    def get_tools(self) -> list[BaseTool]:
        """Return list of LangChain tools."""
        ...

    @abstractmethod
    def get_tool_info(self) -> list[ToolInfo]:
        """Return tool metadata for API responses."""
        ...


class BuiltinToolProvider(BaseToolProvider):
    """Provides built-in tools: web search, calculator, database query."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._tools: list[BaseTool] = []
        self._tool_info: list[ToolInfo] = []
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all enabled built-in tools."""
        if self.settings.tool_web_search_enabled:
            self._register_web_search()
        if self.settings.tool_calculator_enabled:
            self._register_calculator()
        if self.settings.tool_database_query_enabled:
            self._register_database_query()
        logger.info("Registered %d built-in tools", len(self._tools))

    def _register_web_search(self) -> None:
        """Register web search tool (Tavily or mock)."""
        from src.tools.web_search import create_web_search_tool

        tool = create_web_search_tool(self.settings)
        self._tools.append(tool)
        self._tool_info.append(
            ToolInfo(
                name="web_search",
                description="Search the web for current information",
                parameters={"query": {"type": "string", "description": "Search query"}},
                enabled=True,
            )
        )

    def _register_calculator(self) -> None:
        """Register calculator tool."""
        from src.tools.calculator import create_calculator_tool

        tool = create_calculator_tool()
        self._tools.append(tool)
        self._tool_info.append(
            ToolInfo(
                name="calculator",
                description="Perform mathematical calculations",
                parameters={"expression": {"type": "string", "description": "Math expression to evaluate"}},
                enabled=True,
            )
        )

    def _register_database_query(self) -> None:
        """Register database query tool."""
        from src.tools.database_query import create_database_query_tool

        tool = create_database_query_tool()
        self._tools.append(tool)
        self._tool_info.append(
            ToolInfo(
                name="database_query",
                description="Query a sample SQLite database with SQL",
                parameters={"query": {"type": "string", "description": "SQL query to execute"}},
                enabled=True,
            )
        )

    def get_tools(self) -> list[BaseTool]:
        return self._tools

    def get_tool_info(self) -> list[ToolInfo]:
        return self._tool_info


class MCPToolProvider(BaseToolProvider):
    """Provides tools from an MCP server (Phase 4 integration)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._tools: list[BaseTool] = []
        self._tool_info: list[ToolInfo] = []

    async def connect(self) -> None:
        """Connect to MCP server and discover tools."""
        if not self.settings.mcp_enabled or not self.settings.mcp_server_url:
            logger.info("MCP client disabled or no server URL configured")
            return

        logger.info("Connecting to MCP server: %s", self.settings.mcp_server_url)
        # MCP client integration — will be fully implemented in Phase 4
        # For now, this is a placeholder that logs the connection attempt
        logger.info("MCP client: server discovery not yet implemented (Phase 4)")

    def get_tools(self) -> list[BaseTool]:
        return self._tools

    def get_tool_info(self) -> list[ToolInfo]:
        return self._tool_info


class ToolRegistry:
    """Aggregates tools from multiple providers."""

    def __init__(self) -> None:
        self._providers: list[BaseToolProvider] = []

    def register_provider(self, provider: BaseToolProvider) -> None:
        """Register a tool provider."""
        self._providers.append(provider)

    def get_all_tools(self) -> list[BaseTool]:
        """Return all tools from all providers."""
        tools: list[BaseTool] = []
        for provider in self._providers:
            tools.extend(provider.get_tools())
        return tools

    def get_all_tool_info(self) -> list[ToolInfo]:
        """Return all tool info from all providers."""
        info: list[ToolInfo] = []
        for provider in self._providers:
            info.extend(provider.get_tool_info())
        return info


def create_tool_registry(settings: Settings) -> ToolRegistry:
    """Factory: create the tool registry with all providers."""
    registry = ToolRegistry()

    # Built-in tools
    builtin = BuiltinToolProvider(settings)
    registry.register_provider(builtin)

    # MCP tools (optional)
    if settings.mcp_enabled:
        mcp = MCPToolProvider(settings)
        registry.register_provider(mcp)

    logger.info("Tool registry created with %d tools", len(registry.get_all_tools()))
    return registry
