> Part of the `testing-guide-cwyd-backend` skill (see `../SKILL.md`).

# Use cases (classes/functions in `app/application/` that depend on ports)

## What to test
- One success test plus one test per error row the use case covers (rule from
  `.claude/rules/backend-tests.md`).
- Orchestration branches: empty retrieval → "not enough evidence" without calling the chat
  model; chat answer citing unknown chunk IDs → those citations dropped; provider failure →
  typed error; parsing failure → document marked failed.
- Filters the app must always apply: owner and `Ready` status are passed by the use case to the
  retriever, never derived from LLM output.
- What leaves the use case: the result object and domain errors, never provider exceptions.

## Layer assignment
- **Unit with declared port fakes.** `FakeChatModel`, `FakeEmbeddings` (deterministic vectors),
  in-memory `FakeDocumentRepository`/`FakeRetriever` implementing the same `Protocol`.
- The adapters behind those ports carry the integration tests; the use case does not get a
  second integration test of its own unless it coordinates a transaction across adapters.
- Its HTTP surface is tested in `artifacts/routes.md`.

## Setup pattern
```python
class FakeRetriever:                       # implements RetrieverPort
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.calls: list[RetrievalQuery] = []

    async def retrieve(self, query: RetrievalQuery) -> list[Chunk]:
        self.calls.append(query)
        return [c for c in self.chunks if c.owner_id == query.owner_id]

async def test_ask_question_returns_not_enough_evidence_when_nothing_is_retrieved() -> None:
    chat = FakeChatModel(answers=[])                     # would fail if called
    use_case = AskQuestion(retriever=FakeRetriever([]), chat_model=chat)
    result = await use_case.execute(owner_id=OWNER, question="q")
    assert result.status is AnswerStatus.NOT_ENOUGH_EVIDENCE
    assert chat.calls == 0
```
- Fakes live in `tests/fakes.py` (regular module, importable), not in `conftest.py`.
- At most 3 test doubles per test; more means the use case has too many collaborators.

## When to skip
- A use case that only forwards to one adapter without branching: no unit test; the adapter's
  integration test and the route's HTTP test cover it.
- Do not assert the order of port calls unless the order is the behavior.

## Examples from project
- None yet. First ones: ingestion (CWYD-3) and question answering (CWYD-4).
