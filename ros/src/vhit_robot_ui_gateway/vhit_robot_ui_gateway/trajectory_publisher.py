from __future__ import annotations

from builtin_interfaces.msg import Duration
from rclpy.node import Node
from trajectory_msgs.msg import (
    JointTrajectory,
    JointTrajectoryPoint,
)


def duration_from_seconds(seconds: float) -> Duration:
    if seconds <= 0:
        raise ValueError("Duration must be greater than zero")

    whole_seconds = int(seconds)
    nanoseconds = int(
        (seconds - whole_seconds) * 1_000_000_000
    )

    return Duration(
        sec=whole_seconds,
        nanosec=nanoseconds,
    )


class TrajectoryPublisher:
    def __init__(
        self,
        node: Node,
        topic: str,
        joint_name: str,
    ) -> None:
        self._node = node
        self._topic = topic
        self._joint_name = joint_name

        self._publisher = node.create_publisher(
            JointTrajectory,
            topic,
            10,
        )

        node.get_logger().info(
            f"Trajectory publisher created for '{topic}'"
        )

    def move_to(
        self,
        position: float,
        duration: float,
    ) -> None:
        self.execute(
            points=[
                {
                    "position": position,
                    "duration": duration,
                    "hold_time": 0.0,
                }
            ]
        )

    def execute(
        self,
        points: list[dict],
    ) -> None:
        if not points:
            raise ValueError(
                "Trajectory must contain at least one point"
            )

        message = JointTrajectory()
        message.joint_names = [self._joint_name]

        elapsed = 0.0

        for item in points:
            duration = float(item["duration"])
            hold_time = float(
                item.get("hold_time", 0.0)
            )
            position = float(item["position"])

            elapsed += duration

            trajectory_point = JointTrajectoryPoint()
            trajectory_point.positions = [position]
            trajectory_point.time_from_start = (
                duration_from_seconds(elapsed)
            )

            message.points.append(trajectory_point)

            if hold_time > 0:
                elapsed += hold_time

                hold_point = JointTrajectoryPoint()
                hold_point.positions = [position]
                hold_point.time_from_start = (
                    duration_from_seconds(elapsed)
                )

                message.points.append(hold_point)

        self._publisher.publish(message)

        self._node.get_logger().info(
            f"Published trajectory with "
            f"{len(message.points)} points"
        )