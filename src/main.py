"""AI Agent — FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.agent.conversation import SQLiteConversationStore, create_conversation_store
from src.agent.graph import create_agent_graph
from src.config import Settings
from src.llm.provider import create_llm_provider
from src.tools.registry import create_tool_registry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialise and cleanup components."""
    settings = Settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("Starting AI Agent (provider=%s, port=%d)", settings.cloud_provider.value, settings.app_port)

    # Create components
    llm_provider = create_llm_provider(settings)
    tool_registry = create_tool_registry(settings)
    conversation_store = create_conversation_store(settings)

    # Initialize conversation store
    if isinstance(conversation_store, SQLiteConversationStore):
        await conversation_store.initialize()

    # Create agent graph
    agent_graph = create_agent_graph(llm_provider, tool_registry, settings)

    # Store on app state
    app.state.settings = settings
    app.state.llm_provider = llm_provider
    app.state.tool_registry = tool_registry
    app.state.conversation_store = conversation_store
    app.state.agent_graph = agent_graph

    logger.info(
        "AI Agent ready — provider=%s, model=%s, tools=%d",
        llm_provider.get_provider_name(),
        llm_provider.get_model_name(),
        len(tool_registry.get_all_tools()),
    )

    yield

    # Cleanup
    await conversation_store.close()
    logger.info("AI Agent shutdown complete")


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="AI Agent",
        description="Phase 3 — AI Agent with LangGraph, tool use, and conversation persistence",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from src.routes.chat import router as chat_router
    from src.routes.conversations import router as conversations_router
    from src.routes.health import router as health_router
    from src.routes.tools import router as tools_router

    app.include_router(health_router)
    app.include_router(chat_router, prefix="/v1")
    app.include_router(conversations_router, prefix="/v1")
    app.include_router(tools_router, prefix="/v1")

    return app
