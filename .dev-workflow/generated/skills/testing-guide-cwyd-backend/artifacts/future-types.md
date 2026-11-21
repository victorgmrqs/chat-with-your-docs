> Part of the `testing-guide-cwyd-backend` skill (see `../SKILL.md`).

# Future types (not in the codebase yet)

## Document parsers (adapters implementing `DocumentParserPort`)
- **What:** text extraction for .pdf, .md, .txt using generated fixture files with known facts
  (`backend/tests/fixtures/documents/`); unsupported or corrupt files → typed error.
- **Layer:** unit with real parsing libraries (they are configured libs, never mocked); blocking
  parsing runs in `asyncio.to_thread` and is awaited in the test.
- **Skip:** layout fidelity; assert extracted facts, not whole text snapshots.

## Exception handlers (`app.add_exception_handler` / `@app.exception_handler`)
- **What:** each domain exception → status code + stable error code; unknown exceptions → 500
  without stack trace or provider message.
- **Layer:** HTTP. One test per mapping row, using a route or `dependency_overrides` that raises
  the exception.
- **Setup:** `TestClient(app, raise_server_exceptions=False)` to assert the 500 body.

## Background indexing jobs
- **What:** status transitions written to the database (indexing → ready/failed), chunks and
  embeddings persisted, failure path marks the document failed with a reason.
- **Layer:** integration with real Postgres + `DeterministicFakeEmbedding`; the job gets its
  own resources from the composition root, so tests build them the same way.
- **Isolation:** unique `owner_id` per test (jobs open their own connections, so the
  rollback fixture does not apply). Poll the status with a bounded timeout, never `sleep`.

## Streaming answers (SSE / `StreamingResponse`)
- **What:** event order (tokens, then citations, then done), error event on provider failure,
  final citations limited to retrieved chunks.
- **Layer:** HTTP with `client.stream("POST", ...)` and the fake chat model emitting known
  chunks.

## Schema setup (CWYD-3)
- **What:** schema creates cleanly on an empty database and is idempotent; indexes the queries
  depend on exist (HNSW, GIN for full-text).
- **Layer:** integration, once per session in the `engine` fixture; one test asserts the
  expected indexes through `pg_indexes`.
