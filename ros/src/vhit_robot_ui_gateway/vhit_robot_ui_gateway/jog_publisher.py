from __future__ import annotations

from std_msgs.msg import Int8

from rclpy.node import Node
from rclpy.publisher import Publisher


class JogPublisher:
    """Publishes positive and negative jog commands to the ELAC tester."""

    NEGATIVE_DIRECTION = -1
    POSITIVE_DIRECTION = 1

    def __init__(
        self,
        node: Node,
        topic: str = "/elac_tester_node/jog",
    ) -> None:
        self._node = node
        self._topic = topic

        self._publisher: Publisher = node.create_publisher(
            Int8,
            topic,
            10,
        )

        self._node.get_logger().info(
            f"ELAC jog publisher created for topic '{topic}'"
        )

    @property
    def topic(self) -> str:
        return self._topic

    def jog_positive(self) -> None:
        self.publish_direction(self.POSITIVE_DIRECTION)

    def jog_negative(self) -> None:
        self.publish_direction(self.NEGATIVE_DIRECTION)

    def publish_direction(self, direction: int) -> None:
        if direction not in (
            self.NEGATIVE_DIRECTION,
            self.POSITIVE_DIRECTION,
        ):
            raise ValueError(
                f"Invalid jog direction {direction}. "
                "Expected -1 or 1."
            )

        message = Int8()
        message.data = direction

        self._publisher.publish(message)

        self._node.get_logger().info(
            f"Published jog direction {direction} on '{self._topic}'"
        )