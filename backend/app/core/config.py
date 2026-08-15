"""Configuration settings using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False

    # MySQL Configuration
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "lifegift"
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_POOL_SIZE: int = 5
    MYSQL_MAX_OVERFLOW: int = 10
    DATABASE_URL: Optional[str] = None

    # Qdrant Configuration
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "lifegift_knowledge"

    # OpenAI-Compatible LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.0

    # OpenAI-Compatible Embedding Configuration
    EMBEDDING_BASE_URL: Optional[str] = None
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    @property
    def effective_llm_api_key(self) -> Optional[str]:
        return self.LLM_API_KEY or self.OPENAI_API_KEY

    @property
    def effective_llm_base_url(self) -> Optional[str]:
        return self.LLM_BASE_URL

    @property
    def effective_embedding_api_key(self) -> Optional[str]:
        return self.EMBEDDING_API_KEY or self.LLM_API_KEY or self.OPENAI_API_KEY

    @property
    def effective_embedding_base_url(self) -> Optional[str]:
        return self.EMBEDDING_BASE_URL or self.LLM_BASE_URL

    @property
    def sync_database_url(self) -> str:
        """Return synchronous SQLAlchemy MySQL / SQLite database URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@"
            f"{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            "?charset=utf8mb4"
        )


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
