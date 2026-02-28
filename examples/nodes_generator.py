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
Swarm Generator example.

Spin 50 nodes with 2 publishers each.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""

import random
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.action import ActionServer
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from std_msgs.msg import String
from std_srvs.srv import Trigger
from example_interfaces.action import Fibonacci


SMALL_MSG = "x" * 20          # ~20 bytes
LARGE_MSG = "y" * 2048        # ~2 kB
# https://docs.ros.org/en/rolling/Concepts/Intermediate/About-Quality-of-Service-Settings.html
QOS_PROFILE = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,      # RELIABLE or BEST_EFFORT
    durability=DurabilityPolicy.VOLATILE,           # VOLATILE or TRANSIENT_LOCAL
    history=HistoryPolicy.KEEP_LAST,                # KEEP_ALL or KEEP_LAST
    depth=1                                         # Used only with KEEP_LAST
)
QOS_PROFILE2 = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,         # RELIABLE or BEST_EFFORT
    durability=DurabilityPolicy.VOLATILE,           # VOLATILE or TRANSIENT_LOCAL
    history=HistoryPolicy.KEEP_LAST,                # KEEP_ALL or KEEP_LAST
    depth=1                                         # Used only with KEEP_LAST
)


class FakeNode(Node):
    """Handle normal nodes."""
    def __init__(self, node_id: int = 1):
        super().__init__(node_name=f"node_{node_id}")

        # Declare params
        self.declare_parameter("param_a", "value_a")
        self.declare_parameter("param_rand", random.randint(0, node_id))

        # Publishers
        self.pub_small = self.create_publisher(msg_type=String,
                                               topic="topic1",
                                               qos_profile=QOS_PROFILE)
        self.pub_large = self.create_publisher(msg_type=String,
                                               topic="topic2",
                                               qos_profile=QOS_PROFILE2)

        # Services
        self.srv1 = self.create_service(srv_type=Trigger,
                                        srv_name="service1",
                                        callback=self.srv_cb,
                                        qos_profile=QOS_PROFILE)

        # Action
        self.action_server = ActionServer(node=self,
                                          action_type=Fibonacci,
                                          action_name="fibonacci",
                                          execute_callback=self.execute_cb)

        # Timers
        self.create_timer(1.0, self.publish_small)     # 1 Hz
        self.create_timer(0.1, self.publish_large)     # 10 Hz
        self.get_logger().info(f"Node: {node_id} created!")

    def publish_small(self):
        """Publish small msg."""
        msg = String()
        msg.data = SMALL_MSG
        self.pub_small.publish(msg)

    def publish_large(self):
        """Publish large msg."""
        msg = String()
        msg.data = LARGE_MSG
        self.pub_large.publish(msg)

    def srv_cb(self, request, response):
        """Service callback."""
        response.success = True
        response.message = "ok"
        return response

    async def execute_cb(self, goal_handle):
        """Action callback."""
        result = Fibonacci.Result()
        result.sequence = [0, 1, 1, 2, 3]
        goal_handle.succeed()
        return result


def main():
    """Entry point."""
    rclpy.init()

    nodes = []
    for i in range(50):
        nodes.append(FakeNode(node_id=i))

    executor = MultiThreadedExecutor(num_threads=6)

    for node in nodes:
        executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        for node in nodes:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
