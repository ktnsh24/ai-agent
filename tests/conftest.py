"""
AI Agent — Shared Test Fixtures

Reusable fixtures for all test files. Components are mocked directly
on app.state (bypassing lifespan) so no Ollama/SQLite is needed.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.agent.conversation import InMemoryConversationStore
from src.models import AgentResponse, AgentStatus, ToolInfo


@pytest.fixture
def mock_llm_provider() -> MagicMock:
    """Mock LLM provider — local Ollama by default."""
    llm = MagicMock()
    llm.get_provider_name.return_value = "local"
    llm.get_model_name.return_value = "llama3.2"
    return llm


@pytest.fixture
def mock_tool_registry() -> MagicMock:
    """Mock tool registry with 3 default tools."""
    registry = MagicMock()
    registry.get_all_tools.return_value = []
    registry.get_all_tool_info.return_value = [
        ToolInfo(name="web_search", description="Search the web", parameters={}, enabled=True),
        ToolInfo(name="calculator", description="Math calculations", parameters={}, enabled=True),
        ToolInfo(name="database_query", description="Query the database", parameters={}, enabled=True),
    ]
    return registry


@pytest.fixture
def mock_agent_graph() -> AsyncMock:
    """Mock agent graph with default response."""
    agent = AsyncMock()
    agent.run.return_value = AgentResponse(
        conversation_id="test-conv-001",
        message="Hello! I'm the AI agent.",
        tool_calls=[],
        iterations=1,
        status=AgentStatus.COMPLETE,
        model="llama3.2",
        provider="local",
        total_tokens=50,
        latency_ms=1500.0,
    )
    return agent


@pytest.fixture
def conversation_store() -> InMemoryConversationStore:
    """Real in-memory conversation store (no mocking needed)."""
    return InMemoryConversationStore()


@pytest.fixture
def app(
    mock_llm_provider: MagicMock,
    mock_tool_registry: MagicMock,
    mock_agent_graph: AsyncMock,
    conversation_store: InMemoryConversationStore,
):
    """FastAPI app with all components mocked on app.state."""
    from src.main import create_app

    application = create_app()
    application.state.settings = MagicMock()
    application.state.llm_provider = mock_llm_provider
    application.state.tool_registry = mock_tool_registry
    application.state.agent_graph = mock_agent_graph
    application.state.conversation_store = conversation_store
    return application


@pytest.fixture
def client(app) -> TestClient:
    """Test client with all mocks wired."""
    return TestClient(app, raise_server_exceptions=False)
