from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Int8

from vhit_robot_ui_gateway.api_server import ApiServer
from vhit_robot_ui_gateway.jog_publisher import JogPublisher
from vhit_robot_ui_gateway.keyboard_controller import KeyboardController
from vhit_robot_ui_gateway.state_store import RobotStateStore


class RobotUiGatewayNode(Node):
    VALID_CONTROL_MODES = {
        "keyboard",
        "web",
        "topic",
    }

    def __init__(self) -> None:
        super().__init__("vhit_robot_ui_gateway")

        self.declare_parameter(
            "control_mode",
            "topic",
        )
        self.declare_parameter(
            "jog_output_topic",
            "/elac_tester_node/jog",
        )
        self.declare_parameter(
            "jog_input_topic",
            "~/jog",
        )
        self.declare_parameter(
            "joint_state_topic",
            "/joint_states",
        )
        self.declare_parameter(
            "joint_name",
            "elac_node",
        )
        self.declare_parameter(
            "web_host",
            "127.0.0.1",
        )
        self.declare_parameter(
            "web_port",
            8080,
        )

        self._control_mode = str(
            self.get_parameter("control_mode").value
        ).lower()

        if self._control_mode not in self.VALID_CONTROL_MODES:
            valid_modes = ", ".join(
                sorted(self.VALID_CONTROL_MODES)
            )
            raise ValueError(
                f"Invalid control_mode '{self._control_mode}'. "
                f"Expected one of: {valid_modes}"
            )

        jog_output_topic = str(
            self.get_parameter("jog_output_topic").value
        )
        joint_state_topic = str(
            self.get_parameter("joint_state_topic").value
        )
        joint_name = str(
            self.get_parameter("joint_name").value
        )

        self._command_queue: Queue[int] = Queue(maxsize=32)

        self._state_store = RobotStateStore(
            joint_name=joint_name,
        )

        self._jog_publisher = JogPublisher(
            node=self,
            topic=jog_output_topic,
        )

        self._joint_state_subscription = self.create_subscription(
            JointState,
            joint_state_topic,
            self._state_store.update_from_joint_state,
            10,
        )

        self._command_timer = self.create_timer(
            0.02,
            self._process_command_queue,
        )

        self._keyboard_controller: KeyboardController | None = None
        self._api_server: ApiServer | None = None
        self._jog_input_subscription = None

        self._configure_control_mode()

        self.get_logger().info(
            f"Gateway started in '{self._control_mode}' mode"
        )
        self.get_logger().info(
            f"Publishing jog commands to '{jog_output_topic}'"
        )

    def _configure_control_mode(self) -> None:
        if self._control_mode == "keyboard":
            self._configure_keyboard_control()
            return

        if self._control_mode == "web":
            self._configure_web_control()
            return

        if self._control_mode == "topic":
            self._configure_topic_control()
            return

        # This should be unreachable because the mode was validated.
        raise RuntimeError(
            f"Unsupported control mode: {self._control_mode}"
        )

    def _configure_keyboard_control(self) -> None:
        self._keyboard_controller = KeyboardController(
            node=self,
            on_left=lambda: self._enqueue_jog(-1),
            on_right=lambda: self._enqueue_jog(1),
        )

    def _configure_web_control(self) -> None:
        web_host = str(
            self.get_parameter("web_host").value
        )
        web_port = int(
            self.get_parameter("web_port").value
        )

        package_share = Path(
            get_package_share_directory(
                "vhit_robot_ui_gateway"
            )
        )

        self._api_server = ApiServer(
            host=web_host,
            port=web_port,
            www_directory=package_share / "www",
            command_queue=self._command_queue,
            state_store=self._state_store,
        )
        self._api_server.start()

        self.get_logger().info(
            f"Web UI available at http://{web_host}:{web_port}"
        )

    def _configure_topic_control(self) -> None:
        jog_input_topic = str(
            self.get_parameter("jog_input_topic").value
        )

        self._jog_input_subscription = self.create_subscription(
            Int8,
            jog_input_topic,
            self._on_jog_topic,
            10,
        )

        self.get_logger().info(
            f"Listening for jog commands on '{jog_input_topic}'"
        )

    def _on_jog_topic(self, message: Int8) -> None:
        self._enqueue_jog(int(message.data))

    def _enqueue_jog(self, direction: int) -> None:
        if direction not in (-1, 1):
            self.get_logger().warning(
                f"Rejected invalid jog direction: {direction}"
            )
            return

        state = self._state_store.snapshot()

        if not state["feedback_fresh"]:
            self.get_logger().warning(
                "Rejected jog command because feedback is stale"
            )
            return

        try:
            self._command_queue.put_nowait(direction)
        except Exception:
            self.get_logger().warning(
                "Jog command queue is full"
            )

    def _process_command_queue(self) -> None:
        while True:
            try:
                direction = self._command_queue.get_nowait()
            except Empty:
                return

            try:
                self._jog_publisher.publish_direction(direction)
            except Exception as exception:
                self.get_logger().error(
                    f"Failed to publish jog command: {exception}"
                )

    def close(self) -> None:
        if self._keyboard_controller is not None:
            self._keyboard_controller.close()

        if self._api_server is not None:
            self._api_server.stop()


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