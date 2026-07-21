#!/bin/bash
set -e

export MOVEIT_RUNTIME=$SNAP/moveit-runtime

source $MOVEIT_RUNTIME/usr/bin/setup-env.sh

source $SNAP/local_setup.bash

exec "$ROS_BASE/opt/ros/humble/bin/ros2" run \
  vhit_robot_ui_gateway \
  gateway_node \
  --ros-args \
  -p control_mode:=web \
  -p waypoint_storage_file:="$SNAP_COMMON/waypoints.json"