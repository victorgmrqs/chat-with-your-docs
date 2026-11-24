from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.adapters.anthropic_chat import AnthropicChatAdapter
from app.adapters.openai_chat import OpenAIChatAdapter
from app.adapters.openai_embeddings import OpenAIEmbeddingAdapter
from app.adapters.parsers import DocumentParserAdapter, RecursiveTextSplitter
from app.adapters.postgres_documents import PostgresDocumentRepository
from app.adapters.postgres_readiness import PostgresReadiness
from app.adapters.postgres_retriever import PostgresRetriever
from app.adapters.price_table import load_price_table
from app.application.answering import AnsweringLimits, AnswerQuestion
from app.application.ingestion import IngestionService
from app.application.ports import ChatModelPort, EmbeddingPort, RetrieverPort
from app.application.reranking import LLMReranker
from app.config import Settings
from app.domain.usage import PriceTable


@dataclass(frozen=True, slots=True)
class Container:
    """Concrete dependencies built once at startup and shared by every request."""

    settings: Settings
    engine: AsyncEngine
    readiness: PostgresReadiness
    ingestion: IngestionService
    answering: AnswerQuestion
    prices: PriceTable  # DOM-24; also read by the RAG evaluation


def build_chat_model(settings: Settings) -> ChatModelPort:
    """DOM-13: the provider is configuration only."""
    adapter: type[OpenAIChatAdapter | AnthropicChatAdapter] = OpenAIChatAdapter
    api_key = settings.openai_api_key
    if settings.chat_provider == "anthropic":
        if settings.anthropic_api_key is None:  # Settings rejects this; never fall back
            raise ValueError("ANTHROPIC_API_KEY is required when CHAT_PROVIDER=anthropic")
        adapter, api_key = AnthropicChatAdapter, settings.anthropic_api_key
    return adapter(
        settings.chat_model,
        api_key,
        max_tokens=settings.answer_max_tokens,
        timeout_seconds=settings.chat_timeout_seconds,
        max_retries=settings.chat_max_retries,
        temperature=settings.chat_temperature,
    )


def build_container(
    settings: Settings,
    embeddings: EmbeddingPort | None = None,
    chat: ChatModelPort | None = None,
    wrap_retriever: Callable[[RetrieverPort], RetrieverPort] | None = None,
    wrap_embeddings: Callable[[EmbeddingPort], EmbeddingPort] | None = None,
) -> Container:
    """`embeddings` and `chat` replace the provider adapters in tests (declared fakes).

    `wrap_retriever` and `wrap_embeddings` decorate those ports, e.g. so the RAG evaluation can
    record what retrieval returned (CWYD-11) and the embedding tokens (CWYD-28) per question.
    """
    # hide_parameters: driver errors must not echo bound values (chunk text) into logs.
    engine = create_async_engine(
        str(settings.database_url), pool_pre_ping=True, hide_parameters=True
    )
    embeddings = embeddings or OpenAIEmbeddingAdapter(
        settings.embedding_model, settings.openai_api_key, settings.embedding_dimensions
    )
    if wrap_embeddings is not None:
        embeddings = wrap_embeddings(embeddings)
    chat = chat or build_chat_model(settings)
    prices = load_price_table(settings.price_table_path)
    readiness = PostgresReadiness(engine)
    ingestion = IngestionService(
        PostgresDocumentRepository(engine),
        DocumentParserAdapter(max_pdf_pages=settings.pdf_max_pages),
        RecursiveTextSplitter(settings.chunk_size, settings.chunk_overlap),
        embeddings,
        readiness,  # VectorSchemaPort (DOM-26)
        max_upload_bytes=settings.max_upload_bytes,
        embedding_dimensions=settings.embedding_dimensions,
        pdf_parse_timeout_seconds=settings.pdf_parse_timeout_seconds,
        prices=prices,  # DOM-24
    )
    retriever: RetrieverPort = PostgresRetriever(engine)
    if wrap_retriever is not None:
        retriever = wrap_retriever(retriever)
    answering = AnswerQuestion(
        retriever,
        embeddings,
        chat,
        AnsweringLimits(
            question_max_chars=settings.question_max_chars,
            retrieval_candidates=settings.retrieval_candidates,
            retrieval_top_k=settings.retrieval_top_k,
            min_relevance=settings.min_relevance,
            rerank_top_n=settings.rerank_top_n,
            context_token_budget=settings.context_token_budget,
        ),
        reranker=LLMReranker(chat) if settings.rerank_enabled else None,
        prices=prices,  # DOM-24
        capture_content=settings.capture_content,  # DOM-22
    )
    return Container(
        settings=settings,
        engine=engine,
        readiness=readiness,
        ingestion=ingestion,
        answering=answering,
        prices=prices,
    )
