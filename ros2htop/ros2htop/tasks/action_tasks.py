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
Action Statistics.

Collects and processes action metrics.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""

import re
import subprocess
import threading
import time


class ActionTasks:
    """Collect and process action metrics."""

    CHECK_INTERVAL = 2.0

    def __init__(self):
        self._lock = threading.Lock()
        self._lock_ac = threading.Lock()
        self._metrics = {}
        self._ros_actions_list = {}
        self._running = True

        self._thread = threading.Thread(target=self._list_worker, daemon=False)
        self._inthread = threading.Thread(target=self._info_worker, daemon=False)
        self._thread.start()
        self._inthread.start()

    def stop(self):
        """Stop the thread."""
        self._running = False
        self._thread.join()
        self._inthread.join()

    def get_metrics(self):
        """Return the latest action metrics."""
        with self._lock:
            return self._metrics.copy()

    def _list_worker(self):
        """Background worker for the action metrics."""
        while self._running:
            list_output = self.get_list_actions()
            if list_output is None:
                time.sleep(self.CHECK_INTERVAL)
                continue

            lines = [line.strip() for line in list_output.splitlines() if line.strip()]
            if not lines:
                time.sleep(self.CHECK_INTERVAL)
                continue

            for line in lines:
                match_ = re.match(r'(.+?)\s*\[(.+?)\]', line)
                if not match_:
                    continue
                action_name, types_str = match_.groups()
                action_type = types_str.split(',')[0].strip()
                with self._lock_ac:
                    self._ros_actions_list[action_name] = action_type
            time.sleep(self.CHECK_INTERVAL)

    def _info_worker(self):
        """Background worker for the action metrics."""
        while self._running:
            info_dict = {}
            with self._lock_ac:
                info_dict = self._ros_actions_list.copy()

            if info_dict is None or len(info_dict) == 0:
                time.sleep(self.CHECK_INTERVAL)
                continue
            for info, _ in info_dict.items():
                info_output = self.get_info_actions(info=info)
                if info_output is None:
                    time.sleep(self.CHECK_INTERVAL)
                    continue
                clients = re.search(r'Action clients:\s*(\d+)', info_output)
                servers = re.search(r'Action servers:\s*(\d+)', info_output)

                clients_val = int(clients.group(1)) if clients else None
                servers_val = int(servers.group(1)) if servers else None
                with self._lock:
                    self._metrics[info] = {'clients': clients_val, 'servers': servers_val}

            time.sleep(self.CHECK_INTERVAL)

    def get_list_actions(self):
        """Get the list of ROS2 actions."""
        try:
            proc = subprocess.run(
                ['ros2', 'action', 'list', '-t'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            if proc.stderr:
                return None
            return proc.stdout
        except subprocess.CalledProcessError:
            return None

    def get_info_actions(self, info):
        """Get the info of ROS2 actions."""
        try:
            proc = subprocess.run(
                ['ros2', 'action', 'info', f'{info}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            if proc.stderr:
                return None
            return proc.stdout
        except subprocess.CalledProcessError:
            return None
