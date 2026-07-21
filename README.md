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
- Saves named waypoints from the current measured position and persists them
  across gateway restarts.

The gateway publishes only the jog direction. The target increment, trajectory
duration, and position limits are managed by `vhit_elac_tester`.

The UI is deliberately decoupled from the robot hardware implementation. It
communicates through ROS 2 topics and can therefore run by itself with synthetic
joint feedback, with a mocked Data Layer, or against a robot using the VHIT
ros2_control driver.

## Repository Layout

```text
vhit-robot-ui/
├── build-snap.sh
├── build-workspace.sh
├── configs/
│   └── package-assets/
├── scripts/
│   └── run-ui.sh
├── snap/
│   └── snapcraft.yaml
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

## Dependencies

### Direct requirements

- ROS 2 Humble
- Python 3.10
- Node.js 22.12 or newer and npm, to build the browser application
- `colcon`, `rosdep`, and Snapcraft when building the ctrlX snap
- `rclpy`
- `std_msgs`
- `sensor_msgs`
- `ament_index_python`
- An active subscriber for the output jog topic, normally
  `elac_tester_node` from the `vhit_elac_tester` package
- Joint state feedback containing the configured joint name

Keyboard mode also requires an interactive terminal. It cannot start when
standard input is redirected or no TTY is available.

### Robot and Data Layer repositories

The following repositories are not linked into the UI binary, but provide the
robot-side runtime used in a complete system:

- [VHIT Robot Driver](https://github.com/vhit-spa/VHIT-Robot-Driver) provides
  the `vhit_robot_driver/VhitRobotHardwareInterface` ros2_control plugin. It
  connects the robot control stack to the ctrlX Data Layer and EtherCAT
  realtime shared-memory areas.
- [VHIT Mock Data Layer](https://github.com/vhit-spa/vhit-mock-datalayer)
  provides a standalone Data Layer broker, provider, and shared-memory loopback
  for driver development without ctrlX CORE or EtherCAT hardware. The central
  implementation is
  [`MockDatalayerOwner`](https://github.com/vhit-spa/vhit-mock-datalayer/blob/main/include/vhit_mock_datalayer/mock_datalayer_owner.hpp).

The normal integration is:

```text
vhit-robot-ui  <-- ROS 2 topics -->  robot bringup / ros2_control
                                             |
                                      vhit_robot_driver
                                             |
                       ctrlX Data Layer or vhit_mock_datalayer
```

For local driver development, build and start the mock first:

```bash
git clone https://github.com/vhit-spa/vhit-mock-datalayer.git
cd vhit-mock-datalayer
cmake -S . -B build
cmake --build build
cd build
./vhit_mock_datalayer
```

The mock requires the ctrlX Data Layer runtime and headers, JsonCpp development
files, CMake, and a C++17 compiler. Configure the driver's hardware description
with `connection_string` set to `ipc://` when using it.

Build the driver in a separate terminal:

```bash
git clone https://github.com/vhit-spa/VHIT-Robot-Driver.git
cd VHIT-Robot-Driver
source /opt/ros/humble/setup.bash
rosdep install --ignore-src --from-paths src --rosdistro humble -y
colcon build --packages-select vhit_robot_driver
source install/setup.bash
```

The driver is a hardware plugin rather than a standalone executable. Start it
through a robot description and `controller_manager` bringup that selects
`vhit_robot_driver/VhitRobotHardwareInterface`.

## Local standalone operation

### Build the UI

The `ros/` directory is the colcon workspace root:

```bash
git clone https://github.com/vhit-spa/vhit-robot-ui.git
cd vhit-robot-ui
./build-workspace.sh
source ros/install/setup.bash
```

`build-workspace.sh` installs declared ROS dependencies, builds the Vite
frontend into the ROS package's `www` directory, and performs a merged colcon
build. Source `ros/install/setup.bash` in every new terminal that runs the
gateway.

Use a clean build before release packaging or after removing installed files:

```bash
CLEAN_BUILD=1 ./build-workspace.sh
```

### Run without a robot

The UI can be tested without the driver, Data Layer, or robot hardware. In one
sourced terminal, publish synthetic joint feedback:

```bash
ros2 topic pub --rate 10 /joint_states sensor_msgs/msg/JointState \
  "{name: ['elac_node'], position: [0.0], velocity: [0.0]}"
```

In a second sourced terminal, observe jog output:

```bash
ros2 topic echo /elac_tester_node/jog
```

In a third sourced terminal, start the web interface:

```bash
ros2 launch vhit_robot_ui_gateway gateway.launch.py \
  control_mode:=web \
  web_host:=127.0.0.1 \
  web_port:=8080
```

Open `http://127.0.0.1:8080`. Jog commands will appear in the topic echo; no
actuator will move. Waypoint execution publishes trajectories, but requires a
compatible trajectory controller to act on them.

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

#### Save and use waypoints

Waypoints are available in the browser interface while the gateway is running
in `web` mode:

1. Jog the actuator to the position you want to save and wait for the position
   display to update.
2. Enter an optional name in **Waypoint name**. If the field is empty, the UI
   assigns a name such as `Waypoint 1`.
3. Select **Teach current position**. The gateway saves the current measured
   joint position, not a commanded or pending target position.
4. Use the **Move** button next to a saved waypoint to move to it, or select
   **Play all** to visit every saved waypoint in list order.
5. Set **Move duration** to control the travel time for each move. For
   **Play all**, **Hold time** controls the pause at each waypoint.
6. Use the delete button next to a waypoint to remove it.

The gateway can save a waypoint only when it is receiving fresh feedback for
the configured `joint_name`. If teaching fails because feedback is unavailable
or stale, verify `/joint_states` and the `joint_name` parameter.

