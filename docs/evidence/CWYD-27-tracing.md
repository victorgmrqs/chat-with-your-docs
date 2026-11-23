# CWYD-27: tracing follow-ups, evidence

Collected on 2026-11-23 on branch `feat/CWYD-27-tracing-follow-ups`.

## Required scenarios (backend unit tests)

```
$ uv run pytest -v tests/unit/test_tracing.py::test_otel_no_usage_no_cost \
    tests/unit/test_tracing.py::test_otel_call_without_usage_is_left_out_of_the_totals \
    tests/unit/test_config.py::test_price_table_default_independent_of_cwd \
    tests/unit/test_config.py::test_price_table_path_from_env_is_used_as_given \
    tests/unit/test_http_tracing.py::test_otel_ignores_client_traceparent \
    tests/unit/test_http_tracing.py::test_telemetry_logs_disabled
6 passed in 0.19s
```

Each test was run before the change and failed for the expected reason:
- the root span carried `gen_ai.usage.* = 0` and `app.cost.usd = 0.0`;
- the price path was the relative `app/prices.yaml`;
- the client's `traceparent` made the request span a child of the client's span;
- an unhandled error exported one FastAPI log record.

Full suite: `336 passed, 2 skipped`; ruff and mypy clean.

## Default price table from three working directories

The default `price_table_path` loaded from `backend/`, from the repository root and from an
unrelated directory resolves to the same file:

```
cwd=<repo>/backend   default=<repo>/backend/app/prices.yaml models=1
cwd=<repo>           default=<repo>/backend/app/prices.yaml models=1
cwd=/tmp/claude-1000 default=<repo>/backend/app/prices.yaml models=1
```

Inside the image the package lives at `/app/app`, so the default is `/app/app/prices.yaml`, the
same file the old relative default reached from the working directory `/app`.

## Manual check

`docs/http/chat.http`, request `otel_ignores_client_traceparent`, with
`OTEL_TRACES_EXPORTER=console`.
