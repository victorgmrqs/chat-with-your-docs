import uuid
from typing import Literal, Self

from pydantic import (
    Field,
    PostgresDsn,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import ErrorDetails
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: PostgresDsn
    chat_provider: Literal["openai", "anthropic"]
    chat_model: str
    embedding_model: str
    openai_api_key: SecretStr
    anthropic_api_key: SecretStr | None = None
    max_upload_mb: int = Field(default=10, gt=0)  # DOM-01
    # Must match the vector(N) column created by migrations/versions/0001 (A5).
    embedding_dimensions: int = Field(default=1536, gt=0)
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=150, ge=0)
    # DOM-06: single-owner MVP; the application sets the owner, never the client.
    default_owner_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

    model_config = SettingsConfigDict(extra="ignore", env_ignore_empty=True)

    @field_validator("database_url")
    @classmethod
    def _require_async_driver(cls, url: PostgresDsn) -> PostgresDsn:
        if url.scheme != "postgresql+asyncpg":
            raise ValueError("must use the postgresql+asyncpg:// scheme (async driver)")
        return url

    @model_validator(mode="after")
    def _require_provider_key(self) -> Self:
        if self.chat_provider == "anthropic" and self.anthropic_api_key is None:
            raise ValueError("ANTHROPIC_API_KEY is required when CHAT_PROVIDER=anthropic")
        return self

    @model_validator(mode="after")
    def _overlap_smaller_than_chunk(self) -> Self:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


class ConfigurationError(Exception):
    """Raised at startup when required environment variables are missing or invalid."""


def _describe(error: ErrorDetails) -> str:
    """One line per problem, named by its environment variable when it belongs to a field."""
    reason = error["msg"].removeprefix("Value error, ")
    if not error["loc"]:  # model-level rule: the reason already names the variables
        return f"  - {reason}"
    return f"  - {str(error['loc'][0]).upper()}: {reason}"


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        problems = [_describe(error) for error in exc.errors()]
        message = "\n".join(
            [
                "Invalid configuration:",
                *problems,
                "Set these variables in .env (see .env.example) and restart.",
            ]
        )
        raise ConfigurationError(message) from None
