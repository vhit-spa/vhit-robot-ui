from __future__ import annotations

import rclpy
from rclpy.node import Node

from vhit_robot_ui_gateway.jog_publisher import JogPublisher
from vhit_robot_ui_gateway.keyboard_controller import (
    KeyboardController,
)


class RobotUiGatewayNode(Node):
    def __init__(self) -> None:
        super().__init__("vhit_robot_ui_gateway")

        self.declare_parameter(
            "jog_topic",
            "/elac_tester_node/jog",
        )

        self.declare_parameter(
            "keyboard_control",
            False,
        )

        jog_topic = self.get_parameter("jog_topic").value
        keyboard_control = self.get_parameter(
            "keyboard_control"
        ).value

        self.jog_publisher = JogPublisher(
            node=self,
            topic=jog_topic,
        )

        self.keyboard_controller: KeyboardController | None = None

        if keyboard_control:
            try:
                self.keyboard_controller = KeyboardController(
                    node=self,
                    on_left=self.jog_negative,
                    on_right=self.jog_positive,
                )
            except RuntimeError as exception:
                self.get_logger().error(str(exception))
                raise

        self.get_logger().info(
            f"VHIT robot UI gateway started; jog topic: {jog_topic}"
        )

    def jog_positive(self) -> None:
        self.jog_publisher.jog_positive()

    def jog_negative(self) -> None:
        self.jog_publisher.jog_negative()

    def close(self) -> None:
        if self.keyboard_controller is not None:
            self.keyboard_controller.close()


def main(args=None) -> None:
    rclpy.init(args=args)

    node = RobotUiGatewayNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Gateway interrupted")
    finally:
        node.close()
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()