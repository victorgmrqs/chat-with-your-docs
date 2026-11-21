---
name: fastapi
description: FastAPI conventions for this project. Use when writing or reviewing FastAPI routes, Pydantic models, dependencies (Depends), background tasks or streaming responses.
license: MIT
---

## Project overrides

These project rules win over anything below.

- Routes are thin: map HTTP to DTO, call a use case injected via `Depends` from the composition root, map the result back. No business logic, SQL, LangChain or provider SDK calls in routes.
- `async def` is the default for routes and dependencies. Blocking calls (sync SDKs, file parsing) go through `asyncio.to_thread` inside adapters, never in routes or use cases.
- No SQLModel and no Asyncer. Tooling is uv + ruff + mypy strict (never ty).
- Anything marked "verify against the pinned FastAPI version" must be checked against the version in `pyproject.toml` before use.
- No FastAPI Cloud deployment, no frontend serving from FastAPI (the frontend is a separate app).

# FastAPI

Conventions for writing FastAPI code in this project (adapted from the official FastAPI skill).

## Quick Reference

* Thin routes and use cases via DI: see [Thin routes](#thin-routes-use-cases-via-di) and [Background tasks](#background-tasks).
* Dependencies: use `Annotated[..., Depends(...)]`; see [Dependency Injection](#dependency-injection) and [the dependency injection reference](references/dependencies.md).
* Response models: prefer return types; use `response_model` when the public response schema differs from the internal return value; see [the response reference](references/responses.md).
* Streaming (JSON Lines, SSE, bytes): see [Streaming](#streaming-json-lines-sse-bytes) and [the streaming reference](references/streaming.md).
* Parameter models: `Query`, `Header`, `Cookie`, and `Form` support models; see [the parameter models reference](references/parameter-models.md).
* Pydantic models: do not use ellipsis or `RootModel`; see [the Pydantic reference](references/pydantic.md).
* Routing: declare router-level prefix, tags, and shared dependencies on the `APIRouter`; see [the path operation reference](references/path-operations.md).
* Tooling and related libraries: uv, ruff, mypy strict, HTTPX; see [the other tools reference](references/other-tools.md).

## Use `Annotated`

Always prefer the `Annotated` style for parameter and dependency declarations. It keeps function signatures working in other contexts, respects the types, and allows reusability.

Use `Annotated` for parameter declarations, including `Path`, `Query`, `Header`, etc.:

```python
from typing import Annotated

from fastapi import FastAPI, Path, Query

app = FastAPI()


@app.get("/items/{item_id}")
async def read_item(
    item_id: Annotated[int, Path(ge=1, description="The item ID")],
    q: Annotated[str | None, Query(max_length=50)] = None,
) -> dict[str, str]:
    return {"message": "Hello World"}
```

Use `Annotated` for dependencies with `Depends()`. Unless asked not to, create a new type alias for the dependency to allow reusing it:

```python
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


async def get_current_user() -> dict[str, str]:
    return {"username": "johndoe"}


CurrentUserDep = Annotated[dict[str, str], Depends(get_current_user)]


@app.get("/items/")
async def read_item(current_user: CurrentUserDep) -> dict[str, str]:
    return {"message": "Hello World"}
```

## Do not use Ellipsis for *path operations* or Pydantic models

Do not use `...` as a default value for required parameters or model fields. It's not needed and not recommended.

```python
from typing import Annotated

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

app = FastAPI()


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float = Field(gt=0)


@app.post("/items/")
async def create_item(item: Item, project_id: Annotated[int, Query()]) -> Item:
    return item
```

See [the Pydantic reference](references/pydantic.md) for more details.

## Return Type or Response Model

When possible, include a return type. It will be used to validate, filter, document, and serialize the response.

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    description: str | None = None


@app.get("/items/me")
async def get_item() -> Item:
    return Item(name="Plumbus", description="All-purpose home device")
```

Return types or response models filter data to avoid exposing sensitive information, and they let Pydantic serialize the data on the Rust side for performance.

Use `response_model` when the type you return is not the same as the public schema you want to validate, filter, document, and serialize. See [the response reference](references/responses.md).

## Performance

Do not use `ORJSONResponse` or `UJSONResponse`, they are deprecated.

Instead, declare a return type or response model. Pydantic will handle the data serialization on the Rust side.

## Including Routers

When declaring routers, prefer to add router-level parameters like prefix, tags, and shared dependencies to the router itself instead of in `include_router()`.

```python
from fastapi import APIRouter, Depends, FastAPI

app = FastAPI()


async def get_current_user() -> dict[str, str]:
    return {"username": "johndoe"}


router = APIRouter(
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/")
async def list_items() -> list[str]:
    return []


app.include_router(router)
```

See [the path operation reference](references/path-operations.md) for more routing patterns.

## Dependency Injection

Use dependencies when the logic can't be declared in Pydantic validation, depends on external resources, needs cleanup with `yield`, or is shared across endpoints.

Apply shared dependencies at the router level via `dependencies=[Depends(...)]`.

See [the dependency injection reference](references/dependencies.md) for `yield` with `scope` and class dependencies.

## Thin routes, use cases via DI

A route only maps HTTP to a DTO, calls one use case and maps the result back. Use cases (and their ports) are built in the composition root and exposed as dependency functions; domain and use-case code never imports FastAPI, SQL drivers, LangChain or provider SDKs.

```python
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.composition import get_ask_question  # composition root
from app.use_cases.ask_question import AskQuestion

router = APIRouter(prefix="/chat", tags=["chat"])


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


AskQuestionDep = Annotated[AskQuestion, Depends(get_ask_question)]


@router.post("/ask")
async def ask(body: AskRequest, use_case: AskQuestionDep) -> AskResponse:
    answer = await use_case.execute(body.question)
    return AskResponse(answer=answer)
```

In tests, override the dependency with `app.dependency_overrides` to inject declared fakes (LLM, embeddings), while the database stays a real PostgreSQL.

## Background tasks

Ingestion runs through `BackgroundTasks`. The task runs after the response is sent, so request-scoped resources are gone.

* The job opens its own resources (DB session/engine, clients) through the composition root; never reuse a `yield` dependency (session, connection) from the request.
* Pass only plain data (IDs, paths) to the task, not request-bound objects.
* Catch errors inside the job and persist the failure (e.g. document `status = "failed"` with a reason); nobody is waiting on the response.

```python
from fastapi import BackgroundTasks

from app.composition import build_ingest_document  # composition root factory


async def run_ingestion(document_id: str) -> None:
    ingest = build_ingest_document()  # opens its own session/resources
    await ingest.execute(document_id)


@router.post("/documents/{document_id}/ingest", status_code=202)
async def start_ingestion(document_id: str, tasks: BackgroundTasks) -> None:
    tasks.add_task(run_ingestion, document_id)
```

## Async vs Sync *path operations*

Default to `async def` for routes and dependencies. Never run blocking code on the event loop: wrap it with `asyncio.to_thread` inside the adapter that owns the blocking call.

```python
import asyncio


def parse_pdf_blocking(path: str) -> str:
    # blocking third-party parser
    return ""


async def parse_pdf(path: str) -> str:
    return await asyncio.to_thread(parse_pdf_blocking, path)
```

Plain `def` routes run in a threadpool; avoid them unless the whole call path is blocking and cannot be wrapped in an adapter.

## Streaming (JSON Lines, SSE, bytes)

SSE via `fastapi.sse` (`EventSourceResponse`, `ServerSentEvent`) is a newer feature: verify against the pinned FastAPI version (pyproject) before use. If it is not available, return a `StreamingResponse` with `media_type="text/event-stream"`.

```python
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent

app = FastAPI()


@app.get("/events", response_class=EventSourceResponse)
async def stream_events() -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(data={"status": "started"}, event="status", id="1")
```

See [the streaming reference](references/streaming.md) for JSON Lines, SSE and byte streaming patterns.

## Tooling

See [the other tools reference](references/other-tools.md): uv, ruff, mypy strict, HTTPX. Never install packages without asking the user.

## Do not use Pydantic RootModels

Do not use Pydantic `RootModel`; instead use regular type annotations with `Annotated` and Pydantic validation utilities.

```python
from typing import Annotated

from fastapi import Body, FastAPI
from pydantic import Field

app = FastAPI()


@app.post("/items/")
async def create_items(
    items: Annotated[list[int], Field(min_length=1), Body()],
) -> list[int]:
    return items
```

FastAPI supports these type annotations and will create a Pydantic `TypeAdapter` for them, so types work normally without custom wrapper models. See [the Pydantic reference](references/pydantic.md).

## Use one HTTP operation per function

Don't mix HTTP operations in a single function. Having one function per HTTP operation helps separate concerns and organize the code.

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str


@app.get("/items/")
async def list_items() -> list[Item]:
    return []


@app.post("/items/")
async def create_item(item: Item) -> Item:
    return item
```

See [the path operation reference](references/path-operations.md) for more examples.
