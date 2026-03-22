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
Test Textual tabs.

Test the textual tabs by simulating key presses.

Author: yiannis88 <selinis.g@gmail.com> 2026
"""

import pytest
from ros2htop.ui.textual_app import SystemTUI


@pytest.mark.asyncio
async def test_textual_tabs():
    """Test tab switching."""
    app = SystemTUI(ros_node=None)
    async with app.run_test() as pilot:
        assert app.active_tab == 'Nodes'
        await pilot.press('right')
        await pilot.pause()
        assert app.active_tab == 'Topics'
        await pilot.press('right')
        await pilot.pause()
        assert app.active_tab == 'Services'
        await pilot.press('right')
        await pilot.pause()
        assert app.active_tab == 'Parameters'
        await pilot.press('right')
        await pilot.pause()
        assert app.active_tab == 'Actions'
        await pilot.press('right')
        await pilot.pause()
        assert app.active_tab == 'Help'
        await pilot.press('left')
        await pilot.pause()
        assert app.active_tab == 'Actions'
