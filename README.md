# VHIT Robot UI

ROS 2 gateway for controlling the VHIT robot from user-interface inputs.

The repository currently provides the `vhit_robot_ui_gateway` Python package.
It translates left- and right-arrow key presses into signed jog commands for
the ELAC tester. A graphical or web frontend is not included yet.

## Current Functionality

- Publishes jog commands as `std_msgs/msg/Int8` messages.
- Uses `/elac_tester_node/jog` as the default jog topic.
- Maps the left arrow to a negative jog (`-1`).
- Maps the right arrow to a positive jog (`1`).
- Reads keyboard input without blocking the ROS executor.
- Restores the terminal configuration when the node exits normally or through
  Ctrl+C.

The gateway publishes only the jog direction. The target increment, trajectory
duration, and position limits are managed by `vhit_elac_tester`.

## Repository Layout

```text
vhit-robot-ui/
├── README.md
└── ros/
    └── src/
        └── vhit_robot_ui_gateway/
            ├── package.xml
            ├── setup.py
            ├── test/
            └── vhit_robot_ui_gateway/
                ├── gateway_node.py
                ├── jog_publisher.py
                └── keyboard_controller.py
```

## Requirements

- ROS 2 Humble
- Python 3
- `rclpy`
- `std_msgs`
- An active subscriber for the jog topic, normally `elac_tester_node` from the
  `vhit_elac_tester` package

Keyboard control also requires an interactive terminal. It will not start when
standard input is redirected or no TTY is available.

## Build

The `ros/` directory is the colcon workspace root:

```bash
cd /home/<user>/vhit-robot-ui/ros
source /opt/ros/humble/setup.bash
colcon build --packages-select vhit_robot_ui_gateway
source install/setup.bash
```

Source `install/setup.bash` in every new terminal that runs the gateway.

## Start the ELAC Tester

The gateway expects the ELAC tester to be running in manual mode. For an
offline test with ROS 2 mock hardware:

```bash
cd /home/<user>/vhit-robot-demo
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch vhit_elac_tester elac_tester.launch.py \
  use_mock_hardware:=true \
  automatic_test:=false \
  jog_step:=0.01 \
  point_duration_s:=0.25
```

`jog_step` is the position increment in radians applied by the tester for each
received direction command.

## Run the Gateway

In another interactive terminal:

```bash
cd /home/<user>/vhit-robot-ui/ros
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run vhit_robot_ui_gateway gateway_node --ros-args \
  -p keyboard_control:=true
```

Keyboard controls:

| Key | Result |
| --- | --- |
| Left arrow | Publish `-1` for a negative jog. |
| Right arrow | Publish `1` for a positive jog. |
| `Q` | Stop the gateway. |
| Ctrl+C | Stop the gateway. |

Holding an arrow key can generate repeated terminal key events and therefore
multiple jog commands.

## ROS Interface

### Published topic

| Topic | Type | Description |
| --- | --- | --- |
| `/elac_tester_node/jog` | `std_msgs/msg/Int8` | Signed jog direction. Only `-1` and `1` are published. |

The topic can be tested without the gateway:

```bash
ros2 topic pub --once /elac_tester_node/jog \
  std_msgs/msg/Int8 "{data: 1}"
```

```bash
ros2 topic pub --once /elac_tester_node/jog \
  std_msgs/msg/Int8 "{data: -1}"
```

### Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `jog_topic` | `/elac_tester_node/jog` | Topic on which signed jog commands are published. |
| `keyboard_control` | `false` | Enable interactive left- and right-arrow keyboard input. |

To publish on a different topic:

```bash
ros2 run vhit_robot_ui_gateway gateway_node --ros-args \
  -p keyboard_control:=true \
  -p jog_topic:=/my_robot/jog
```

The subscriber must be configured to use the same topic.

## Verify Operation

Inspect the topic from a third sourced terminal:

```bash
ros2 topic echo /elac_tester_node/jog
```

Pressing the left and right arrows should produce messages containing `-1` and
`1`, respectively. The gateway also logs every detected arrow key and every
published direction.

Useful checks:

```bash
ros2 node list
ros2 topic info /elac_tester_node/jog --verbose
ros2 param get /vhit_robot_ui_gateway keyboard_control
ros2 param get /vhit_robot_ui_gateway jog_topic
```

## Tests

Run the package tests from the ROS workspace:

```bash
cd /home/riky/vhit-robot-ui/ros
source /opt/ros/humble/setup.bash
colcon test --packages-select vhit_robot_ui_gateway
colcon test-result --verbose
```

## Troubleshooting

### Arrow keys produce no commands

- Start the gateway with `keyboard_control:=true`.
- Run it directly in an interactive terminal rather than through redirected
  input or a background service.
- Confirm that the gateway and tester use the same `ROS_DOMAIN_ID` and jog
  topic.
- Check the topic directly with `ros2 topic echo`.

### Commands are published but the actuator does not move

- Start `elac_tester_node` with `automatic_test:=false`; its jog subscriber is
  only created in manual mode.
- Wait until the tester reports that it initialized its target from
  `/joint_states`.
- Confirm that `vhit_elac_controller` is active.
- Check the tester's `jog_step`, position limits, and trajectory-point duration.

### Runtime does not reflect source changes

ROS 2 runs the installed package. Rebuild and source the workspace after making
changes:

```bash
cd /home/<user>/vhit-robot-ui/ros
source /opt/ros/humble/setup.bash
colcon build --packages-select vhit_robot_ui_gateway
source install/setup.bash
```

Use the following command to see which installation ROS resolves:

```bash
ros2 pkg prefix vhit_robot_ui_gateway
```

## License

The `vhit_robot_ui_gateway` package is licensed under Apache-2.0. See
`ros/src/vhit_robot_ui_gateway/LICENSE`.
