"""LLM provider abstraction — Strategy Pattern for LLM selection."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel

from src.config import CloudProvider, Settings

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def get_chat_model(self) -> BaseChatModel:
        """Return a LangChain chat model configured for this provider."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier string."""
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name (aws, azure, local)."""
        ...


class BedrockProvider(BaseLLMProvider):
    """AWS Bedrock LLM provider using Claude."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_chat_model(self) -> BaseChatModel:
        from langchain_aws import ChatBedrock

        return ChatBedrock(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name=self.settings.aws_default_region,
            model_kwargs={
                "temperature": self.settings.llm_temperature,
                "max_tokens": self.settings.llm_max_tokens,
            },
        )

    def get_model_name(self) -> str:
        return "anthropic.claude-3-5-sonnet-v2"

    def get_provider_name(self) -> str:
        return "aws"


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI LLM provider."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_chat_model(self) -> BaseChatModel:
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_deployment=self.settings.azure_openai_deployment_name,
            azure_endpoint=self.settings.azure_openai_endpoint,
            api_key=self.settings.azure_openai_api_key,
            api_version=self.settings.azure_openai_api_version,
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens,
        )

    def get_model_name(self) -> str:
        return self.settings.azure_openai_deployment_name

    def get_provider_name(self) -> str:
        return "azure"


class OllamaProvider(BaseLLMProvider):
    """Local Ollama LLM provider."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_chat_model(self) -> BaseChatModel:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=self.settings.ollama_chat_model,
            base_url=self.settings.ollama_base_url,
            temperature=self.settings.llm_temperature,
            num_predict=self.settings.llm_max_tokens,
        )

    def get_model_name(self) -> str:
        return self.settings.ollama_chat_model

    def get_provider_name(self) -> str:
        return "local"


def create_llm_provider(settings: Settings) -> BaseLLMProvider:
    """Factory: create the appropriate LLM provider based on configuration."""
    providers: dict[CloudProvider, type[BaseLLMProvider]] = {
        CloudProvider.AWS: BedrockProvider,
        CloudProvider.AZURE: AzureOpenAIProvider,
        CloudProvider.LOCAL: OllamaProvider,
    }

    provider_cls = providers.get(settings.cloud_provider)
    if provider_cls is None:
        raise ValueError(f"Unsupported cloud provider: {settings.cloud_provider}")

    provider = provider_cls(settings)
    logger.info(
        "LLM provider created: %s (%s)",
        provider.get_provider_name(),
        provider.get_model_name(),
    )
    return provider
