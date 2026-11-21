from typing import Literal, Self

from pydantic import PostgresDsn, SecretStr, ValidationError, model_validator
from pydantic_core import ErrorDetails
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: PostgresDsn
    chat_provider: Literal["openai", "anthropic"]
    chat_model: str
    embedding_model: str
    openai_api_key: SecretStr
    anthropic_api_key: SecretStr | None = None

    model_config = SettingsConfigDict(extra="ignore", env_ignore_empty=True)

    @model_validator(mode="after")
    def _require_provider_key(self) -> Self:
        if self.chat_provider == "anthropic" and self.anthropic_api_key is None:
            raise ValueError("ANTHROPIC_API_KEY is required when CHAT_PROVIDER=anthropic")
        return self


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
