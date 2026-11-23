"""DOM-26: request bodies above MAX_UPLOAD_MB plus multipart overhead are cut off before
Starlette spools them. nginx caps the proxied path; this covers direct calls to the API."""

from collections.abc import Callable

from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.errors import STATUS_BY_ERROR, error_json
from app.config import Settings
from app.domain.documents import FileTooLarge

MULTIPART_OVERHEAD_BYTES = 1024 * 1024  # boundaries and part headers around the file


class _BodyTooLarge(Exception):
    pass


class BodySizeLimit:
    """Pure ASGI middleware (not BaseHTTPMiddleware): it sees the body as it streams in.

    `settings` returns None until they are loaded (lifespan): no limit then.
    """

    def __init__(self, app: ASGIApp, settings: Callable[[], Settings | None]) -> None:
        self.app = app
        self._settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        settings = self._settings() if scope["type"] == "http" else None
        if settings is None:
            await self.app(scope, receive, send)
            return
        limit = settings.max_upload_bytes + MULTIPART_OVERHEAD_BYTES
        limit_mb = settings.max_upload_mb

        declared = Headers(scope=scope).get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await self._reject(scope, receive, send, limit_mb)  # the body is never read
            return

        received = 0
        exceeded = response_started = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    raise _BodyTooLarge
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal response_started
            if exceeded:  # the app's answer to a cut-off body is replaced by the 413
                return
            response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            # FastAPI may wrap the cut-off as a body parsing error; only ours is swallowed.
            if not exceeded:
                raise
        if exceeded and not response_started:
            await self._reject(scope, receive, send, limit_mb)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send, limit_mb: int) -> None:
        error = FileTooLarge(limit_mb)
        response = error_json(
            Request(scope), error.code, error.message, STATUS_BY_ERROR[FileTooLarge]
        )
        await response(scope, receive, send)
