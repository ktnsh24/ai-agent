"""Tests for API endpoints — health, tools, chat."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.agent.conversation import InMemoryConversationStore
from src.models import AgentResponse, AgentStatus, ToolInfo


@pytest.fixture
def mock_app():
    """Create a test app with mocked components."""
    from src.main import create_app

    app = create_app()

    # Mock LLM provider
    mock_llm = MagicMock()
    mock_llm.get_provider_name.return_value = "local"
    mock_llm.get_model_name.return_value = "llama3.2"

    # Mock tool registry
    mock_registry = MagicMock()
    mock_registry.get_all_tools.return_value = []
    mock_registry.get_all_tool_info.return_value = [
        ToolInfo(name="web_search", description="Search the web", parameters={}, enabled=True),
        ToolInfo(name="calculator", description="Math calculations", parameters={}, enabled=True),
    ]

    # Mock agent graph
    mock_agent = AsyncMock()
    mock_agent.run.return_value = AgentResponse(
        conversation_id="test123",
        message="Hello! I'm the AI agent.",
        tool_calls=[],
        iterations=1,
        status=AgentStatus.COMPLETE,
        model="llama3.2",
        provider="local",
        total_tokens=50,
        latency_ms=1500.0,
    )

    # Mock conversation store
    mock_store = InMemoryConversationStore()

    # Attach to app state (bypass lifespan)
    app.state.settings = MagicMock()
    app.state.llm_provider = mock_llm
    app.state.tool_registry = mock_registry
    app.state.agent_graph = mock_agent
    app.state.conversation_store = mock_store

    return app


@pytest.fixture
def client(mock_app):
    """Create a test client."""
    return TestClient(mock_app, raise_server_exceptions=False)


class TestHealthEndpoint:
    """Test GET /health."""

    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_status(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["version"] == "0.1.0"

    def test_health_shows_provider(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert data["provider"] == "local"


class TestToolsEndpoint:
    """Test GET /v1/tools."""

    def test_list_tools(self, client: TestClient) -> None:
        response = client.get("/v1/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) == 2

    def test_tool_has_name_and_description(self, client: TestClient) -> None:
        response = client.get("/v1/tools")
        tools = response.json()["tools"]
        assert tools[0]["name"] == "web_search"
        assert tools[0]["description"] == "Search the web"


class TestChatEndpoint:
    """Test POST /v1/chat."""

    def test_chat_returns_200(self, client: TestClient) -> None:
        response = client.post("/v1/chat", json={"message": "Hello!"})
        assert response.status_code == 200

    def test_chat_returns_agent_response(self, client: TestClient) -> None:
        response = client.post("/v1/chat", json={"message": "Hello!"})
        data = response.json()
        assert "message" in data
        assert "conversation_id" in data
        assert data["status"] == "complete"

    def test_chat_has_model_info(self, client: TestClient) -> None:
        response = client.post("/v1/chat", json={"message": "Hello!"})
        data = response.json()
        assert data["model"] == "llama3.2"
        assert data["provider"] == "local"

    def test_chat_empty_message_returns_422(self, client: TestClient) -> None:
        response = client.post("/v1/chat", json={})
        assert response.status_code == 422


class TestConversationsEndpoint:
    """Test /v1/conversations endpoints."""

    def test_list_conversations_empty(self, client: TestClient) -> None:
        response = client.get("/v1/conversations")
        assert response.status_code == 200
        assert response.json() == []

    def test_conversation_created_after_chat(self, client: TestClient) -> None:
        # Chat creates a conversation
        client.post("/v1/chat", json={"message": "Hello!"})

        response = client.get("/v1/conversations")
        assert response.status_code == 200
        conversations = response.json()
        assert len(conversations) >= 1
