> Part of the `testing-guide-cwyd-backend` skill (see `../SKILL.md`).

# Postgres adapters (classes in `app/adapters/` that receive an `AsyncEngine`)

## What to test
- Every query against real PostgreSQL 17 + pgvector: filters (owner, `Ready` status), ordering,
  limits, vector similarity, full-text search, RRF fusion, upserts.
- Constraints the app relies on: unique keys, foreign keys with cascade, NOT NULL.
- Mapping: rows → domain types (`str | None`, entities), never `Row` leaking out.
- Isolation of tenants: a query never returns another owner's rows.
- Absence: missing rows return `None`/empty, not an exception (or the declared domain error).
- Connection failures surface as `DatabaseUnavailable` (unreachable port, wrong credentials),
  SQL errors do not.

## Layer assignment
- **Integration only.** No unit tests with a mocked engine or session.
- If an adapter also has branching (e.g. choose hybrid vs vector-only search by flag), test
  each branch through the real database; do not mock SQL to isolate the branch.
- Ranking quality (does hybrid beat vector-only?) belongs to the RAG evaluation
  (`docs/eval/`), not to the test suite. Tests assert deterministic facts: a known chunk is
  returned, filters hold, order follows a known score.

## Setup pattern
```python
@pytest.fixture(scope="session")
def postgres() -> Iterator[PostgresContainer]:
    # same image and init scripts as Compose (db/Dockerfile, runtime target)
    with (
        DockerImage(path=DB_IMAGE_DIR, tag="cwyd-db:test", target="runtime") as image,
        PostgresContainer(str(image), driver="asyncpg") as container,
    ):
        yield container

@pytest.fixture(scope="session")
async def engine(postgres: PostgresContainer) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(postgres.get_connection_url(), pool_pre_ping=True)
    # create the schema once per session here (CWYD-3 schema setup)
    yield engine
    await engine.dispose()

@pytest.fixture
async def connection(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as conn:
        transaction = await conn.begin()
        yield conn                      # adapter under test receives this connection/session
        await transaction.rollback()    # isolation: nothing survives the test
```
- With an `AsyncSession`, bind it to that connection with
  `join_transaction_mode="create_savepoint"` so code that commits still rolls back at teardown.
- Alternative isolation when rollback is impractical (background jobs that open their own
  connections): a unique `owner_id` per test.
- Embedding vectors in fixtures come from `DeterministicFakeEmbedding(size=<column dim>)` or
  hand-built vectors with known distances.

## When to skip
- Do not test SQLAlchemy's pooling, reconnection or type conversion.
- No test that only proves "a row was inserted" when a read test already round-trips it.

## Examples from project
- `PostgresReadiness.pgvector_version` — single query, no branching → integration, covered
  through `/health/ready` (`tests/integration/test_readiness.py`): extension present, absent
  (separate database) and unreachable.
