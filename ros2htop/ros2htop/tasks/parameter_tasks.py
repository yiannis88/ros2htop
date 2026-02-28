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
Param Statistics.

Collects and processes parameter metrics.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""

import threading
import time
from typing import Dict, Any
from rclpy.lifecycle import LifecycleNode
from rcl_interfaces.srv import ListParameters, GetParameterTypes
from textual import log


class ParameterTasks:
    """Collect and process parameter metrics."""

    CHECK_INTERVAL = 0.5
    SERVICE_TIMEOUT = 2.0
    MEASURE_LIMIT = 10

    def __init__(self):
        self._lock = threading.Lock()
        self._lock_list = threading.Lock()
        self._lock_type = threading.Lock()

        self._running = True
        self._node: LifecycleNode = None
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._list_state: Dict[str, Dict[str, Any]] = {}
        self._type_state: Dict[str, Dict[str, Any]] = {}

        self._list_thread = threading.Thread(target=self._list_worker, daemon=False)
        self._list_thread.start()
        self._type_thread = threading.Thread(target=self._type_worker, daemon=False)
        self._type_thread.start()

    def stop(self):
        """Stop the thread."""
        self._running = False
        self._list_thread.join()
        self._type_thread.join()

    def get_metrics(self):
        """Return the latest parameter metrics."""
        with self._lock:
            return self._metrics.copy()

    def _list_res_cb(self, future, fqn):
        """SRV list param cb."""
        try:
            result = future.result()
            names = result.result.names
            with self._lock_list:
                self._list_state.pop(fqn, None)
                self._list_state[fqn] = {
                    "names": names,
                    "timestamp": time.time()
                }

            with self._lock:
                if fqn in self._metrics:
                    self._metrics[fqn]["names"] = names
        except Exception:
            with self._lock_list:
                self._list_state.pop(fqn, None)

    def _list_worker(self):
        """Background worker for the list param."""
        while self._running:
            with self._lock_list:
                for fqn in list(self._list_state.keys()):
                    state = self._list_state[fqn]
                    if "future" in state and state["future"].done():
                        self._list_state.pop(fqn)
                    elif time.time() - state.get("timestamp", 0) > self.SERVICE_TIMEOUT:
                        self._list_state.pop(fqn)

            with self._lock_list:
                if len(self._list_state) >= self.MEASURE_LIMIT:
                    time.sleep(self.CHECK_INTERVAL)
                    continue

            with self._lock:
                for fqn, data in self._metrics.items():
                    if data["names"] is not None:
                        continue
                    with self._lock_list:
                        if fqn in self._list_state:
                            continue

                    try:
                        client = self._node.create_client(ListParameters, data["list_srv"])
                        req = ListParameters.Request()
                        req.prefixes = []
                        req.depth = 10

                        future = client.call_async(req)
                        future.add_done_callback(lambda fut, fqn=fqn: self._list_res_cb(fut, fqn))

                        with self._lock_list:
                            self._list_state[fqn] = {"future": future, "timestamp": time.time()}
                    except Exception:
                        continue

            time.sleep(self.CHECK_INTERVAL)

    def _type_res_cb(self, future, fqn):
        """SRV get param type cb."""
        try:
            result = future.result()
            types = result.types

            with self._lock_type:
                self._type_state.pop(fqn, None)
                self._type_state[fqn] = {"types": types, "timestamp": time.time()}

            with self._lock:
                if fqn in self._metrics and "names" in self._metrics[fqn]:
                    names = self._metrics[fqn]["names"]
                    self._metrics[fqn]["params"] = {n: {"type": t} for n, t in zip(names, types)}
                    self._metrics[fqn]["last_update"] = time.time()

        except Exception:
            with self._lock_type:
                self._type_state.pop(fqn, None)

    def _type_worker(self):
        """Continuously fetch parameter types for nodes that have names but missing types."""
        while self._running:
            with self._lock_type:
                for fqn in list(self._type_state.keys()):
                    state = self._type_state[fqn]
                    if "future" in state and state["future"].done():
                        self._type_state.pop(fqn)
                    elif time.time() - state.get("timestamp", 0) > self.SERVICE_TIMEOUT:
                        self._type_state.pop(fqn)

            with self._lock_type:
                if len(self._type_state) >= self.MEASURE_LIMIT:
                    time.sleep(self.CHECK_INTERVAL)
                    continue

            with self._lock:
                for fqn, data in self._metrics.items():
                    if data.get("names") is None or data.get("params") is not None:
                        continue

                    try:
                        client = self._node.create_client(GetParameterTypes, data["type_srv"])
                        req = GetParameterTypes.Request()
                        req.names = data["names"]

                        future = client.call_async(req)
                        future.add_done_callback(lambda fut, fqn=fqn: self._type_res_cb(fut, fqn))

                        with self._lock_type:
                            self._type_state[fqn] = {"future": future, "timestamp": time.time()}
                    except Exception:
                        continue

            time.sleep(self.CHECK_INTERVAL)

    def update_metrics(self, node: LifecycleNode) -> None:
        """Collect and process param metrics."""
        try:
            if not node:
                return
            if not self._node:
                self._node = node
            services = dict(node.get_service_names_and_types())
            nodes = node.get_node_names_and_namespaces()
            new_dict = {}

            for node_name, namespace in nodes:
                fqn_ = f"/{node_name}" if namespace == "/" else f"{namespace}/{node_name}"
                list_srv = f"{fqn_}/list_parameters"
                type_srv = f"{fqn_}/get_parameter_types"

                if not all(srv in services for srv in (list_srv, type_srv)):
                    continue

                with self._lock:
                    if fqn_ in self._metrics:
                        continue

                new_dict[fqn_] = {
                    "list_srv": list_srv,
                    "type_srv": type_srv,
                    "params": None,
                    "names": None,
                    "last_update": None
                }

            if new_dict:
                with self._lock:
                    self._metrics.update(new_dict)
        except Exception as err:
            log('Error getting param state: %s', err)
