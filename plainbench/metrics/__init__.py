"""
Metrics collection module.

Provides collectors for various performance metrics:
- Timing (wall time, CPU time)
- Memory (tracemalloc, psutil)
- CPU usage and affinity
- Disk I/O
- Custom metrics via registry
"""

from plainbench.metrics.base import MetricCollector, MetricResult
from plainbench.metrics.cpu import CPUCollector
from plainbench.metrics.io import IOCollector
from plainbench.metrics.memory import ProcessMemoryCollector, TraceMallocCollector
from plainbench.metrics.registry import (
    MetricRegistry,
    get_metric_registry,
    register_metric,
)
from plainbench.metrics.timing import CPUTimeCollector, WallTimeCollector

__all__ = [
    "MetricCollector",
    "MetricResult",
    "WallTimeCollector",
    "CPUTimeCollector",
    "TraceMallocCollector",
    "ProcessMemoryCollector",
    "IOCollector",
    "CPUCollector",
    "MetricRegistry",
    "get_metric_registry",
    "register_metric",
]
