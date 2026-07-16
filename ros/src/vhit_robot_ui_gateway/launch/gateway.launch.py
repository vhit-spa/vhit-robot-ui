from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    control_mode = LaunchConfiguration("control_mode")
    jog_output_topic = LaunchConfiguration("jog_output_topic")
    jog_input_topic = LaunchConfiguration("jog_input_topic")
    joint_state_topic = LaunchConfiguration("joint_state_topic")
    joint_name = LaunchConfiguration("joint_name")
    web_host = LaunchConfiguration("web_host")
    web_port = LaunchConfiguration("web_port")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "control_mode",
                default_value="topic",
                choices=[
                    "keyboard",
                    "web",
                    "topic",
                ],
                description=(
                    "Gateway command source: keyboard, web, or topic"
                ),
            ),
            DeclareLaunchArgument(
                "jog_output_topic",
                default_value="/elac_tester_node/jog",
                description=(
                    "Jog topic used to send commands to the ELAC tester"
                ),
            ),
            DeclareLaunchArgument(
                "jog_input_topic",
                default_value="/vhit_robot_ui_gateway/jog",
                description=(
                    "Jog command topic consumed when control_mode=topic"
                ),
            ),
            DeclareLaunchArgument(
                "joint_state_topic",
                default_value="/joint_states",
                description="Joint-state feedback topic",
            ),
            DeclareLaunchArgument(
                "joint_name",
                default_value="elac_node",
                description="Joint monitored by the gateway",
            ),
            DeclareLaunchArgument(
                "web_host",
                default_value="127.0.0.1",
                description=(
                    "HTTP server address used when control_mode=web"
                ),
            ),
            DeclareLaunchArgument(
                "web_port",
                default_value="8080",
                description=(
                    "HTTP server port used when control_mode=web"
                ),
            ),
            DeclareLaunchArgument(
                "trajectory_topic",
                default_value=(
                    "/vhit_elac_controller/joint_trajectory"
                ),
            ),
            DeclareLaunchArgument(
                "waypoint_storage_file",
                default_value=(
                    "~/.vhit_robot_ui/waypoints.json"
                ),
            ),
            DeclareLaunchArgument(
                "waypoint_move_duration",
                default_value="1.0",
            ),
            Node(
                package="vhit_robot_ui_gateway",
                executable="gateway_node",
                name="vhit_robot_ui_gateway",
                output="screen",
                emulate_tty=True,
                parameters=[
                    {
                        "control_mode": control_mode,
                        "jog_output_topic": jog_output_topic,
                        "jog_input_topic": jog_input_topic,
                        "joint_state_topic": joint_state_topic,
                        "joint_name": joint_name,
                        "web_host": web_host,
                        "web_port": web_port,
                        "trajectory_topic": LaunchConfiguration(
                            "trajectory_topic"
                        ),
                        "waypoint_storage_file": LaunchConfiguration(
                            "waypoint_storage_file"
                        ),
                         "waypoint_move_duration": ParameterValue(
                            LaunchConfiguration(
                                "waypoint_move_duration"
                            ),
                            value_type=float,
                        ),
                    }
                ],
            ),
        ]
    )