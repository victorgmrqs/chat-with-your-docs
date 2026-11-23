"""CWYD-20: the docs behind the web server. nginx proxies `/api/*` with the prefix stripped and
says so in `X-Forwarded-Prefix`; the API then serves its docs and spec as seen from the browser
(`/api/openapi.json`, `servers: [/api]`). Direct calls (`:8000`) carry no header and keep the
plain paths, which is why this is not `uvicorn --root-path` (that applies to every request)."""

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send


class ForwardedPrefix:
    """Pure ASGI middleware: sets `root_path` only when the header equals the configured prefix.

    Any other value is ignored, so a client cannot make the API advertise an arbitrary prefix.
    The prefix is also prepended to `path`, as the ASGI spec (and `uvicorn --root-path`) does:
    Starlette strips `root_path` before routing, so `/chat` is routed while an already prefixed
    `/api/chat` (`/api/api/chat` at nginx, outside its rate-limited locations, DOM-27) is a 404.
    """

    def __init__(self, app: ASGIApp, prefix: str) -> None:
        self.app = app
        self._prefix = prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and Headers(scope=scope).get("x-forwarded-prefix") == self._prefix
        ):
            prefix = self._prefix
            scope = {
                **scope,
                "root_path": scope.get("root_path", "") + prefix,
                "path": prefix + scope["path"],
                "raw_path": prefix.encode() + (scope.get("raw_path") or scope["path"].encode()),
            }
        await self.app(scope, receive, send)
