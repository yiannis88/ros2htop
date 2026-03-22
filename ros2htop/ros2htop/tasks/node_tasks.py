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

from functools import partial
import threading
import time
from typing import Dict, Union

from lifecycle_msgs.srv import GetState
import psutil
from rclpy.lifecycle import LifecycleNode
from rclpy.task import Future
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
                    if node_name in self._metrics:
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

            for name, _ in batch_nodes:
                try:
                    now_started = time.time()
                    service_name = f"{name}/get_state".replace('//', '/')
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

            def extract_ros_node_name(cmdline_list):
                """Extract ros name."""
                for i, arg in enumerate(cmdline_list):
                    if '__node:=' in arg:
                        return arg.split(':=')[1]
                    if arg == '-r' and i + 1 < len(cmdline_list):
                        next_arg = cmdline_list[i + 1]
                        if '__node:=' in next_arg:
                            return next_arg.split(':=')[1]
                return None

            def extract_ros_namespace(cmdline_list):
                for i, arg in enumerate(cmdline_list):
                    if '__ns:=' in arg:
                        return arg.split(':=')[1]
                    if arg == '-r' and i + 1 < len(cmdline_list):
                        nxt = cmdline_list[i + 1]
                        if '__ns:=' in nxt:
                            return nxt.split(':=')[1]
                return '/'

            def is_ros2_wrapper(cmdline_list):
                """Filter out ros2 stuff."""
                return (
                    len(cmdline_list) >= 2
                    and 'ros2' in cmdline_list[0]
                    and ('run' in cmdline_list or 'launch' in cmdline_list)
                )

            candidates = {key: [] for key in node_names}
            for process in psutil.process_iter(['pid',
                                                'cmdline',
                                                'name',
                                                'create_time',
                                                'memory_info']):
                try:
                    cmdline_list = process.info['cmdline'] or []
                    if not cmdline_list:
                        continue
                    if is_ros2_wrapper(cmdline_list):
                        continue
                    ros_node = extract_ros_node_name(cmdline_list)
                    ros_ns = extract_ros_namespace(cmdline_list)
                    
                    for name, value in node_names.items():
                        match = False
                        if ros_node:
                            if ros_node == value['node'] and ros_ns == value['ns']:
                                match = True
                        else:
                            name_ = value['node']
                            exe = process.info['name'] or ''
                            if ros_ns == value['ns'] and (exe == name_ or exe == f'{name_}_node'):
                                match = True
                        if not match:
                            continue
                        candidates[name].append(process)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            for name, procs in candidates.items():
                if not procs:
                    continue
                proc = max(procs, key=lambda p: p.info['create_time'])
                try:
                    pid = proc.pid
                    value = node_names[name]

                    gpu = gpu_map.get(pid) if gpu_map else None
                    proc_mem = proc.memory_info().rss

                    value['pid'] = pid
                    value['uptime'] = (time.time() - proc.create_time()) / 60.0
                    value['mem'] = proc_mem / (1024 * 1024)
                    value['mem_pct'] = max(min((proc_mem / mem_total) * 100.0, 100.0), 0.0)
                    value['cpu'] = proc.cpu_percent(interval=None)
                    value['core'] = proc.cpu_num()

                    if gpu:
                        value['gpu_mem_mb'] = gpu.get('gpu_mem_mb')
                        value['gpu_mem_pct'] = gpu.get('gpu_mem_pct')
                        value['gpu_index'] = gpu.get('gpu_index')
                        value['gpu_load'] = gpu.get('gpu_load')
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        try:
            node_list = node.get_node_names_and_namespaces()
            mem_total = psutil.virtual_memory().total
            for name, ns in node_list:
                if ns == '/':
                    fq_name = f'/{name}'
                else:
                    fq_name = f'{ns}/{name}'
                node_names[fq_name] = {
                    'node': name,
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
