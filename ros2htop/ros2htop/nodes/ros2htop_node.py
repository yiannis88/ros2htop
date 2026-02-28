#!/usr/bin/env python3
# Copyright (c) 2026 yiannis88.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Entry point for the ros2htop ROS 2 node.

This script initialises the ROS2 node, responsible for monitoring
and displaying real-time system and ROS2 metrics in a terminal interface.

The param and launch files have been removed as they are interfering with
the TUI and couldn't figure out a way to completely disable the logs coming
from them. The recommended way to run the node is to use the ros2 run command.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""

__author__ = "yiannis88"
__email__ = "selinis.g@gmail.com"
__date__ = "2026"
__version__ = "0.0.1"
__license__ = "MIT"

import sys
import threading
import time
import rclpy
from textual import log

from ros2htop.core.ros2htop_core import Ros2HtopCore
from ros2htop.ui.textual_app import SystemTUI


def ros_spin(node):
    """Spin ROS 2 node in a background thread."""
    executor = rclpy.executors.MultiThreadedExecutor(num_threads=10)
    executor.add_node(node)
    try:
        executor.spin()
    except Exception as err:
        log('Failed to shutdown ROS 2: %s', err)
    finally:
        if node:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        log("ROS 2 node shutdown successfully.")


def main(args=None):
    """Entry point for the ros2htop ROS 2 node."""
    try:
        rclpy.init(args=args)
        node = Ros2HtopCore()
        node.trigger_configure()
        time.sleep(1.0)
        node.trigger_activate()

        ros_thread = threading.Thread(target=ros_spin, args=(node,), daemon=True)
        ros_thread.start()
        time.sleep(2.0)
        sys.stdout.flush()
        sys.stderr.flush()
        app = SystemTUI(ros_node=node)
        app.run()
    except Exception as err:
        log('Failed to initialize ROS 2: %s', err)
    finally:
        if 'node' in locals() and node:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        log('ROS 2 node shutdown successfully.')


if __name__ == "__main__":
    main()
