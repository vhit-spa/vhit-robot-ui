#!/bin/bash
set -eo pipefail

repository_dir="$(
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
  pwd
)"

ros_workspace="$repository_dir/ros"
package_dir="$ros_workspace/src/vhit_robot_ui_gateway"
frontend_dir="$package_dir/frontend"

echo "Building frontend"
npm --prefix "$frontend_dir" ci
npm --prefix "$frontend_dir" run build

# Some ROS setup scripts are not guaranteed to work with nounset enabled.
set +u
source /opt/ros/humble/setup.bash
set -u

echo "Installing ROS dependencies"
rosdep install \
  --ignore-src \
  --from-paths "$ros_workspace/src" \
  --rosdistro humble \
  -y

if [[ "${CLEAN_BUILD:-0}" == "1" ]]; then
  echo "Removing previous workspace build output"
  rm -rf -- \
    "$ros_workspace/build" \
    "$ros_workspace/install" \
    "$ros_workspace/log"
fi

echo "Building ROS package"
cd "$ros_workspace"

colcon build \
  --merge-install \
  --packages-select vhit_robot_ui_gateway

echo "Workspace built successfully"
echo "Source: $ros_workspace/install/setup.bash"