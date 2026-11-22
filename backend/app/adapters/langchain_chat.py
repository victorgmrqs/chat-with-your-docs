"""ChatModelPort over a LangChain chat model with structured output (shared by providers)."""

import logging
from typing import Literal

from langchain_core.exceptions import LangChainException, ModelTimeoutError
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.application.ports import ChatPrompt
from app.domain.answers import ChatModelTimeout, ChatModelUnavailable

logger = logging.getLogger(__name__)

StructuredOutputMethod = Literal["function_calling", "json_schema"]


class LangChainChatAdapter:
    """Subclasses pass the LangChain model and the provider's exception types.

    The provider client retries transient errors (429, 5xx, timeouts) up to its
    `max_retries`; what still fails becomes ChatModelTimeout or ChatModelUnavailable (DOM-12).
    """

    def __init__(
        self,
        provider: str,
        model: str,
        client: BaseChatModel,
        method: StructuredOutputMethod,
        *,
        timeout_errors: tuple[type[Exception], ...],
        provider_errors: tuple[type[Exception], ...],
    ) -> None:
        self._provider = provider
        self._model = model
        self._client = client
        self._method = method
        self._timeout_errors: tuple[type[Exception], ...] = (*timeout_errors, ModelTimeoutError)
        # LangChainException covers refusals and content filters (ModelRefusalError) and
        # unparseable output (OutputParserException); ValueError covers pydantic validation
        # and the providers' "no parsed output" errors. All are DOM-12 technical failures.
        self._failures: tuple[type[Exception], ...] = (
            *provider_errors,
            LangChainException,
            ValueError,
        )

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    async def generate[T: BaseModel](self, prompt: ChatPrompt, schema: type[T]) -> T:
        runnable = self._client.with_structured_output(schema, method=self._method)
        messages = [SystemMessage(prompt.system), HumanMessage(prompt.user)]
        try:
            result = await runnable.ainvoke(messages)
        except self._timeout_errors as exc:
            self._log_failure(type(exc).__name__)
            raise ChatModelTimeout from exc
        except self._failures as exc:
            # Exception type only: provider messages may echo prompt content.
            self._log_failure(type(exc).__name__)
            raise ChatModelUnavailable from exc
        if not isinstance(result, schema):  # e.g. the model answered without the tool call
            self._log_failure("MissingStructuredOutput")
            raise ChatModelUnavailable
        return result

    def _log_failure(self, error_type: str) -> None:
        logger.warning(
            "Chat model call failed: %s",
            error_type,
            extra={"error_type": error_type, "provider": self._provider, "model": self._model},
        )
