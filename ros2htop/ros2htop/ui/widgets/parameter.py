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
Parameter statistics.

Collects and processes ros2 parameters metrics.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""


from textual.widgets import Static
from rich import box
from rich.table import Table
from rich.text import Text


class ParameterWidget(Static):
    """PARAMETER metrics panel."""

    PARAM_TYPE_MAP = {
        0: "unknown",
        1: "bool",
        2: "integer",
        3: "double",
        4: "string",
        5: "byte_array",
        6: "bool_array",
        7: "integer_array",
        8: "double_array",
        9: "string_array",
    }

    def render_node(self, parameter: dict, sort_key: str = 'name', hdr_cfg: dict = None) -> Table:
        """Render the parameter widget."""
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

        if not parameter:
            return table

        flat_params = []
        for node_name, metrics in parameter.items():
            params = metrics.get("params", {})
            for param_name, param_data in params.items():
                type_int = param_data.get("type", 0)
                type_str = self.PARAM_TYPE_MAP.get(type_int, str(type_int))
                flat_params.append({
                    "node": node_name,
                    "name": param_name,
                    "type": type_str
                })

        if sort_key == "name":
            sorted_parameters = sorted(flat_params, key=lambda x: x["name"].lower())
        elif sort_key == "type":
            sorted_parameters = sorted(flat_params, key=lambda x: x["type"].lower())
        else:
            sorted_parameters = flat_params

        i = 0
        for i, metrics in enumerate(sorted_parameters):
            row_style = "bold white" if i % 2 == 0 else "bold #008000"
            table.add_row(
                Text(metrics.get("name", "?"),
                     justify='center',
                     style=row_style),
                Text(metrics.get("type", "?"),
                     justify='center',
                     style=row_style),
                Text(metrics.get("node", "?"),
                     justify='center',
                     style=row_style))

        return table

    def update_metrics(self, data: dict, sort_key: str = 'name', header_config: dict = None):
        """Update the parameter metrics."""
        if not data or not header_config or "param" not in data:
            return

        self.update(self.render_node(parameter=data["param"],
                                     sort_key=sort_key,
                                     hdr_cfg=header_config))
