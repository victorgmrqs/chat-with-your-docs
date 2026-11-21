# Dependency Injection

Use dependencies when:

* They can't be declared in Pydantic validation and require additional logic
* The logic depends on external resources or could block in any other way
* Other dependencies need their results (it's a sub-dependency)
* The logic can be shared by multiple endpoints to do things like error early, handle authentication, etc.
* They need to handle cleanup (e.g., DB sessions, file handles), using dependencies with `yield`
* Their logic needs input data from the request, like headers, query parameters, etc.

## Dependencies with `yield` and `scope`

When using dependencies with `yield`, they can have a `scope` that defines when the exit code is run.

Use the default scope `"request"` to run the exit code after the response is sent back.

```python
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.composition import session_factory  # composition root


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
```

Keep `yield` dependencies for adapters (sessions, clients) owned by the composition root. Routes stay thin: they should not query the session directly but call a use case that receives the repository/port built from it (see "Thin routes, use cases via DI" in SKILL.md). Never reuse a request-scoped `yield` dependency inside a `BackgroundTasks` job; the job opens its own resources.

Use the scope `"function"` when they should run the exit code after the response data is generated but before the response is sent back to the client.

```python
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


def get_username() -> Iterator[str]:
    try:
        yield "Rick"
    finally:
        print("Clean up before response is sent")


UserNameDep = Annotated[str, Depends(get_username, scope="function")]


@app.get("/users/me")
async def get_user_me(username: UserNameDep) -> str:
    return username
```

## Limit dependency concurrency

`Depends(..., max_concurrency=N)` is a newer feature: verify against the pinned FastAPI version (pyproject) before use. Size connection pools in the engine configuration first; the limit is per worker process and applies only if the dependency manages the shared resource.

## Class Dependencies

Avoid creating class dependencies when possible.

If a class is needed, instead create a regular function dependency that returns a class instance.

Do this:

```python
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


@dataclass
class DatabasePaginator:
    offset: int = 0
    limit: int = 100
    q: str | None = None

    def get_page(self) -> dict[str, object]:
        # Simulate a page of data
        return {
            "offset": self.offset,
            "limit": self.limit,
            "q": self.q,
            "items": [],
        }


def get_db_paginator(
    offset: int = 0, limit: int = 100, q: str | None = None
) -> DatabasePaginator:
    return DatabasePaginator(offset=offset, limit=limit, q=q)


PaginatorDep = Annotated[DatabasePaginator, Depends(get_db_paginator)]


@app.get("/items/")
async def read_items(paginator: PaginatorDep) -> dict[str, object]:
    return paginator.get_page()
```

instead of this:

```python
# DO NOT DO THIS
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


class DatabasePaginator:
    def __init__(self, offset: int = 0, limit: int = 100, q: str | None = None) -> None:
        self.offset = offset
        self.limit = limit
        self.q = q

    def get_page(self) -> dict[str, object]:
        # Simulate a page of data
        return {
            "offset": self.offset,
            "limit": self.limit,
            "q": self.q,
            "items": [],
        }


@app.get("/items/")
async def read_items(
    paginator: Annotated[DatabasePaginator, Depends()],
) -> dict[str, object]:
    return paginator.get_page()
```
