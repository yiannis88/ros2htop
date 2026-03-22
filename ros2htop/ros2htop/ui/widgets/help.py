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
Help widget.

Help widget for the ros2htop TUI.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""

from rich.text import Text
from textual.widgets import Static


class HelpWidget(Static):
    """Help information for the users."""

    COLOURS = [
        'bold cyan',
        'bold magenta',
        'bold yellow',
        'bold green',
        'bold blue',
        'bold red',
        'bold coral',
        'bold bisque'
    ]

    BANNER = [
        '   ___  ____  _______  __ ____________  ___',
        '  / _ \\/ __ \\/ __/_  |/ // /_  __/ __ \\/ _ \\',
        ' / , _/ /_/ /\\ \\/ __// _  / / / / /_/ / ___/',
        '/_/|_|\\____/___/____/_//_/ /_/  \\____/_/   '
    ]

    def on_mount(self, event) -> None:
        """On mount show help."""
        self.current_line = 0
        side_hashes = 5
        ctx_width = 61
        total_width = side_hashes * 2 + ctx_width

        def pad_line(line: str):
            return '#' * side_hashes + line.center(ctx_width) + '#' * side_hashes

        self.total_banner = ['#' * total_width, '#' * total_width]
        for line in self.BANNER:
            if line == '':
                self.total_banner.append('#' * side_hashes + ' ' * ctx_width + '#' * side_hashes)
            else:
                self.total_banner.append(pad_line(line))

        self.total_banner.append(pad_line(''))
        self.total_banner.append(pad_line('(C) 2026 yiannis88.'))
        self.total_banner.append(pad_line('Released under the MIT License.'))
        self.total_banner += ['#' * total_width, '#' * total_width]

        self.set_interval(1.0, self.show_banner)

    def show_banner(self):
        """Show banner."""
        keyhelp_row = 13
        num_empty = max(0, keyhelp_row - len(self.total_banner[:self.current_line + 1]))
        tmp_txt = '\n'.join(self.total_banner[:self.current_line+1]) + '\n' * num_empty
        text_ = Text(
            text=f'{tmp_txt}',
            justify='center',
            style='bold green'
        )
        self.update(text_)
        self.current_line = (self.current_line + 1) % len(self.total_banner)


class KeyHelpWidget(Static):
    """Always-visible keybindings help."""

    def on_mount(self):
        """Show the help keys."""
        key_text = '[bold deepskyblue] Keys:[/bold deepskyblue]\n\n'
        key_text += '\t[deepskyblue]q[/deepskyblue]: Quit the app\n'
        key_text += '\t[deepskyblue]↑ / ↓[/deepskyblue]: Scroll up or down\n'
        key_text += '\t[deepskyblue]← / →[/deepskyblue]: Change tab\n'
        key_text += '\t[deepskyblue]c[/deepskyblue]: Sort by CPU (Nodes)\n'
        key_text += '\t[deepskyblue]g[/deepskyblue]: Sort by GPU (Nodes)\n'
        key_text += '\t[deepskyblue]l[/deepskyblue]: Sort by LIFECYCLE (Nodes)\n'
        key_text += '\t[deepskyblue]m[/deepskyblue]: Sort by MEM% (Nodes)\n'
        key_text += '\t[deepskyblue]n[/deepskyblue]: Sort by NODE/TOPIC/SERVICE/PARAMETER/ACTION\n'
        key_text += '\t[deepskyblue]p[/deepskyblue]: Sort by PUBS\n'
        key_text += '\t[deepskyblue]s[/deepskyblue]: Sort by SUBS\n'
        key_text += '\t[deepskyblue]u[/deepskyblue]: Sort by UPTIME\n'
        key_text += '\t[deepskyblue]z[/deepskyblue]: Sort by HZ (Hz rate)\n'
        key_text += '\t[deepskyblue]d[/deepskyblue]: Sort by QOSD (QoS durability)\n'
        key_text += '\t[deepskyblue]h[/deepskyblue]: Sort by QOSH (QoS history)\n'
        key_text += '\t[deepskyblue]r[/deepskyblue]: Sort by QOSR (QoS reliability)\n'
        key_text += '\t[deepskyblue]e[/deepskyblue]: Sort by QOSDE (QoS depth)\n'
        key_text += '\t[deepskyblue]t[/deepskyblue]: Sort by Type where possible'
        self.update(key_text)
