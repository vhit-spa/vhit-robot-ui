# VHIT Robot UI

ROS 2 gateway for controlling the VHIT ELAC robot through keyboard input, the
built-in web interface, or a ROS topic.

The `vhit_robot_ui_gateway` package converts commands from the selected input
mode into signed jog messages for `vhit_elac_tester`. It also monitors joint
state feedback and rejects commands when feedback is unavailable or more than
one second old.

## Features

- Three mutually exclusive control modes: `keyboard`, `web`, and `topic`.
- Publishes signed jog commands as `std_msgs/msg/Int8` messages.
- Uses `/elac_tester_node/jog` as the default output topic.
- Maps negative/left commands to `-1` and positive/right commands to `1`.
- Monitors the configured joint through `sensor_msgs/msg/JointState`.
- Provides a browser UI with position feedback in `web` mode.

The gateway publishes only the jog direction. The target increment, trajectory
duration, and position limits are managed by `vhit_elac_tester`.

## Repository Layout

```text
vhit-robot-ui/
├── README.md
└── ros/
    └── src/
        └── vhit_robot_ui_gateway/
            ├── launch/
            │   └── gateway.launch.py
            ├── test/
            ├── vhit_robot_ui_gateway/
            │   ├── api_server.py
            │   ├── gateway_node.py
            │   ├── jog_publisher.py
            │   ├── keyboard_controller.py
            │   └── state_store.py
            └── www/
```

## Requirements

- ROS 2 Humble
- Python 3
- `rclpy`
- `std_msgs`
- `sensor_msgs`
- `ament_index_python`
- An active subscriber for the output jog topic, normally
  `elac_tester_node` from the `vhit_elac_tester` package
- Joint state feedback containing the configured joint name

Keyboard mode also requires an interactive terminal. It cannot start when
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

Run one of the following modes in a separate terminal after sourcing the UI
workspace:

```bash
cd /home/<user>/vhit-robot-ui/ros
source /opt/ros/humble/setup.bash
source install/setup.bash
```

Only one control mode is active for each gateway process.

### Keyboard mode

Keyboard mode reads arrow keys directly from the terminal:

```bash
ros2 launch vhit_robot_ui_gateway gateway.launch.py \
  control_mode:=keyboard
```

| Key | Result |
| --- | --- |
| Left arrow | Request a negative jog (`-1`). |
| Right arrow | Request a positive jog (`1`). |
| `Q` | Stop the gateway. |
| Ctrl+C | Stop the gateway. |

Holding an arrow key can generate repeated terminal key events and therefore
multiple jog commands.

### Web mode

Web mode starts the HTTP server and built-in browser interface:

```bash
ros2 launch vhit_robot_ui_gateway gateway.launch.py \
  control_mode:=web \
  web_host:=127.0.0.1 \
  web_port:=8080
```

Open `http://127.0.0.1:8080` in a browser. Use the left and right buttons or
the browser's left and right arrow keys to jog. The page displays the latest
position of the configured joint.

The default host accepts connections only from the local machine. To expose
the interface on all network interfaces, set `web_host:=0.0.0.0` and apply the
appropriate firewall and network-access restrictions.

The web server also exposes these endpoints:

| Method and path | Description |
| --- | --- |
| `GET /api/v1/state` | Return the latest configured joint state and feedback freshness. |
| `POST /api/v1/jog` | Queue a jog using JSON such as `{"direction": 1}` or `{"direction": -1}`. |

### Topic mode

Topic mode subscribes to an input jog topic and forwards valid commands to the
ELAC tester jog topic. It is the default mode:

```bash
ros2 launch vhit_robot_ui_gateway gateway.launch.py \
  control_mode:=topic
```

Publish a positive or negative command from another sourced terminal:

```bash
ros2 topic pub --once /vhit_robot_ui_gateway/jog \
  std_msgs/msg/Int8 "{data: 1}"
```

```bash
ros2 topic pub --once /vhit_robot_ui_gateway/jog \
  std_msgs/msg/Int8 "{data: -1}"
```

Only `-1` and `1` are accepted. Other values are rejected. The input and
output topics may be changed independently, which allows the gateway to sit
between an arbitrary command source and `vhit_elac_tester`.

