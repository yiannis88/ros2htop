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
Topic statistics.

Collects and processes ros2 topic metrics.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""


from textual.widgets import Static
from rich import box
from rich.table import Table
from rich.text import Text


class TopicWidget(Static):
    """TOPIC metrics panel."""

    def render_node(self, topic: dict, sort_key: str = 'pubs', hdr_cfg: dict = None) -> Table:
        """Render the topic widget."""

        def sort_value(item, key):
            """Sort function."""
            name, metrics = item
            if key == "name":
                return name.lower()
            value = metrics.get(key)

            if value is None:
                return -1
            if isinstance(value, str):
                return value.lower()
            return value

        table = Table(min_width=self.size.width,
                      box=box.HORIZONTALS,
                      header_style="bold black on #90EE90",
                      show_lines=True)

        if hdr_cfg is None:
            return table

        for _, value in hdr_cfg.items():
            label_ = value.get("label")
            key_ = value.get("key")
            shortcut_ = value.get("shortcut")
            display_label = f"{label_} [{shortcut_}]" if shortcut_ else label_
            if key_ and key_ == sort_key:
                table.add_column(header=Text(display_label),
                                 header_style="bold black on #00BFFF",
                                 justify="center",
                                 no_wrap=True,
                                 overflow="ellipsis")
            else:
                table.add_column(header=Text(display_label),
                                 justify="center",
                                 no_wrap=True,
                                 overflow="ellipsis")

        if not topic:
            return table

        sorted_topics = sorted(
            topic.items(),
            key=lambda item: item[0].lower() if sort_key == "name" else sort_value(item, sort_key),
            reverse=False if sort_key == "name" else True
        )

        for i, (name, metrics) in enumerate(sorted_topics):
            types = metrics.get("types")
            type_ = (
                types[0]
                if isinstance(types, list) and types
                else ""
            )
            size = metrics.get("msg_size") or 0
            hz_ = metrics.get("hz") or 0.0
            durability = metrics.get("durability_label", "?")
            reliability = metrics.get("reliability_label", "?")
            history = metrics.get("history_label", "?")
            depth = metrics.get("depth") or 0

            if hz_ > 50:
                row_style = "bold white on #DC143C"
            else:
                row_style = "bold white" if i % 2 == 0 else "bold #008000"

            table.add_row(
                Text(f"{name}",
                     justify='center',
                     style=row_style),
                Text(f"{metrics.get('hidden', True)}",
                     justify='center',
                     style=row_style),
                Text(f"{type_}",
                     justify='center',
                     style=row_style),
                Text(f"{metrics.get('pubs', '')}",
                     justify='center',
                     style=row_style),
                Text(f"{metrics.get('subs', '')}",
                     justify='center',
                     style=row_style),
                Text(f"{hz_:.2f}",
                     justify='center',
                     style=row_style),
                Text(f"{size:.0f}",
                     justify='center',
                     style=row_style),
                Text(durability,
                     justify='center',
                     style=row_style),
                Text(reliability,
                     justify='center',
                     style=row_style),
                Text(history,
                     justify='center',
                     style=row_style),
                Text(f"{depth}",
                     justify='center',
                     style=row_style))
        return table

    def update_metrics(self, data: dict, sort_key: str = 'pubs', header_config: dict = None):
        """Update the topic metrics."""
        if not data or not header_config or "topic" not in data:
            return

        self.update(self.render_node(topic=data["topic"],
                                     sort_key=sort_key,
                                     hdr_cfg=header_config))
