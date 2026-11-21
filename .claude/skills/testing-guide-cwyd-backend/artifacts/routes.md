> Part of the `testing-guide-cwyd-backend` skill (see `../SKILL.md`).

# Routes (`@router.get/post/put/delete` functions in `app/api/`)

## What to test
- Status code and response body shape for the happy path.
- Validation wiring: one test per endpoint proving an invalid request returns 422 (more only
  for security or business-critical rules such as file type and size on upload).
- Error mapping: each domain exception the route can surface → status + stable error code.
- Dependency failures: the adapter's `DatabaseUnavailable` → 503 with the stable `detail`;
  programming errors are NOT caught and surface as 500.
- Access rules once they exist: another owner's document → 404, never 403 with content.
- No leakage: `detail` never contains SQL, provider messages or document text.

## Layer assignment
- **HTTP (TestClient)** for every route. No unit tests of route functions.
- Real Postgres (testcontainers) when the route reaches the database; use-case fakes through
  `app.dependency_overrides` when the test is about HTTP mapping of a use-case result or error
  and the use case is covered elsewhere.
- Liveness routes (`/health`) need no database: use the unreachable-settings fixture to prove
  they do not touch it.

## Setup pattern
```python
def test_<route>_<scenario>(postgres: PostgresContainer,
                            settings_for: Callable[[str], Settings]) -> None:
    settings = settings_for(postgres.get_connection_url())
    with TestClient(create_app(settings=settings)) as client:   # `with` runs the lifespan
        response = client.get("/documents")
    assert response.status_code == 200
```
Overriding a use case to test HTTP mapping only:
```python
app = create_app(settings=unreachable_settings)
app.dependency_overrides[get_ask_question] = lambda: FailingAskQuestion(InsufficientEvidence())
with TestClient(app) as client:
    response = client.post("/questions", json={"question": "q"})
assert response.status_code == 200
assert response.json()["answer_status"] == "not_enough_evidence"
```
- Routes have no `/api` prefix; call `/health`, not `/api/health`.

## When to skip
- One validation test per endpoint; do not enumerate every invalid field.
- Do not re-test use-case branches through HTTP; test the mapping of each outcome once.

## Examples from project
- `health` — no I/O → HTTP with unreachable settings (`tests/unit/test_health.py`).
- `ready` — branching on dependency state → HTTP against real pgvector, a database without the
  extension and an unreachable port (`tests/integration/test_readiness.py`).
