"""Agent configuration for LLM provider management."""
from typing import Literal
from openai import AsyncOpenAI

from app.core.config import settings


def get_llm_client() -> AsyncOpenAI:
    """Get the appropriate LLM client based on provider configuration."""
    return AsyncOpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
    )


def get_model_name() -> str:
    """Get the model name based on provider configuration."""
    return settings.model_name


def get_provider() -> Literal["openrouter", "openai"]:
    """Get the current LLM provider."""
    return settings.PROVIDER
