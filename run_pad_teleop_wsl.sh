#!/bin/bash
export SDL_VIDEODRIVER=dummy
source /opt/ros/jazzy/setup.bash
cp /mnt/c/Users/mando/OneDrive/Desktop/turtleclaude4/pad_teleop.py /root/pad_teleop.py
python3 /root/pad_teleop.py
