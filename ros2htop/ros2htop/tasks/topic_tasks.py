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
Topic Statistics.

Collects and processes topic metrics such as QoS, publishers, subscribers, etc.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""


from functools import partial
import importlib
import threading
import time
from typing import Any, Dict

from rclpy.lifecycle import LifecycleNode
from rclpy.qos import QoSPresetProfiles
from rclpy.serialization import serialize_message
from textual import log


DURABILITY_MAP = {-1: '?', 1: 'volatile', 2: 'transient_local'}
RELIABILITY_MAP = {-1: '?', 1: 'best_effort', 2: 'reliable'}
HISTORY_MAP = {-1: '?', 1: 'keep_last', 2: 'keep_all'}


class TopicTasks:
    """Collect and process topic metrics."""

    BATCH_SIZE = 10
    MEASURE_DURATION = 60.0
    MEASURE_LIMIT = 10
    CHECK_INTERVAL = 2.0

    def __init__(self):
        self._lock = threading.Lock()
        self._lock_hz = threading.Lock()

        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._hz_sessions: Dict[str, Dict[str, Any]] = {}

        self._running = True
        self._node: LifecycleNode = None

        self._thread = threading.Thread(target=self._hz_worker, daemon=False)
        self._thread.start()

    def stop(self):
        """Stop the background Hz thread."""
        self._running = False
        self._thread.join()

    def resolve_msg_type(self, type_str: str):
        """Return the msg type from a string."""
        try:
            pkg, _, msg = type_str.partition('/msg/')
            module = importlib.import_module(f'{pkg}.msg')
            return getattr(module, msg)
        except Exception as err:
            log(f'Failed to resolve message type {type_str}: {err}')
            return None

    def get_metrics(self):
        """Return the latest topic metrics."""
        with self._lock:
            return self._metrics.copy()

    def _start_hz_measurement(self, msg, topic_name):
        """Handle the Hz measurement thread callback."""
        try:
            with self._lock_hz:
                if topic_name not in self._hz_sessions:
                    return

                if len(self._hz_sessions[topic_name]['timestamps']) >= TopicTasks.MEASURE_LIMIT:
                    return
                bytes_size = len(serialize_message(msg))
                self._hz_sessions[topic_name]['timestamps'].append(time.time())
                self._hz_sessions[topic_name]['msg_size'] += bytes_size
        except Exception as err:
            log('Error getting node state: %s', err)
            return

    def _hz_worker(self):
        """Background thread for measuring the Hz."""
        while self._running:
            if not self._node or not self._metrics:
                time.sleep(TopicTasks.CHECK_INTERVAL)
                continue

            update_hz = {}
            continue_flag = False
            with self._lock_hz:
                if self._hz_sessions:
                    for name in list(self._hz_sessions.keys()):
                        session = self._hz_sessions[name]
                        if (
                            time.time() - session['start_time'] > TopicTasks.MEASURE_DURATION
                            or len(session['timestamps']) >= TopicTasks.MEASURE_LIMIT
                        ):
                            self._node.destroy_subscription(session['subscription'])
                            rate_ = 0
                            msg_size = 0
                            samples = len(session['timestamps'])
                            if samples > 0:
                                dt = session['timestamps'][-1] - session['timestamps'][0]
                                if dt == 0:
                                    rate_ = 1 / TopicTasks.MEASURE_DURATION
                                else:
                                    rate_ = (samples - 1) / dt
                                msg_size = int(session['msg_size'] / samples)
                            update_hz[name] = {'rate': rate_, 'msg_size': msg_size}
                            del self._hz_sessions[name]
                    if len(self._hz_sessions) >= TopicTasks.BATCH_SIZE:
                        continue_flag = True

            with self._lock:
                for name, rate in update_hz.items():
                    if name in self._metrics:
                        self._metrics[name]['hz'] = rate['rate']
                        self._metrics[name]['msg_size'] = rate['msg_size']

            if continue_flag:
                time.sleep(TopicTasks.CHECK_INTERVAL)
                continue

            topic_name = None
            topic_info = None
            with self._lock:
                for name, info in self._metrics.items():
                    if (
                        info.get('hz') is None
                        and info.get('durability') >= 0
                        and info.get('pubs', 0) > 0
                        and not info.get('hidden', True)
                    ):
                        topic_name = name
                        topic_info = info
                        break

            if not topic_info or len(topic_info['types']) == 0:
                time.sleep(TopicTasks.CHECK_INTERVAL)
                continue

            msg_type = self.resolve_msg_type(topic_info['types'][0])
            if not msg_type:
                time.sleep(TopicTasks.CHECK_INTERVAL)
                continue

            with self._lock:
                if topic_name in self._metrics:
                    self._metrics[topic_name]['hz'] = -1
            try:
                qos_profile = QoSPresetProfiles.SYSTEM_DEFAULT.value
                sub = self._node.create_subscription(
                    msg_type=msg_type,
                    callback=partial(self._start_hz_measurement, topic_name=topic_name),
                    topic=topic_name,
                    qos_profile=qos_profile
                )
            except Exception as err:
                log(f'Failed to create subscription for {topic_name}: {err}')
                time.sleep(TopicTasks.CHECK_INTERVAL)
                continue

            with self._lock_hz:
                self._hz_sessions[topic_name] = {
                    'timestamps': [],
                    'msg_size': 0,
                    'start_time': time.time(),
                    'subscription': sub
                }

            time.sleep(TopicTasks.CHECK_INTERVAL)

    def update_metrics(self, node: LifecycleNode) -> None:
        """Collect and process topic metrics."""
        try:
            if not self._node:
                self._node = node
            topic_list = node.get_topic_names_and_types()

            topics = {}
            for name, types in topic_list:
                publishers = node.get_publishers_info_by_topic(name)
                subscribers = node.get_subscriptions_info_by_topic(name)
                qos = None
                if publishers:
                    # get QoS for 1st publisher only
                    qos_profile = publishers[0].qos_profile
                    qos = {
                        'durability': qos_profile.durability.value,
                        'durability_label': DURABILITY_MAP.get(qos_profile.durability.value,
                                                               '?'),
                        'history': qos_profile.history.value,
                        'history_label': HISTORY_MAP.get(qos_profile.history.value,
                                                         '?'),
                        'depth': qos_profile.depth,
                        'reliability': qos_profile.reliability.value,
                        'reliability_label': RELIABILITY_MAP.get(qos_profile.reliability.value,
                                                                 '?')
                    }
                topics[name] = {
                    'types': types,
                    'pubs': len(publishers) if publishers else 0,
                    'subs': len(subscribers) if subscribers else 0,
                    'durability': qos['durability'] if qos else 0,
                    'durability_label': qos['durability_label'] if qos else '?',
                    'history': qos['history'] if qos else 0,
                    'history_label': qos['history_label'] if qos else '?',
                    'depth': qos['depth'] if qos else 0,
                    'reliability': qos['reliability'] if qos else 0,
                    'reliability_label': qos['reliability_label'] if qos else '?',
                    'hidden': True if '_action/' in name or name.startswith('/_') else False
                }
            with self._lock:
                for name, new_data in topics.items():
                    entry = self._metrics.get(name, {})
                    entry.update(new_data)
                    entry.setdefault('hz', None)
                    entry.setdefault('msg_size', 0)
                    self._metrics[name] = entry
                removed = set(self._metrics.keys()) - set(topics.keys())
                for name in removed:
                    self._metrics.pop(name, None)
        except Exception as err:
            log('Error collecting topic metrics: %s', err)
