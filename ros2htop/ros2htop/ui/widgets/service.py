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
Service statistics.

Collects and processes ros2 service metrics.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""

from typing import Any

from rich import box
from rich.table import Table
from rich.text import Text
from textual.widgets import Static


class ServiceWidget(Static):
    """SERVICE metrics panel."""

    def render_node(self,
                    service: dict,
                    sort_key: str = 'name',
                    hdr_cfg: dict[Any, Any] | None = None) -> Table:
        """Render the service widget."""

        def sort_value(item, key):
            """Sort function."""
            name, metrics = item
            if key == 'name':
                return name.lower()
            value = metrics.get(key)

            if value is None:
                return -1
            if isinstance(value, str):
                return value.lower()
            return value

        table = Table(min_width=self.size.width,
                      box=box.HORIZONTALS,
                      header_style='bold black on #90EE90',
                      show_lines=True)

        if hdr_cfg is None:
            return table

        for _, value in hdr_cfg.items():
            label_ = value.get('label')
            key_ = value.get('key')
            shortcut_ = value.get('shortcut')
            display_label = f'{label_} [{shortcut_}]' if shortcut_ else label_
            if key_ and key_ == sort_key:
                table.add_column(header=Text(display_label),
                                 header_style='bold black on #00BFFF',
                                 justify='center',
                                 no_wrap=True,
                                 overflow='ellipsis')
            else:
                table.add_column(header=Text(display_label),
                                 justify='center',
                                 no_wrap=True,
                                 overflow='ellipsis')

        if not service:
            return table

        sorted_services = sorted(
            service.items(),
            key=lambda item: item[0].lower() if sort_key == 'name' else sort_value(item, sort_key),
            reverse=False if sort_key == 'name' else True
        )

        for i, (name, metrics) in enumerate(sorted_services):
            row_style = 'bold white' if i % 2 == 0 else 'bold #008000'
            type_ = metrics.get('types', '?')

            table.add_row(
                Text(f'{name}',
                     justify='center',
                     style=row_style),
                Text(f'{type_}',
                     justify='center',
                     style=row_style))
        return table

    def update_metrics(self,
                       data: dict,
                       sort_key: str = 'name',
                       header_config: dict[Any, Any] | None = None):
        """Update the service metrics."""
        if not data or not header_config or 'service' not in data:
            return

        self.update(self.render_node(service=data['service'],
                                     sort_key=sort_key,
                                     hdr_cfg=header_config))
