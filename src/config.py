"""AI Agent configuration — Pydantic Settings for all environment variables."""

from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class CloudProvider(str, Enum):
    """Supported cloud providers."""

    AWS = "aws"
    AZURE = "azure"
    LOCAL = "local"


class AppEnvironment(str, Enum):
    """Application environments."""

    DEV = "dev"
    STG = "stg"
    PRD = "prd"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Cloud Provider ─────────────────────────────────────────────
    cloud_provider: CloudProvider = CloudProvider.LOCAL

    # ── Application ────────────────────────────────────────────────
    app_environment: AppEnvironment = AppEnvironment.DEV
    app_port: int = 8200
    log_level: str = "INFO"

    # ── LLM Settings ──────────────────────────────────────────────
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048
    agent_max_iterations: int = 10

    # ── Tool Configuration ────────────────────────────────────────
    tavily_api_key: str = ""
    tool_web_search_enabled: bool = True
    tool_calculator_enabled: bool = True
    tool_database_query_enabled: bool = True

    # ── MCP Client ────────────────────────────────────────────────
    mcp_server_url: str = ""
    mcp_enabled: bool = False

    # ── AI Gateway ────────────────────────────────────────────────
    gateway_url: str = "http://localhost:8100"
    gateway_enabled: bool = False
    gateway_api_key: str = ""

    # ── Database ──────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///data/conversations.db"

    # ── AWS Bedrock ───────────────────────────────────────────────
    aws_default_region: str = "eu-west-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # ── Azure OpenAI ──────────────────────────────────────────────
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_deployment_name: str = "gpt-4o"

    # ── Ollama ────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"
