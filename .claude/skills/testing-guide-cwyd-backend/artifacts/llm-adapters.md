> Part of the `testing-guide-cwyd-backend` skill (see `../SKILL.md`).

# LLM and embedding adapters (classes implementing `ChatModelPort` / `EmbeddingPort`)

## What to test
- Request mapping: model name and provider come from `Settings`; the prompt includes the
  retrieved chunks with their IDs; system instructions are present.
- Response mapping: structured output or citations parsed into domain types; malformed output
  → typed error, not a crash.
- Provider errors (timeout, rate limit, auth) translated into one domain error without leaking
  the provider message.
- Embedding dimension matches the pgvector column; batching splits inputs as configured.
- Nothing logged or put in span attributes contains question, prompt, chunk or answer text.

## Layer assignment
- **Unit with langchain-core fakes** injected where the adapter builds its LangChain model:
  `GenericFakeChatModel(messages=iter([...]))` (one response per call; build a new iterator per
  test), `FakeListChatModel` (cycles responses), `DeterministicFakeEmbedding(size=N)` (same text
  → same vector).
- **No integration test against real providers** in the suite. A real call belongs to the RAG
  evaluation script (`docs/eval/`), run manually with real keys.

## Setup pattern
```python
async def test_openai_chat_adapter_maps_citations() -> None:
    fake = GenericFakeChatModel(messages=iter([AIMessage(content='{"answer": "x", "citations": ["c1"]}')]))
    adapter = OpenAIChatModel(model=fake)          # adapter accepts the LangChain model
    answer = await adapter.answer(question="q", chunks=[chunk("c1"), chunk("c2")])
    assert answer.citations == ["c1"]
```
- Design adapters so the LangChain model is injectable (constructed in the composition root),
  which keeps fakes out of module patching.
- `GenericFakeChatModel` does not support `bind_tools`; if the adapter binds tools, use a small
  hand-written fake chat model that does.

## When to skip
- Do not test LangChain's retry or streaming internals.
- Do not assert on full prompt strings; assert on the facts the prompt must contain.

## Examples from project
- None yet. First ones arrive with embeddings (CWYD-3) and chat (CWYD-4).
