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

import re

from vhit_robot_ui_gateway.state_store import RobotStateStore
from vhit_robot_ui_gateway.trajectory_publisher import TrajectoryPublisher
from vhit_robot_ui_gateway.waypoint_repository import WaypointRepository
from vhit_robot_ui_gateway.threading_unix_socket_server import ThreadingUnixHTTPServer

def make_request_handler(
    www_directory: Path,
    command_queue: Queue[int],
    state_store: RobotStateStore,
    waypoint_repository: WaypointRepository,
    trajectory_publisher: TrajectoryPublisher,
    default_move_duration: float,
) -> type[SimpleHTTPRequestHandler]:

    class GatewayRequestHandler(SimpleHTTPRequestHandler):
        ROUTE_PREFIX = "/vhit-robot-ui"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(
                *args,
                directory=str(www_directory),
                **kwargs,
            )

        def _application_path(self) -> str | None:
            path = urlparse(self.path).path

            if path == self.ROUTE_PREFIX:
                return "/"

            if path.startswith(self.ROUTE_PREFIX + "/"):
                return path[len(self.ROUTE_PREFIX):]

            # Preserve direct local-development access.
            if not path.startswith(self.ROUTE_PREFIX):
                return path

            return None

        def do_GET(self) -> None:
            path = self._application_path()

            if path is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            if path == "/api/v1/waypoints":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "waypoints": waypoint_repository.list(),
                    },
                )
                return

            if path == "/api/v1/state":
                self._send_json(
                    HTTPStatus.OK,
                    state_store.snapshot(),
                )
                return

            if path == "/":
                path = "/index.html"

            self.path = path
            super().do_GET()

        def do_POST(self) -> None:
            path = self._application_path()
            execute_match = re.fullmatch(
                r"/api/v1/waypoints/([^/]+)/execute",
                path,
            )

            if execute_match:
                waypoint_id = execute_match.group(1)
                self._handle_execute_POST(waypoint_id = waypoint_id)
                return
            if path == "/api/v1/playback":
                self._handle_playback_POST()
                return
            if path == "/api/v1/jog":
                self._handle_jog_POST()
                return
            if path == "/api/v1/waypoints":
                self._handle_waypoints_POST()
                return
            else:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "Endpoint not found"},
                )
                return
        
        def _handle_jog_POST(self) -> None:
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

        def _handle_waypoints_POST(self) -> None:
            
            request = self._read_json()
            state = state_store.snapshot()

            if not state["feedback_fresh"]:
                self._send_json(
                    HTTPStatus.CONFLICT,
                    {
                        "error": (
                            "Cannot teach waypoint because "
                            "feedback is unavailable or stale"
                        )
                    },
                )
                return

            waypoint = waypoint_repository.create(
                name=str(request.get("name", "")),
                position=float(state["position"]),
            )

            self._send_json(
                HTTPStatus.CREATED,
                waypoint,
            )
            return
        
        def _handle_execute_POST(self, waypoint_id: str) -> None:
            waypoint = waypoint_repository.get(
                waypoint_id
            )

            if waypoint is None:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "Waypoint not found"},
                )
                return

            state = state_store.snapshot()

            if not state["feedback_fresh"]:
                self._send_json(
                    HTTPStatus.CONFLICT,
                    {"error": "Robot feedback is stale"},
                )
                return

            request = self._read_json()
            duration = float(
                request.get(
                    "duration",
                    default_move_duration,
                )
            )

            trajectory_publisher.move_to(
                position=float(waypoint["position"]),
                duration=duration,
            )

            self._send_json(
                HTTPStatus.ACCEPTED,
                {
                    "accepted": True,
                    "waypoint": waypoint,
                    "duration": duration,
                },
            )


        def _handle_playback_POST(self) -> None:
            request = self._read_json()

            move_duration = float(
                request.get(
                    "move_duration",
                    default_move_duration,
                )
            )

            hold_time = float(
                request.get("hold_time", 0.0)
            )

            waypoints = waypoint_repository.list()

            if not waypoints:
                self._send_json(
                    HTTPStatus.CONFLICT,
                    {"error": "No waypoints are stored"},
                )
                return

            state = state_store.snapshot()

            if not state["feedback_fresh"]:
                self._send_json(
                    HTTPStatus.CONFLICT,
                    {"error": "Robot feedback is stale"},
                )
                return

            trajectory_publisher.execute(
                [
                    {
                        "position": waypoint["position"],
                        "duration": move_duration,
                        "hold_time": hold_time,
                    }
                    for waypoint in waypoints
                ]
            )

            self._send_json(
                HTTPStatus.ACCEPTED,
                {
                    "accepted": True,
                    "waypoint_count": len(waypoints),
                },
            )
            return
        
        def do_DELETE(self) -> None:
            path = self._application_path()

            match = re.fullmatch(
                r"/api/v1/waypoints/([^/]+)",
                path,
            )

            if not match:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "Endpoint not found"},
                )
                return

            deleted = waypoint_repository.delete(
                match.group(1)
            )

            if not deleted:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "Waypoint not found"},
                )
                return

            self._send_json(
                HTTPStatus.OK,
                {"deleted": True},
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
        waypoint_repository: WaypointRepository,
        trajectory_publisher: TrajectoryPublisher,
        default_move_duration: float,
        socket_path: Path | None = None,
    ) -> None:
        handler = make_request_handler(
            www_directory=www_directory,
            command_queue=command_queue,
            state_store=state_store,
            waypoint_repository=waypoint_repository,
            trajectory_publisher=trajectory_publisher,
            default_move_duration=default_move_duration,
        )

        self._socket_path = socket_path

        if socket_path is not None:
            socket_path.parent.mkdir(parents=True, exist_ok=True)
            socket_path.unlink(missing_ok=True)

            self._server = ThreadingUnixHTTPServer(
                str(socket_path),
                handler,
            )
        else:
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

        if self._socket_path is not None:
            self._socket_path.unlink(missing_ok=True)