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
Service Statistics.

Collects and processes service metrics.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""


import threading
from rclpy.lifecycle import LifecycleNode
from textual import log


class ServiceTasks:
    """Collect and process service metrics."""

    def __init__(self):
        self._lock = threading.Lock()
        self._metrics = {}

    def get_metrics(self):
        """Return the latest service metrics."""
        with self._lock:
            return self._metrics.copy()

    def update_metrics(self, node: LifecycleNode) -> None:
        """Collect and process service metrics."""
        try:
            if not node:
                return
            srv_list = node.get_service_names_and_types()
            new_dict = {}
            for name, srv_types in srv_list:
                srv_type = srv_types[0] if srv_types else "unknown"
                new_dict[name] = {
                    'types': srv_type
                }
            with self._lock:
                self._metrics = new_dict.copy()
        except Exception as err:
            log('Error getting service state: %s', err)
