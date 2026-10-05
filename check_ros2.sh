#!/bin/bash
source /opt/ros/jazzy/setup.bash
python3 -c "import rclpy; print('rclpy OK')"
ros2 --version 2>&1 || true
python3 -c "import pygame; print('pygame OK', pygame.version.ver)"
