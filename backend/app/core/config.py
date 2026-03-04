"""Application configuration settings."""
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Todo Agent API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/todoagent"

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # LLM Provider Configuration
    PROVIDER: Literal["openrouter", "openai"] = "openrouter"

    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    DEFAULT_OPENROUTER_MODEL: str = "anthropic/claude-3.5-sonnet"

    # OpenAI
    OPENAI_API_KEY: str = ""
    DEFAULT_OPENAI_MODEL: str = "gpt-4o-mini"

    # Model (can override default)
    MODEL_NAME: str = ""

    @property
    def model_name(self) -> str:
        """Get the model name based on provider."""
        if self.MODEL_NAME:
            return self.MODEL_NAME
        return (
            self.DEFAULT_OPENROUTER_MODEL
            if self.PROVIDER == "openrouter"
            else self.DEFAULT_OPENAI_MODEL
        )

    @property
    def api_key(self) -> str:
        """Get the API key based on provider."""
        return (
            self.OPENROUTER_API_KEY
            if self.PROVIDER == "openrouter"
            else self.OPENAI_API_KEY
        )

    @property
    def base_url(self) -> str | None:
        """Get the base URL based on provider."""
        return self.OPENROUTER_BASE_URL if self.PROVIDER == "openrouter" else None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
