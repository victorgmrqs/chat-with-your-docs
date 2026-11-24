"""DOM-23: one request id per HTTP request, on every response and every error body."""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-ID"


def request_id_of(request: Request) -> uuid.UUID:
    """The request's id, made on first use. Never taken from the client: a supplied id could
    point a report at someone else's trace. Also a FastAPI dependency."""
    request_id: uuid.UUID | None = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = uuid.uuid4()
        request.state.request_id = request_id
    return request_id


async def add_request_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """HTTP middleware. Unhandled errors bypass it: the 500 handler sets the header itself."""
    request_id = request_id_of(request)
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = str(request_id)
    return response
