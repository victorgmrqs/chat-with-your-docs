"""Local HTTP server standing in for an LLM provider (contract tests, no network).

Transport-agnostic: the provider SDKs talk real HTTP to 127.0.0.1, whatever HTTP library
they use internally. Each request consumes the next scripted reply.
"""

import json
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


@dataclass(frozen=True)
class JsonReply:
    body: dict[str, Any]
    status: int = 200


@dataclass(frozen=True)
class Hang:
    """Answer only after `seconds`: longer than the client timeout means a timeout."""

    seconds: float


@dataclass
class ProviderStub:
    base_url: str
    replies: list[JsonReply | Hang] = field(default_factory=list)
    requests: list[dict[str, Any]] = field(default_factory=list)


@contextmanager
def provider_stub() -> Iterator[ProviderStub]:
    stub = ProviderStub(base_url="")

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            stub.requests.append({"path": self.path, "body": json.loads(self.rfile.read(length))})
            reply = stub.replies.pop(0) if stub.replies else JsonReply({"error": "no reply"}, 500)
            if isinstance(reply, Hang):
                time.sleep(reply.seconds)
                reply = JsonReply({"error": "too late"}, 500)
            payload = json.dumps(reply.body).encode()
            try:
                self.send_response(reply.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except BrokenPipeError, ConnectionResetError:
                pass  # the client gave up (timeout test)

        def log_message(self, format: str, *args: Any) -> None:
            pass  # keep test output clean

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    stub.base_url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()