## Parameters

The launch arguments below are passed to gateway parameters with the same
names.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `control_mode` | string | `topic` | Active command source. Must be `keyboard`, `web`, or `topic`. |
| `jog_output_topic` | string | `/elac_tester_node/jog` | Topic on which accepted signed jog commands are published. |
| `jog_input_topic` | string | `/vhit_robot_ui_gateway/jog` | Topic subscribed to in `topic` mode. |
| `joint_state_topic` | string | `/joint_states` | Joint-state feedback topic monitored in every mode. |
| `joint_name` | string | `elac_node` | Entry in `JointState.name` whose position and velocity are monitored. |
| `web_host` | string | `127.0.0.1` | HTTP bind address used in `web` mode. |
| `web_port` | integer | `8080` | HTTP port used in `web` mode. |

For example, to use custom command and feedback topics in topic mode:

```bash
ros2 launch vhit_robot_ui_gateway gateway.launch.py \
  control_mode:=topic \
  jog_input_topic:=/operator/jog \
  jog_output_topic:=/elac_tester_node/jog \
  joint_state_topic:=/robot/joint_states \
  joint_name:=elac_node
```

The node can also be run directly. Pass the same values as ROS parameters:

```bash
ros2 run vhit_robot_ui_gateway gateway_node --ros-args \
  -p control_mode:=keyboard \
  -p jog_output_topic:=/elac_tester_node/jog \
  -p joint_state_topic:=/joint_states \
  -p joint_name:=elac_node
```

When the node is run directly, the default `jog_input_topic` is the private
topic `~/jog`, which resolves to `/vhit_robot_ui_gateway/jog` with the default
node name.

## ROS Interfaces

| Direction | Topic | Type | Description |
| --- | --- | --- | --- |
| Published | `/elac_tester_node/jog` | `std_msgs/msg/Int8` | Accepted jog direction sent to the tester. |
| Subscribed | `/vhit_robot_ui_gateway/jog` | `std_msgs/msg/Int8` | Command input used only in `topic` mode. |
| Subscribed | `/joint_states` | `sensor_msgs/msg/JointState` | Position and velocity feedback used in every mode. |

The table shows the default topic names. Use the corresponding parameters to
override them.

## Verify Operation

Inspect the gateway output from another sourced terminal:

```bash
ros2 topic echo /elac_tester_node/jog
```

After fresh joint feedback has arrived, a command in the selected mode should
produce a message containing `-1` or `1`. The gateway logs accepted output and
rejected invalid or stale-feedback commands.

Useful checks:

```bash
ros2 node list
ros2 topic info /elac_tester_node/jog --verbose
ros2 topic echo /joint_states
ros2 param dump /vhit_robot_ui_gateway
```

## Tests

Run the package tests from the ROS workspace:

```bash
cd /home/<user>/vhit-robot-ui/ros
source /opt/ros/humble/setup.bash
colcon test --packages-select vhit_robot_ui_gateway
colcon test-result --verbose
```

## Troubleshooting

### Commands are rejected because feedback is stale

- Confirm that `joint_state_topic` is receiving messages.
- Confirm that every message contains `joint_name` and a finite position.
- Keep joint feedback publishing continuously; it is considered stale after
  one second.

### Arrow keys produce no commands in keyboard mode

- Run the gateway with `control_mode:=keyboard`.
- Run it directly in an interactive terminal rather than through redirected
  input or a background service.
- Confirm that the gateway is receiving fresh joint state feedback.

### The web page is unavailable

- Run the gateway with `control_mode:=web`.
- Confirm the URL uses the configured `web_host` and `web_port`.
- Use `web_host:=0.0.0.0` when access from another machine is required, and
  confirm that the host firewall permits the configured port.

### Topic commands do not reach the tester

- Run the gateway with `control_mode:=topic`.
- Confirm the publisher uses `jog_input_topic`, not `jog_output_topic`.
- Publish only `std_msgs/msg/Int8` values `-1` or `1`.
- Confirm that the gateway is receiving fresh joint state feedback.

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
