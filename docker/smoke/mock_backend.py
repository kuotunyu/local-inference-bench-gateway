"""Tiny standard-library OpenAI-shaped backend used only by CPU Compose smoke tests."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROLE = os.environ.get("MOCK_ROLE", "fallback")


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, content: dict) -> None:
        body = json.dumps(content).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self._send(
                200,
                {
                    "object": "list",
                    "data": [{"id": f"mock-{ROLE}", "object": "model"}],
                },
            )
            return
        self._send(404, {"error": {"message": "not found", "type": "invalid_request_error"}})

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            self._send(400, {"error": {"message": "invalid JSON", "type": "invalid_request_error"}})
            return
        if self.path != "/v1/chat/completions":
            self._send(404, {"error": {"message": "not found", "type": "invalid_request_error"}})
            return
        if ROLE == "primary":
            self._send(
                503, {"error": {"message": "controlled primary failure", "type": "api_error"}}
            )
            return
        self._send(
            200,
            {
                "id": "chatcmpl-smoke",
                "object": "chat.completion",
                "created": 0,
                "model": request.get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "fallback-ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    def log_message(self, _format: str, *_args) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
