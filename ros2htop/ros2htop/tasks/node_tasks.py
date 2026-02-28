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
Node Statistics.

Collects and processes node metrics such as CPU usage, memory usage,
disk usage, etc.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""

import threading
import time
from functools import partial
from typing import Dict, Union
import psutil
from rclpy.task import Future
from rclpy.lifecycle import LifecycleNode
from lifecycle_msgs.srv import GetState
from textual import log


class NodeTasks:
    """Collect and process node stats."""

    CHECK_INTERVAL = 1.0
    BATCH_SIZE = 10

    def __init__(self):
        self._lock = threading.Lock()
        self._lock_srv = threading.Lock()
        self._metrics = {}
        self._services = {}

        self._running = True
        self._node: LifecycleNode = None

        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the background thread."""
        self._running = False
        self._node = None
        self._thread.join()

    def get_metrics(self):
        """Return the latest node metrics."""
        with self._lock:
            return self._metrics.copy()

    def service_callback(self, future: Future, node_name: str) -> None:
        """Handle the node state service callback."""
        try:
            result = future.result()
            if result:
                with self._lock:
                    self._metrics[node_name]['lifecycle_state'] = result.current_state.label
        except Exception as err:
            log('Error getting node state: %s', err)

    def _worker(self) -> None:
        """Get the node state in the background."""
        while self._running:
            with self._lock:
                metrics_dict = self._metrics.copy()

            if metrics_dict is None or len(metrics_dict) == 0:
                time.sleep(NodeTasks.CHECK_INTERVAL)
                continue

            # Check if there's any service cb not triggered yet
            now = time.time()
            continue_flag = False
            unavailable_slots = NodeTasks.BATCH_SIZE
            with self._lock_srv:
                for srv in list(self._services.keys()):
                    if (
                        self._services[srv]['future'].done()
                        or now - self._services[srv]['started'] > NodeTasks.CHECK_INTERVAL
                    ):
                        try:
                            self._node.destroy_client(self._services[srv]['client'])
                        except Exception:
                            pass
                        del self._services[srv]
                unavailable_slots = len(self._services)
                if unavailable_slots >= NodeTasks.BATCH_SIZE:
                    continue_flag = True

            if continue_flag:
                time.sleep(NodeTasks.CHECK_INTERVAL)
                continue

            sorted_nodes = sorted(
                metrics_dict.items(),
                key=lambda item: item[1].get('last_updated') or 0
            )
            available_slots = NodeTasks.BATCH_SIZE - unavailable_slots
            batch_nodes = sorted_nodes[:available_slots]

            for name, data in batch_nodes:
                try:
                    now_started = time.time()
                    service_name = f"{data['ns']}/{name}/get_state".replace('//', '/')
                    client = self._node.create_client(GetState, service_name)
                    req = GetState.Request()
                    future = client.call_async(req)
                    future.add_done_callback(partial(self.service_callback, node_name=name))
                    with self._lock:
                        self._metrics[name]['last_updated'] = now_started
                    with self._lock_srv:
                        self._services[service_name] = {
                            'client': client,
                            'future': future,
                            'started': now_started,
                        }
                except Exception:
                    continue

            time.sleep(NodeTasks.CHECK_INTERVAL)

    def update_metrics(self, node: LifecycleNode, gpu_map: dict) -> None:
        """Collect and process node metrics."""
        node_names: Dict[str, Dict[str, Union[int, float, str, None]]] = {}
        if node is None:
            return
        if self._node is None:
            self._node = node

        def find_node_proc(mem_total: int = 0) -> None:
            """Find the PID of the ROS node."""
            if not node_names:
                return
            for process in psutil.process_iter(['pid',
                                                'cmdline',
                                                'name',
                                                'create_time',
                                                'memory_info']):
                try:
                    cmdline_list = process.info['cmdline'] or []
                    if not cmdline_list:
                        continue

                    cmdline = " ".join(cmdline_list)
                    for name, value in node_names.items():
                        if f"__node:={name}" in cmdline or name in cmdline:
                            pid = process.pid
                            gpu = gpu_map.get(pid) if gpu_map else None
                            proc_mem = process.memory_info().rss
                            value['pid'] = pid
                            value['uptime'] = (time.time() - process.create_time()) / 60.0
                            value['mem'] = proc_mem / (1024 * 1024)
                            value['mem_pct'] = max(min((proc_mem / mem_total) * 100.0, 100.0), 0.0)
                            value['cpu'] = process.cpu_percent(interval=None)
                            value['core'] = process.cpu_num()
                            if gpu:
                                value['gpu_mem_mb'] = gpu.get('gpu_mem_mb')
                                value['gpu_mem_pct'] = gpu.get('gpu_mem_pct')
                                value['gpu_index'] = gpu.get('gpu_index')
                                value['gpu_load'] = gpu.get('gpu_load')
                except Exception:
                    continue

        try:
            node_list = node.get_node_names_and_namespaces()
            mem_total = psutil.virtual_memory().total
            for name, ns in node_list:
                node_names[name] = {
                    'ns': ns,
                    'pid': -1,
                    'uptime': -1,
                    'mem': -1,
                    'mem_pct': 0,
                    'core': -1,
                    'cpu': -1,
                    'gpu_mem_mb': -1,
                    'gpu_mem_pct': 0,
                    'gpu_index': -1,
                    'gpu_load': 0,
                    'last_updated': None,
                    'lifecycle_state': 'unknown'
                }

            find_node_proc(mem_total=mem_total)
            with self._lock:
                for existing_node in list(self._metrics.keys()):
                    if existing_node not in node_names:
                        del self._metrics[existing_node]
                for name, data in node_names.items():
                    if name in self._metrics:
                        self._metrics[name]['ns'] = data['ns']
                        self._metrics[name]['pid'] = data['pid']
                        self._metrics[name]['uptime'] = data['uptime']
                        self._metrics[name]['mem'] = data['mem']
                        self._metrics[name]['mem_pct'] = data['mem_pct']
                        self._metrics[name]['core'] = data['core']
                        self._metrics[name]['cpu'] = data['cpu']
                        self._metrics[name]['gpu_mem_mb'] = data['gpu_mem_mb']
                        self._metrics[name]['gpu_mem_pct'] = data['gpu_mem_pct']
                        self._metrics[name]['gpu_index'] = data['gpu_index']
                        self._metrics[name]['gpu_load'] = data['gpu_load']
                    else:
                        self._metrics[name] = data
        except Exception as err:
            log('Error collecting node metrics: %s', err)
