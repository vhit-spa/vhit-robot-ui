from __future__ import annotations

import math
import threading
import time
from typing import Any

from sensor_msgs.msg import JointState


class RobotStateStore:
    def __init__(self, joint_name: str) -> None:
        self._joint_name = joint_name
        self._position: float | None = None
        self._velocity: float | None = None
        self._last_update: float | None = None
        self._lock = threading.Lock()

    def update_from_joint_state(self, message: JointState) -> None:
        try:
            index = message.name.index(self._joint_name)
        except ValueError:
            return

        if index >= len(message.position):
            return

        position = float(message.position[index])

        if not math.isfinite(position):
            return

        velocity: float | None = None

        if index < len(message.velocity):
            candidate_velocity = float(message.velocity[index])

            if math.isfinite(candidate_velocity):
                velocity = candidate_velocity

        with self._lock:
            self._position = position
            self._velocity = velocity
            self._last_update = time.monotonic()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            position = self._position
            velocity = self._velocity
            last_update = self._last_update

        age_seconds = (
            time.monotonic() - last_update
            if last_update is not None
            else None
        )

        return {
            "joint": self._joint_name,
            "position": position,
            "velocity": velocity,
            "feedback_available": last_update is not None,
            "feedback_age_seconds": age_seconds,
            "feedback_fresh": (
                age_seconds is not None
                and age_seconds < 1.0
            ),
        }