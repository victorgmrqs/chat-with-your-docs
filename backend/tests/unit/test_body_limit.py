"""BodySizeLimit (DOM-26) driven as a raw ASGI app: no server, no spooling."""

import json
from typing import Any

from starlette.types import Message, Receive, Scope, Send

from app.api.body_limit import MULTIPART_OVERHEAD_BYTES, BodySizeLimit
from tests.factories import VALID_SETTINGS, make_settings

MB = 1024 * 1024
LIMIT = 1 * MB + MULTIPART_OVERHEAD_BYTES  # max_upload_mb=1
CHUNK = 256 * 1024


class ReadingApp:
    """Downstream app that reads the whole body, then answers 200 with its size."""

    def __init__(self) -> None:
        self.bytes_read = 0
        self.called = False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.called = True
        while True:
            message = await receive()
            self.bytes_read += len(message.get("body", b""))
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": str(self.bytes_read).encode()})


def _scope(headers: list[tuple[bytes, bytes]] | None = None) -> Scope:
    return {
        "type": "http",
        "method": "POST",
        "path": "/documents",
        "headers": headers or [],
        "query_string": b"",
    }


async def _run(
    app: Any, scope: Scope, total: int, limit_mb: int | None = 1
) -> tuple[list[Message], int]:
    """Stream `total` bytes in chunks; returns the sent messages and the chunks consumed."""
    chunks = [CHUNK] * (total // CHUNK) + ([total % CHUNK] if total % CHUNK else [])
    consumed = 0

    async def receive() -> Message:
        nonlocal consumed
        consumed += 1
        size = chunks[consumed - 1] if consumed <= len(chunks) else 0
        return {"type": "http.request", "body": b"x" * size, "more_body": consumed < len(chunks)}

    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    settings = None
    if limit_mb is not None:
        settings = make_settings(VALID_SETTINGS["database_url"], max_upload_mb=limit_mb)
    await BodySizeLimit(app, lambda: settings)(scope, receive, send)
    return sent, consumed


def _status(sent: list[Message]) -> int:
    return int(next(m["status"] for m in sent if m["type"] == "http.response.start"))


def _body(sent: list[Message]) -> dict[str, Any]:
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    result: dict[str, Any] = json.loads(body)
    return result


async def test_body_limit_streamed_body_over_limit_is_cut_off() -> None:
    app = ReadingApp()

    sent, consumed = await _run(app, _scope(), total=8 * MB)

    assert _status(sent) == 413
    assert _body(sent)["code"] == "file_too_large"
    assert "request_id" in _body(sent)
    assert app.bytes_read <= LIMIT  # stopped at the limit, not after spooling 8 MB
    assert consumed < (8 * MB) // CHUNK


async def test_body_limit_declared_length_over_limit_is_rejected_unread() -> None:
    app = ReadingApp()
    headers = [(b"content-length", str(LIMIT + 1).encode())]

    sent, consumed = await _run(app, _scope(headers), total=LIMIT + 1)

    assert _status(sent) == 413
    assert app.called is False
    assert consumed == 0


async def test_body_limit_body_within_limit_reaches_the_app() -> None:
    app = ReadingApp()

    sent, _ = await _run(app, _scope(), total=LIMIT)

    assert _status(sent) == 200
    assert app.bytes_read == LIMIT


async def test_body_limit_before_settings_are_loaded_passes_through() -> None:
    app = ReadingApp()

    sent, _ = await _run(app, _scope(), total=4 * MB, limit_mb=None)

    assert _status(sent) == 200
    assert app.bytes_read == 4 * MB
