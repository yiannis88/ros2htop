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
System statistics.

Collects and processes system metrics such as CPU usage, memory usage,
disk usage, etc.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""

import math

from textual.widgets import Static

PER_ROW = 5


def make_bar(value: float) -> str:
    """
    Make a bar, following htop format.

    We have 10 steps with the first 5 bars being green,
    the next 3 bars are orange, and the last 2 bars are red.
    """
    def bar_colour(bars: int, value: float) -> str:
        """Return the bar colour."""
        green_ = min(bars, 5)
        orange_ = min(max(bars - 5, 0), 2)
        red_ = min(max(bars - 7, 0), 3)  # sanity
        empty_ = 10 - bars

        return (
            '\\['
            f"{'[green]' + '|' * green_ + '[/green]' if green_ else ''}"
            f"{'[orange]' + '|' * orange_ + '[/orange]' if orange_ else ''}"
            f"{'[red]' + '|' * red_ + '[/red]' if red_ else ''}"
            f"{'':{empty_}}"
            f' [grey]{value:4.1f}%[/grey]]'
        )

    value = max(0.0, min(100.0, value))
    bars = 0
    if value > 0:
        bars = math.ceil(value / 10)

    return bar_colour(bars=bars, value=value)


def group_horizontal(items, per_row=4):
    """Yield lists of items grouped N per row."""
    for i in range(0, len(items), per_row):
        yield items[i:i + per_row]


class SystemWidget(Static):
    """SYSTEM metrics panel."""

    def render_system(self, sys: dict) -> str:
        """Render the system widget."""
        lines = []
        header = 'SYSTEM'
        header_fill = int((self.size.width - len(header)) / 2)
        header = ' ' * header_fill + header + ' ' * header_fill

        # Header
        lines.append(f'[bold black on #90EE90]{header}[/bold black on #90EE90]')

        # CPU
        lines.append('[skyblue]CPU[/skyblue]')
        if 'cpu' in sys:
            cpu_items = []
            for core, load in sys['cpu'].items():
                bar_str = make_bar(load)
                cpu_items.append(f'{core:02d}: {bar_str}')
            for row in group_horizontal(cpu_items, per_row=PER_ROW):
                lines.append(' '.join(row))

        # GPU
        lines.append('[skyblue]GPU[/skyblue]')
        if 'gpu' in sys and sys['gpu']:
            gpu_items = []
            for gid, stats in sys['gpu'].items():
                bar_str = make_bar(stats['load'])
                gpu_items.append(f'{gid:02d}: {bar_str}')
            for row in group_horizontal(gpu_items, per_row=PER_ROW):
                lines.append(' '.join(row))

        # SYS
        mem_bar = ''
        cpu_bar = ''
        disk_bar = ''
        if 'mem_sys' in sys:
            mem_bar = make_bar(sys['mem_sys'])
        if 'cpu_sys' in sys:
            cpu_bar = make_bar(sys['cpu_sys'])
        if 'disk_sys' in sys:
            disk_bar = make_bar(sys['disk_sys'])
        temp_bar = sys.get('temp_sys', '')
        lines.append(f'\n[skyblue]MEM[/skyblue] {mem_bar}\t[skyblue]CPU[/skyblue] {cpu_bar}\t[skyblue]DISK[/skyblue] {disk_bar}\t[skyblue]TEMP[/skyblue] [grey]{temp_bar}°C[/grey]\n')

        # ROS
        rmw_avimpl = sys.get('rmw_avimpl', '')
        rmw_impl = sys.get('rmw_implementation', '')
        rmw_txt = []
        for rmw in rmw_avimpl:
            if rmw_impl == rmw:
                rmw_txt.append(f'[green]{rmw}[/green]')
            else:
                rmw_txt.append(f'[grey]{rmw}[/grey]')

        fields = [
            ('ROS_DOMAIN_ID', f"[grey]{sys.get('ros_domain_id', '')}[/grey]"),
            ('RMW_IMPLEMENTATION', ', '.join(rmw_txt)),
            ('ROS_DISTRO', f"[grey]{sys.get('ros_distro', '')}[/grey]")
        ]
        line = '\t'.join(
            f'[skyblue]{label}[/skyblue] {value}'
            for label, value in fields
        )

        lines.append(line)

        fields_stats = [
            ('NODES#', sys.get('node#', -1)),
            ('TOPICS#', sys.get('topic#', -1)),
            ('HIDDEN#', sys.get('hidden#', -1)),
            ('TOTAL_HZ', math.floor(sys.get('total_hz', 0.0))),
            ('TOTAL_BPS', math.ceil(sys.get('total_bytes', 0.0))),
            ('SERVICES#', sys.get('service#', -1)),
            ('PARAMETERS#', sys.get('parameter#', -1)),
            ('ACTIONS#', sys.get('action#', -1)),
            ('ACTIONS_S#', sys.get('action_s#', -1)),
            ('ACTIONS_C#', sys.get('action_c#', -1))
        ]
        line = '\t'.join(
            f'[skyblue]{label}[/skyblue] [grey]{value}[/grey]'
            for label, value in fields_stats
        )

        lines.append(line)
        return '\n'.join(lines)

    def update_metrics(self, data: dict):
        """Update the system metrics."""
        if not data or 'sys' not in data:
            return

        self.update(self.render_system(sys=data['sys']))