Saved waypoints persist across gateway restarts in
`~/.vhit_robot_ui/waypoints.json` by default. Set `waypoint_storage_file` when
launching the gateway to use a different file:

```bash
ros2 launch vhit_robot_ui_gateway gateway.launch.py \
  control_mode:=web \
  waypoint_storage_file:=/home/<user>/vhit-waypoints.json
```

The default host accepts connections only from the local machine. To expose
the interface on all network interfaces, set `web_host:=0.0.0.0` and apply the
appropriate firewall and network-access restrictions.

The web server also exposes these endpoints:

| Method and path | Description |
| --- | --- |
| `GET /api/v1/state` | Return the latest configured joint state and feedback freshness. |
| `POST /api/v1/jog` | Queue a jog using JSON such as `{"direction": 1}` or `{"direction": -1}`. |
| `GET /api/v1/waypoints` | List all saved waypoints. |
| `POST /api/v1/waypoints` | Save the current measured position using JSON such as `{"name": "Position A"}`. |
| `POST /api/v1/waypoints/<id>/execute` | Move to a saved waypoint; accepts an optional `duration` in seconds. |
| `DELETE /api/v1/waypoints/<id>` | Delete a saved waypoint. |
| `POST /api/v1/playback` | Play all waypoints using `move_duration` and `hold_time` values in seconds. |

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

## ctrlX CORE snap

### Runtime provider snaps

The UI snap consumes two content interfaces:

- [`ros2-base-humble`](https://github.com/rcruzoliver/ctrlx_ros2/tree/main/base-humble)
  supplies the ROS 2 Humble runtime through the `executables` content slot.
- [`moveit2-base-humble`](https://github.com/vhit-spa/ctrlx-automation-sdk-moveit2)
  supplies the MoveIt/ros2_control overlay, Cyclone DDS, and the proven
  `setup-env.sh` environment setup through the `moveit-runtime` content slot.

The UI does not currently call MoveIt APIs. Nevertheless, using the MoveIt base
snap is convenient because it already composes the ROS base and overlay
environments correctly and provides the Cyclone DDS runtime used by the other
VHIT robot snaps. Reusing that provider avoids duplicating and maintaining
manual `AMENT_PREFIX_PATH`, `PYTHONPATH`, and `LD_LIBRARY_PATH` setup in this
snap. The dependency can be replaced by a smaller dedicated runtime provider
later if reducing the deployed footprint becomes more important.

Build or obtain the provider snaps before installing the UI snap. Each provider
repository contains its own `build-snap.sh`:

```bash
git clone https://github.com/rcruzoliver/ctrlx_ros2.git
cd ctrlx_ros2/base-humble
./build-snap.sh
```

```bash
git clone https://github.com/vhit-spa/ctrlx-automation-sdk-moveit2.git
cd ctrlx-automation-sdk-moveit2
./build-snap.sh
```

### Build the UI snap

The build host needs ROS 2 Humble, Node.js/npm, rosdep, colcon, Snapcraft, and
the ctrlX build package sources used by the provider projects. Build an amd64
snap from the repository root with:

```bash
cd /home/<user>/vhit-robot-ui
./build-snap.sh
```

The script performs these operations:

1. Builds the Vite frontend.
2. Resolves ROS dependencies with rosdep.
3. Builds `vhit_robot_ui_gateway` into `ros/install`.
4. Cleans the previous Snapcraft state.
5. Packs `vhit-robot-ui` for amd64 in destructive mode.

For a clean ROS workspace build before packaging:

```bash
cd /home/<user>/vhit-robot-ui
CLEAN_BUILD=1 ./build-workspace.sh
snapcraft clean --destructive-mode
snapcraft pack --build-for=amd64 --verbosity=verbose --destructive-mode
```

The resulting file is created in the repository root, for example:

```text
vhit-robot-ui_0.0.1_amd64.snap
```

### Install and connect on ctrlX CORE

Install the snaps in dependency order. Replace the example filenames with the
versions produced by each repository:

```bash
sudo snap install --dangerous ./ros2-base-humble_<version>_amd64.snap
sudo snap install --dangerous ./moveit2-base-humble_<version>_amd64.snap
sudo snap install --dangerous ./vhit-robot-ui_0.0.1_amd64.snap
```

Connect the MoveIt provider to ROS base, then connect the UI to both providers:

```bash
sudo snap connect \
  moveit2-base-humble:ros-base \
  ros2-base-humble:ros-base

sudo snap connect \
  vhit-robot-ui:ros-base \
  ros2-base-humble:ros-base

sudo snap connect \
  vhit-robot-ui:moveit-runtime \
  moveit2-base-humble:moveit-base
```

Confirm the exact slot names and all connections on the target with:

```bash
snap connections moveit2-base-humble
snap connections vhit-robot-ui
```

The ctrlX package manager connects the UI's `package-assets` and `package-run`
slots to DeviceAdmin. `package-assets` registers the menu and reverse-proxy
configuration; `package-run` gives the reverse proxy access to the Unix socket
created at:

```text
$SNAP_DATA/package-run/vhit-robot-ui/web.sock
```

Check the service after installation:

```bash
snap services vhit-robot-ui
snap logs -n 100 vhit-robot-ui.ui
```

Open the application from the ctrlX CORE sidebar or overview entry. Opening it
through the menu supplies the ctrlX bearer token required by the protected jog,
waypoint, and playback API routes.

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
| `trajectory_topic` | string | `/vhit_elac_controller/joint_trajectory` | Joint trajectory topic used to execute saved waypoints. |
| `waypoint_storage_file` | string | `~/.vhit_robot_ui/waypoints.json` | JSON file used to persist saved waypoints. |
| `waypoint_move_duration` | float | `1.0` | Default duration in seconds for a move to a waypoint. |

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
