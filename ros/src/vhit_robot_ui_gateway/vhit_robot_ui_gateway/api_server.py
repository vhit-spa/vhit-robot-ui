from __future__ import annotations

import json
import threading
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Full, Queue
from typing import Any
from urllib.parse import urlparse

from vhit_robot_ui_gateway.state_store import RobotStateStore


def make_request_handler(
    www_directory: Path,
    command_queue: Queue[int],
    state_store: RobotStateStore,
) -> type[SimpleHTTPRequestHandler]:

    class GatewayRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(
                *args,
                directory=str(www_directory),
                **kwargs,
            )

        def do_GET(self) -> None:
            path = urlparse(self.path).path

            if path == "/api/v1/state":
                self._send_json(
                    HTTPStatus.OK,
                    state_store.snapshot(),
                )
                return

            if path == "/":
                self.path = "/index.html"

            super().do_GET()

        def do_POST(self) -> None:
            path = urlparse(self.path).path

            if path != "/api/v1/jog":
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "Endpoint not found"},
                )
                return

            try:
                request = self._read_json()
                direction = int(request["direction"])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "error": (
                            "Request must contain direction equal to -1 or 1"
                        )
                    },
                )
                return

            if direction not in (-1, 1):
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "direction must be -1 or 1"},
                )
                return

            state = state_store.snapshot()

            if not state["feedback_fresh"]:
                self._send_json(
                    HTTPStatus.CONFLICT,
                    {"error": "Robot feedback is unavailable or stale"},
                )
                return

            try:
                command_queue.put_nowait(direction)
            except Full:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"error": "Command queue is full"},
                )
                return

            self._send_json(
                HTTPStatus.ACCEPTED,
                {
                    "accepted": True,
                    "direction": direction,
                },
            )

        def _read_json(self) -> dict[str, Any]:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            body = self.rfile.read(content_length)

            if not body:
                return {}

            result = json.loads(body.decode("utf-8"))

            if not isinstance(result, dict):
                raise TypeError("JSON body must be an object")

            return result

        def _send_json(
            self,
            status: HTTPStatus,
            payload: dict[str, Any],
        ) -> None:
            encoded = json.dumps(
                payload,
                allow_nan=False,
            ).encode("utf-8")

            self.send_response(status)
            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8",
            )
            self.send_header(
                "Content-Length",
                str(len(encoded)),
            )
            self.end_headers()
            self.wfile.write(encoded)

    return GatewayRequestHandler


class ApiServer:
    def __init__(
        self,
        host: str,
        port: int,
        www_directory: Path,
        command_queue: Queue[int],
        state_store: RobotStateStore,
    ) -> None:
        handler = make_request_handler(
            www_directory=www_directory,
            command_queue=command_queue,
            state_store=state_store,
        )

        self._server = ThreadingHTTPServer(
            (host, port),
            handler,
        )

        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="vhit-ui-http-server",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2.0)