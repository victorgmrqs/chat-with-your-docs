> Part of the `testing-guide-cwyd-backend` skill (see `../SKILL.md`).

# Domain models (entities and value objects in `app/domain/`)

## What to test
- Rules with branching: document status transitions (only `indexing → ready | failed`;
  reject others), supported formats (.pdf, .md, .txt) and size limits, citation filtering
  (keep only chunk IDs present in the retrieved set), the "not enough evidence" decision
  (thresholds, empty retrieval).
- Invariants enforced at construction (non-empty text, positive chunk index).
- Typed exceptions raised for each violated rule (`UnsupportedFormat`, `InsufficientEvidence`…).

## Layer assignment
- **Unit only.** The domain imports no FastAPI, SQLAlchemy, LangChain or SDK, so tests need no
  fakes at all.
- Persistence of an entity is tested in its Postgres adapter, not here.

## Setup pattern
```python
def test_<model>_<rule>_<scenario>() -> None:
    document = Document.new(owner_id=OWNER, filename="notes.md")
    with pytest.raises(InvalidTransition):
        document.mark_ready()            # must go through indexing first
```
- Build models with small factory functions in the test module (or a shared `tests/factories.py`
  module), never from `conftest.py` imports.

## When to skip
- Field existence, default values and dataclass equality.
- Properties that return a field unchanged.

## Examples from project
- None yet. Domain models arrive with ingestion (CWYD-3) and answering (CWYD-4); their rules are
  the highest-value unit tests in the backend.
