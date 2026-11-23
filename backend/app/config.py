import uuid
from pathlib import Path
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


class HttpSettings(BaseSettings):
    """Read at import time by `create_app`, before the full Settings (database, keys) exist."""

    api_docs_enabled: bool = True  # false removes /docs, /redoc and /openapi.json

    model_config = SettingsConfigDict(extra="ignore", env_ignore_empty=True)


class Settings(HttpSettings):
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

    # Answering (CWYD-4). Defaults are starting points; the RAG evaluation (CWYD-11) tunes them.
    question_max_chars: int = Field(default=2000, gt=0)  # DOM-07
    retrieval_candidates: int = Field(default=20, gt=0)  # per branch, before fusion
    retrieval_top_k: int = Field(default=6, gt=0)  # fused chunks considered for the prompt
    min_relevance: float = Field(default=0.30, ge=0, le=1)  # DOM-08: cosine floor
    rerank_enabled: bool = False  # DOM-11
    rerank_top_n: int = Field(default=4, gt=0)
    context_token_budget: int = Field(default=3000, gt=0)  # DOM-11
    answer_max_tokens: int = Field(default=800, gt=0)
    # Per attempt; the client retries timeouts and 429/5xx up to CHAT_MAX_RETRIES times.
    chat_timeout_seconds: float = Field(default=30, gt=0)
    chat_max_retries: int = Field(default=2, ge=0)
    # Unset: the provider's default. Some models (e.g. reasoning models) reject the parameter.
    chat_temperature: float | None = Field(default=None, ge=0, le=2)

    # Tracing (CWYD-12), standard OpenTelemetry variable names. `none` sets up nothing.
    otel_traces_exporter: Literal["none", "console", "otlp"] = "none"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"  # base URL; /v1/traces is added
    otel_service_name: str = "cwyd-backend"
    otel_traces_sampler_arg: float = Field(default=1.0, ge=0, le=1)  # share of traces kept
    capture_content: bool = False  # DOM-22: dev only; content goes to span events
    price_table_path: Path = Path("app/prices.yaml")  # DOM-24, relative to backend/

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

    @model_validator(mode="after")
    def _top_k_within_candidates(self) -> Self:
        if self.retrieval_top_k > 2 * self.retrieval_candidates:
            raise ValueError("RETRIEVAL_TOP_K cannot exceed twice RETRIEVAL_CANDIDATES")
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
