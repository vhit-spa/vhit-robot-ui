from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class WaypointRepository:
    def __init__(self, storage_file: Path) -> None:
        self._storage_file = storage_file
        self._lock = threading.Lock()
        self._waypoints: list[dict[str, Any]] = []

        self._storage_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._load()

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                waypoint.copy()
                for waypoint in self._waypoints
            ]

    def create(
        self,
        name: str,
        position: float,
    ) -> dict[str, Any]:
        waypoint = {
            "id": str(uuid.uuid4()),
            "name": name.strip() or self._default_name(),
            "position": float(position),
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        with self._lock:
            self._waypoints.append(waypoint)
            self._save_locked()

        return waypoint.copy()

    def get(self, waypoint_id: str) -> dict[str, Any] | None:
        with self._lock:
            for waypoint in self._waypoints:
                if waypoint["id"] == waypoint_id:
                    return waypoint.copy()

        return None

    def delete(self, waypoint_id: str) -> bool:
        with self._lock:
            original_size = len(self._waypoints)

            self._waypoints = [
                waypoint
                for waypoint in self._waypoints
                if waypoint["id"] != waypoint_id
            ]

            if len(self._waypoints) == original_size:
                return False

            self._save_locked()
            return True

    def update_name(
        self,
        waypoint_id: str,
        name: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            for waypoint in self._waypoints:
                if waypoint["id"] != waypoint_id:
                    continue

                waypoint["name"] = (
                    name.strip() or waypoint["name"]
                )

                self._save_locked()
                return waypoint.copy()

        return None

    def reorder(self, waypoint_ids: list[str]) -> None:
        with self._lock:
            by_id = {
                waypoint["id"]: waypoint
                for waypoint in self._waypoints
            }

            if set(waypoint_ids) != set(by_id):
                raise ValueError(
                    "Waypoint order must contain every waypoint exactly once"
                )

            self._waypoints = [
                by_id[waypoint_id]
                for waypoint_id in waypoint_ids
            ]

            self._save_locked()

    def _default_name(self) -> str:
        return f"Waypoint {len(self._waypoints) + 1}"

    def _load(self) -> None:
        if not self._storage_file.exists():
            return

        try:
            data = json.loads(
                self._storage_file.read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, json.JSONDecodeError):
            return

        if isinstance(data, list):
            self._waypoints = data

    def _save_locked(self) -> None:
        temporary_file = self._storage_file.with_suffix(
            ".tmp"
        )

        temporary_file.write_text(
            json.dumps(
                self._waypoints,
                indent=2,
                allow_nan=False,
            ),
            encoding="utf-8",
        )

        os.replace(
            temporary_file,
            self._storage_file,
        )