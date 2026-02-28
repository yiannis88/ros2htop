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
Textual UI for ros2htop.

It provides a terminal-based interface to display real-time system and ROS2 metrics
collected by the Ros2HtopCore node.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""

import asyncio
from functools import partial
from typing import cast, Optional
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Static, TabbedContent, TabPane
from textual.containers import VerticalScroll
from ros2htop.ui.widgets.system import SystemWidget
from ros2htop.ui.widgets.node import NodeWidget
from ros2htop.ui.widgets.topic import TopicWidget
from ros2htop.ui.widgets.service import ServiceWidget
from ros2htop.ui.widgets.parameter import ParameterWidget
from ros2htop.ui.widgets.action import ActionWidget
from ros2htop.ui.widgets.help import HelpWidget, KeyHelpWidget


class SystemTUI(App):
    """Simple TUI."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("up", "scroll_up", "Scroll up"),
        ("down", "scroll_down", "Scroll down"),
        ("left", "prev_tab", "Change tab"),
        ("right", "next_tab", "Change tab"),

        ("c", "sort_cpu", "Sort by CPU"),
        ("g", "sort_gpu", "Sort by GPU"),
        ("l", "sort_lifecycle", "Sort by Lifecycle"),
        ("m", "sort_mem", "Sort by Memory"),
        ("n", "sort_name", "Sort by Name"),
        ("u", "sort_uptime", "Sort by Uptime"),

        ("p", "sort_pubs", "Sort by Topic/PUBS"),
        ("s", "sort_subs", "Sort by Topic/SUBS"),
        ("z", "sort_hz", "Sort by Topic/HZ"),
        ("d", "sort_qosd", "Sort by Topic/QOSD"),
        ("h", "sort_qosh", "Sort by Topic/QOSH"),
        ("r", "sort_qosr", "Sort by Topic/QOSR"),
        ("e", "sort_qosde", "Sort by Topic/QOSDE"),

        ("t", "sort_types", "Sort by Parameter/Type")
    ]

    HEADER_CONFIG = {
        "Nodes": {
            "name": {"label": "NODE ↑", "key": "name", "shortcut": "n"},
            "pid": {"label": "PID"},
            "uptime": {"label": "UPTIME ↓", "key": "uptime", "shortcut": "u"},
            "lifecycle_state": {"label": "LIFECYCLE ↑", "key": "lifecycle_state", "shortcut": "l"},
            "cpu": {"label": "CPU% ↓", "key": "cpu", "shortcut": "c"},
            "cpu#": {"label": "CPU#"},
            "gpu_load": {"label": "GPU% ↓", "key": "gpu_load", "shortcut": "g"},
            "gpu#": {"label": "GPU#"},
            "mem_pct": {"label": "MEM% ↓", "key": "mem_pct", "shortcut": "m"},
        },
        "Topics": {
            "name": {"label": "TOPIC ↑", "key": "name", "shortcut": "n"},
            "hidden": {"label": "HIDDEN"},
            "type": {"label": "TYPE"},
            "pubs": {"label": "PUBS# ↓", "key": "pubs", "shortcut": "p"},
            "subs": {"label": "SUBS# ↓", "key": "subs", "shortcut": "s"},
            "hz": {"label": "HZ ↓", "key": "hz", "shortcut": "z"},
            "msg_size": {"label": "SIZE ↓", "key": "msg_size", "shortcut": "m"},
            "durability_label": {"label": "QOSD ↑", "key": "durability_label", "shortcut": "d"},
            "reliability_label": {"label": "QOSR ↑", "key": "reliability_label", "shortcut": "r"},
            "history_label": {"label": "QOSH ↑", "key": "history_label", "shortcut": "h"},
            "depth": {"label": "QOSDE ↑", "key": "depth", "shortcut": "e"},
        },
        "Services": {
            "name": {"label": "SERVICE ↑", "key": "name", "shortcut": "n"},
            "type": {"label": "TYPE"},
        },
        "Parameters": {
            "name": {"label": "PARAMETER ↑", "key": "name", "shortcut": "n"},
            "type": {"label": "TYPE ↑", "key": "type", "shortcut": "t"},
            "node": {"label": "NODE"},
        },
        "Actions": {
            "name": {"label": "ACTION ↑", "key": "name", "shortcut": "n"},
            "servers": {"label": "SERVERS ↓", "key": "servers", "shortcut": "s"},
            "clients": {"label": "CLIENTS ↓", "key": "clients", "shortcut": "c"},
        }
    }

    def __init__(self, ros_node):
        super().__init__()
        self.ros_node = ros_node
        self.sort_key = "cpu"
        self.sort_topic_key = "pubs"
        self.sort_service_key = "name"
        self.sort_parameter_key = "name"
        self.sort_action_key = "name"
        self.system_widget = SystemWidget()
        self.node_widget = NodeWidget()
        self.topic_widget = TopicWidget()
        self.service_widget = ServiceWidget()
        self.parameter_widget = ParameterWidget()
        self.action_widget = ActionWidget()
        self.active_tab = "Nodes"
        self.label = Static("Starting...")

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Nodes", id="nodes"):
                yield self.system_widget
                with VerticalScroll():
                    yield self.node_widget
            with TabPane("Topics", id="topics"):
                with VerticalScroll():
                    yield self.topic_widget
            with TabPane("Services", id="services"):
                with VerticalScroll():
                    yield self.service_widget
            with TabPane("Parameters", id="parameters"):
                with VerticalScroll():
                    yield self.parameter_widget
            with TabPane("Actions", id="actions"):
                with VerticalScroll():
                    yield self.action_widget
            with TabPane("Help", id="help"):
                yield HelpWidget()
                yield KeyHelpWidget()

    @on(TabbedContent.TabActivated)
    def handle_tab_change(self, event: TabbedContent.TabActivated):
        """Handle tab change event."""
        self.active_tab = event.tab.label or "Nodes"

    async def on_mount(self):
        """On mount event start the refresh timer."""
        self.set_interval(2.0, lambda: asyncio.create_task(self.refresh_metrics()))
        self.query_one(TabbedContent).focus()

    async def on_unmount(self) -> None:
        """On umount event destroy the node."""
        self.log("Unmounting...")
        if self.ros_node:
            self.ros_node.trigger_shutdown()
        if self.ros_node:
            self.ros_node.destroy_node()
        self.ros_node = None

    def action_prev_tab(self) -> None:
        """Change tab."""
        try:
            tabs = self.query_one(TabbedContent)
            panes = list(tabs.query(TabPane))

            if not panes:
                return
            ids = [pane.id for pane in panes]
            if ids is None:
                return
            active_id: Optional[str] = tabs.active
            if active_id is None or active_id not in ids:
                tabs.active = cast(str, ids[0])
                return
            index = ids.index(active_id)
            tabs.active = cast(str, ids[(index - 1) % len(ids)])
        except Exception:
            pass

    def action_next_tab(self) -> None:
        """Change tab."""
        try:
            tabs = self.query_one(TabbedContent)
            panes = list(tabs.query(TabPane))

            if not panes:
                return
            ids = [pane.id for pane in panes]
            active_id: Optional[str] = tabs.active
            if active_id is None or active_id not in ids:
                tabs.active = cast(str, ids[0])
                return
            index = ids.index(active_id)
            tabs.active = cast(str, ids[(index + 1) % len(ids)])
        except Exception:
            pass

    def action_sort_name(self):
        """Sort name (in all tabs)."""
        if self.active_tab == "Nodes":
            self.sort_key = "name"
        elif self.active_tab == "Topics":
            self.sort_topic_key = "name"
        elif self.active_tab == "Services":
            self.sort_service_key = "name"
        elif self.active_tab == "Parameters":
            self.sort_parameter_key = "name"
        elif self.active_tab == "Actions":
            self.sort_action_key = "name"

    def action_sort_cpu(self):
        """Sort cpu."""
        if self.active_tab == "Nodes":
            self.sort_key = "cpu"
        if self.active_tab == "Actions":
            self.sort_action_key = "clients"

    def action_sort_gpu(self):
        """Sort gpu."""
        if self.active_tab == "Nodes":
            self.sort_key = "gpu_load"

    def action_sort_mem(self):
        """Sort mem in nodes and msg_size in topics."""
        if self.active_tab == "Nodes":
            self.sort_key = "mem_pct"
        elif self.active_tab == "Topics":
            self.sort_topic_key = "msg_size"

    def action_sort_uptime(self):
        """Sort uptime."""
        if self.active_tab == "Nodes":
            self.sort_key = "uptime"

    def action_sort_lifecycle(self):
        """Sort lifecycle."""
        if self.active_tab == "Nodes":
            self.sort_key = "lifecycle_state"

    def action_sort_pubs(self):
        """Sort pubs."""
        if self.active_tab == "Topics":
            self.sort_topic_key = "pubs"

    def action_sort_subs(self):
        """Sort subs."""
        if self.active_tab == "Topics":
            self.sort_topic_key = "subs"
        if self.active_tab == "Actions":
            self.sort_action_key = "servers"

    def action_sort_hz(self):
        """Sort hz."""
        if self.active_tab == "Topics":
            self.sort_topic_key = "hz"

    def action_sort_qosd(self):
        """Sort qosd."""
        if self.active_tab == "Topics":
            self.sort_topic_key = "durability_label"

    def action_sort_qosr(self):
        """Sort qosr."""
        if self.active_tab == "Topics":
            self.sort_topic_key = "reliability_label"

    def action_sort_qosh(self):
        """Sort qosh."""
        if self.active_tab == "Topics":
            self.sort_topic_key = "history_label"

    def action_sort_qosde(self):
        """Sort qosde."""
        if self.active_tab == "Topics":
            self.sort_topic_key = "depth"

    def action_sort_types(self):
        """Sort type."""
        if self.active_tab == "Parameters":
            self.sort_parameter_key = "type"

    async def refresh_metrics(self):
        """Fetch the data from ros2htop node."""
        if not self.ros_node:
            self.label.update("No ROS node")
            return

        active_tab = self.active_tab
        if active_tab == "Help":
            return

        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, partial(self.ros_node.fetch_metrics,
                                                            active_tab=active_tab))
            if active_tab == "Nodes":
                self.system_widget.update_metrics(data=data)
                hdr_cfg = SystemTUI.HEADER_CONFIG['Nodes']
                self.node_widget.update_metrics(data=data,
                                                sort_key=self.sort_key,
                                                header_config=hdr_cfg)
            elif active_tab == "Topics":
                hdr_cfg = SystemTUI.HEADER_CONFIG['Topics']
                self.topic_widget.update_metrics(data=data,
                                                 sort_key=self.sort_topic_key,
                                                 header_config=hdr_cfg)
            elif active_tab == "Services":
                hdr_cfg = SystemTUI.HEADER_CONFIG['Services']
                self.service_widget.update_metrics(data=data,
                                                   sort_key=self.sort_service_key,
                                                   header_config=hdr_cfg)
            elif active_tab == "Parameters":
                hdr_cfg = SystemTUI.HEADER_CONFIG['Parameters']
                self.parameter_widget.update_metrics(data=data,
                                                     sort_key=self.sort_parameter_key,
                                                     header_config=hdr_cfg)
            elif active_tab == "Actions":
                hdr_cfg = SystemTUI.HEADER_CONFIG['Actions']
                self.action_widget.update_metrics(data=data,
                                                  sort_key=self.sort_action_key,
                                                  header_config=hdr_cfg)
        except Exception as e:
            self.label.update(f"Error: {e}")
