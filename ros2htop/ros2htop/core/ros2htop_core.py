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
The ROS2 lifecycle node.

This script initialises the lifecycle node that monitors and displays
real-time system and ROS2 metrics in a terminal interface.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""

import threading

from rcl_interfaces.msg import FloatingPointRange, ParameterDescriptor, SetParametersResult
from rclpy.lifecycle import LifecycleNode, LifecycleState, TransitionCallbackReturn
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from ros2htop.tasks.action_tasks import ActionTasks
from ros2htop.tasks.node_tasks import NodeTasks
from ros2htop.tasks.parameter_tasks import ParameterTasks
from ros2htop.tasks.service_tasks import ServiceTasks
from ros2htop.tasks.system_tasks import SystemTasks
from ros2htop.tasks.topic_tasks import TopicTasks
from ros2htop_interfaces.msg import RosHtopStats
from textual import log


QOS_PROFILE = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1
)


class Ros2HtopCore(LifecycleNode):
    """
    Core class for the ros2htop ROS 2 node.

    Handles the lifecycle of the node and is responsible
    for monitoring and displaying system and ROS 2 metrics.
    """

    def __init__(self):
        super().__init__('ros2htop_node')
        self.cancel = False
        self._lock_nodetab = threading.Lock()
        self._lock_topictab = threading.Lock()
        self._lock_servicetab = threading.Lock()
        self._lock_paramtab = threading.Lock()
        self._lock_actiontab = threading.Lock()
        self.timer = None
        self.publisher = None

        self.tui_metrics_nodetab = {'sys': {}, 'node': {}}
        self.tui_metrics_topictab = {'topic': {}}
        self.tui_metrics_servicetab = {'service': {}}
        self.tui_metrics_paramtab = {'param': {}}
        self.tui_metrics_actiontab = {'action': {}}

        # Declare the tasks & timers :)
        self.system_task = None
        self.node_task = None
        self.topic_task = None
        self.service_task = None
        self.param_task = None
        self.action_task = None

        self.node_tab_timer = None
        self.topic_tab_timer = None
        self.service_tab_timer = None
        self.param_tab_timer = None

        self.declare_parameter(name='update_rate',
                               value=10.0,
                               descriptor=ParameterDescriptor(
                                   description='Set the update rate in seconds',
                                   floating_point_range=[FloatingPointRange(from_value=10.0,
                                                                            to_value=120.0,
                                                                            step=5.0)]))
        self.update_rate = float(self.get_parameter('update_rate').value)
        self.add_on_set_parameters_callback(self._on_parameter_change)
        log('Ros2HtopCore node initialized, update rate is %s sec.', self.update_rate)

    def _on_parameter_change(self, params) -> SetParametersResult:
        """Set the update rate on the fly."""
        try:
            for param in params:
                if param.name == 'update_rate':
                    self.update_rate = float(param.value)
                    if self.timer:
                        self.timer.cancel()
                    self.timer = self.create_timer(timer_period_sec=self.update_rate,
                                                   callback=self._update_metrics)
        except Exception as err:
            log('Error updating parameters: %s', err)
            return SetParametersResult(successful=False)
        return SetParametersResult(successful=True)

    def update_node_tab(self):
        """Update the node tui tab."""
        gpu_map = {}
        if self.system_task:
            self.system_task.update_metrics()
            gpu_map = self.system_task.get_gpu_map()
        if self.node_task:
            self.node_task.update_metrics(node=self, gpu_map=gpu_map)

    def update_topic_tab(self):
        """Update the topic tui tab."""
        if self.topic_task:
            self.topic_task.update_metrics(node=self)

    def update_service_tab(self):
        """Update the service tui tab."""
        if self.service_task:
            self.service_task.update_metrics(node=self)

    def update_param_tab(self):
        """Update the parameter tui tab."""
        if self.param_task:
            self.param_task.update_metrics(node=self)

    def fetch_metrics(self, active_tab: str = 'Nodes'):
        """Fetch the latest metrics for the TUI."""
        if active_tab == 'Nodes':
            with self._lock_nodetab:
                return self.tui_metrics_nodetab.copy()
        elif active_tab == 'Topics':
            with self._lock_topictab:
                return self.tui_metrics_topictab.copy()
        elif active_tab == 'Services':
            with self._lock_servicetab:
                return self.tui_metrics_servicetab.copy()
        elif active_tab == 'Parameters':
            with self._lock_paramtab:
                return self.tui_metrics_paramtab.copy()
        elif active_tab == 'Actions':
            with self._lock_actiontab:
                return self.tui_metrics_actiontab.copy()
        return {}

    def _update_metrics(self) -> None:
        """Collect system and ROS2 metrics and publish them."""
        try:
            sys_metrics = self.system_task.get_metrics() if self.system_task else {}
            node_metrics = self.node_task.get_metrics() if self.node_task else {}
            topic_metrics = self.topic_task.get_metrics() if self.topic_task else {}
            service_metrics = self.service_task.get_metrics() if self.service_task else {}
            parameter_metrics = self.param_task.get_metrics() if self.param_task else {}
            action_metrics = self.action_task.get_metrics() if self.action_task else {}

            # Stats
            node_num = len(node_metrics) if node_metrics else 0
            topic_num = len(topic_metrics) if topic_metrics else 0
            service_num = len(service_metrics) if service_metrics else 0
            param_num = len(parameter_metrics) if parameter_metrics else 0
            action_num = len(action_metrics) if action_metrics else 0
            action_count_s = 0
            action_count_c = 0
            hidden_count = 0
            total_hz = 0.0
            total_bytes_per_sec = 0.0
            for _, data in topic_metrics.items():
                if data.get('hidden'):
                    hidden_count += 1
                hz = data.get('hz', 0) or 0
                msg_size = data.get('msg_size', 0) or 0
                if hz > 0:
                    total_hz += hz
                    if msg_size > 0:
                        total_bytes_per_sec += hz * msg_size

            for _, data in action_metrics.items():
                action_count_s += data.get('servers', 0) or 0
                action_count_c += data.get('clients', 0) or 0

            with self._lock_nodetab:
                self.tui_metrics_nodetab['sys'] = sys_metrics
                self.tui_metrics_nodetab['node'] = node_metrics
                self.tui_metrics_nodetab['sys']['node#'] = node_num
                self.tui_metrics_nodetab['sys']['topic#'] = topic_num
                self.tui_metrics_nodetab['sys']['service#'] = service_num
                self.tui_metrics_nodetab['sys']['parameter#'] = param_num
                self.tui_metrics_nodetab['sys']['action#'] = action_num
                self.tui_metrics_nodetab['sys']['action_s#'] = action_count_s
                self.tui_metrics_nodetab['sys']['action_c#'] = action_count_c
                self.tui_metrics_nodetab['sys']['hidden#'] = hidden_count
                self.tui_metrics_nodetab['sys']['total_hz'] = total_hz
                self.tui_metrics_nodetab['sys']['total_bytes'] = total_bytes_per_sec
            with self._lock_topictab:
                self.tui_metrics_topictab['topic'] = topic_metrics
            with self._lock_servicetab:
                self.tui_metrics_servicetab['service'] = service_metrics
            with self._lock_paramtab:
                self.tui_metrics_paramtab['param'] = parameter_metrics
            with self._lock_actiontab:
                self.tui_metrics_actiontab['action'] = action_metrics

            msg = RosHtopStats()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'ros2htop_frame'
            msg.num_nodes = node_num
            msg.num_topics = topic_num
            msg.num_services = service_num
            msg.num_parameters = param_num
            msg.num_actions = action_num
            if self.publisher:
                self.publisher.publish(msg=msg)
        except Exception as err:
            log('Error updating metrics: %s', err)

    def on_configure(self, state: LifecycleState) -> TransitionCallbackReturn:
        """Configure the node."""
        log('Configuring Ros2HtopCore...')
        self.publisher = self.create_lifecycle_publisher(msg_type=RosHtopStats,
                                                         topic='~/stats',
                                                         qos_profile=QOS_PROFILE)
        self.system_task = SystemTasks()
        self.node_task = NodeTasks()
        self.topic_task = TopicTasks()
        self.service_task = ServiceTasks()
        self.param_task = ParameterTasks()
        self.action_task = ActionTasks()
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: LifecycleState) -> TransitionCallbackReturn:
        """Activate the node."""
        log('Activating Ros2HtopCore...')
        if self.timer:
            self.timer.cancel()
        if self.node_tab_timer:
            self.node_tab_timer.cancel()
        if self.topic_tab_timer:
            self.topic_tab_timer.cancel()
        if self.service_tab_timer:
            self.service_tab_timer.cancel()
        if self.param_tab_timer:
            self.param_tab_timer.cancel()
        self.timer = self.create_timer(timer_period_sec=self.update_rate,
                                       callback=self._update_metrics)
        self.node_tab_timer = self.create_timer(timer_period_sec=self.update_rate,
                                                callback=self.update_node_tab)
        self.topic_tab_timer = self.create_timer(timer_period_sec=2*self.update_rate,
                                                 callback=self.update_topic_tab)
        self.service_tab_timer = self.create_timer(timer_period_sec=self.update_rate,
                                                   callback=self.update_service_tab)
        self.param_tab_timer = self.create_timer(timer_period_sec=self.update_rate,
                                                 callback=self.update_param_tab)
        return super().on_activate(state)

    def on_deactivate(self, state):
        """Deactivate the node."""
        log('Deactivating Ros2HtopCore...')
        if self.timer:
            self.timer.cancel()
        if self.node_tab_timer:
            self.node_tab_timer.cancel()
        if self.topic_tab_timer:
            self.topic_tab_timer.cancel()
        if self.service_tab_timer:
            self.service_tab_timer.cancel()
        if self.param_tab_timer:
            self.param_tab_timer.cancel()
        return super().on_deactivate(state)

    def on_cleanup(self, state):
        """Clean up the node."""
        log('Cleaning up Ros2HtopCore...')
        self.system_task = None
        self.node_task = None
        self.service_task = None
        self.publisher = None
        if self.topic_task is not None:
            self.topic_task.stop()
            self.topic_task = None
        if self.param_task is not None:
            self.param_task.stop()
            self.param_task = None
        if self.action_task is not None:
            self.action_task.stop()
            self.action_task = None
        return super().on_cleanup(state)

    def on_shutdown(self, state):
        """Shutdown the node."""
        log('Shutting down Ros2HtopCore...')
        self.cancel = True
        self.publisher = None
        self.system_task = None
        self.node_task = None
        self.service_task = None
        if self.topic_task is not None:
            self.topic_task.stop()
            self.topic_task = None
        if self.param_task is not None:
            self.param_task.stop()
            self.param_task = None
        if self.action_task is not None:
            self.action_task.stop()
            self.action_task = None
        return super().on_shutdown(state)
