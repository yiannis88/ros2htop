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

import os
import threading
import psutil
from textual import log

try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False


class SystemTasks:
    """Collect and process system metrics."""

    def __init__(self):
        self._lock = threading.Lock()
        self._lock_gpu = threading.Lock()
        self._gpu_available = False
        self._metrics = {
            'cpu': {},
            'cpu_sys': 0.0,
            'mem_sys': 0.0,
            'disk_sys': 0.0,
            'gpu': {},
            'gpu_sys': 0.0,
            'temp_sys': 0.0,
            'ros_domain_id': os.getenv('ROS_DOMAIN_ID'),
            'rmw_implementation': os.getenv('RMW_IMPLEMENTATION'),
            'ros_distro': os.getenv('ROS_DISTRO')
        }
        self._gpu_proc_map = {}

        try:
            for ii in range(psutil.cpu_count()):
                self._metrics['cpu'][ii] = 0.0
        except Exception as err:
            log('Failed to initialise CPU metrics: ', err)

        if NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                for ii in range(pynvml.nvmlDeviceGetCount()):
                    self._metrics['gpu'][ii] = {
                        'load': 0.0,
                        'memory_used': 0,
                        'memory_total': 0,
                        'temperature': 0
                    }
                self._gpu_available = True
                log('NVML initialised with %d GPUs.', len(self._metrics['gpu']))
            except Exception as err:
                log('Failed to initialise NVML: %s', err)
        else:
            log('NVML library not available, GPU metrics will be disabled.')

    def get_metrics(self):
        """Return the latest system metrics."""
        with self._lock:
            return self._metrics.copy()

    def get_gpu_map(self):
        """Return the GPU process map."""
        with self._lock_gpu:
            return self._gpu_proc_map.copy()

    def has_gpu(self) -> bool:
        """Return whether GPU is available."""
        return self._gpu_available

    def update_metrics(self):
        """Collect and process system metrics."""
        try:
            cpu_sys = psutil.cpu_percent(interval=None)
            mem_sys = psutil.virtual_memory().percent
            disk_sys = psutil.disk_usage('/').percent
            core_temps = psutil.sensors_temperatures().get('coretemp')
            gpu_process_map = {}
            if core_temps:
                temp_sys = max(temp.current for temp in core_temps)
            else:
                temp_sys = 0.0
            cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
            for ii, cpu in enumerate(cpu_per_core):
                self._metrics['cpu'][ii] = cpu
            if self._metrics['gpu']:
                for ii, gpu_data in self._metrics['gpu'].items():
                    handle = pynvml.nvmlDeviceGetHandleByIndex(ii)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    gpu_data.update({
                        'load': util.gpu,
                        'memory_used': mem.used,
                        'memory_total': mem.total,
                        'temperature': temp
                    })
                for proc in pynvml.nvmlDeviceGetComputeRunningProcesses(handle):
                    gpu_process_map[proc.pid] = {
                        'gpu_index': ii,
                        'gpu_mem_mb': round(proc.usedGpuMemory / (1024 * 1024), 1),
                        'gpu_mem_pct': round((proc.usedGpuMemory / mem.total) * 100.0, 1),
                        'gpu_load': util.gpu
                    }
            with self._lock:
                self._metrics['cpu_sys'] = cpu_sys
                self._metrics['mem_sys'] = mem_sys
                self._metrics['disk_sys'] = disk_sys
                self._metrics['temp_sys'] = temp_sys
                gpu_loads = [gpu_data['load'] for gpu_data in self._metrics['gpu'].values()]
                self._metrics['gpu_sys'] = sum(gpu_loads) / len(gpu_loads) if gpu_loads else 0.0
            with self._lock_gpu:
                self._gpu_proc_map = gpu_process_map
        except Exception as err:
            log('Error collecting system metrics: %s', err)
