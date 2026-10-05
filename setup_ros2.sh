#!/bin/bash
set -e
apt-get install -y curl
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $UBUNTU_CODENAME main" | tee /etc/apt/sources.list.d/ros2.list
apt-get update -y
apt-get install -y ros-jazzy-ros-base python3-colcon-common-extensions
