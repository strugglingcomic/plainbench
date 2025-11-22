"""Memory metric collectors using tracemalloc and psutil."""

import os
import tracemalloc
from typing import Optional

from .base import MetricCollector, MetricResult

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class TraceMallocCollector(MetricCollector):
    """Collects Python heap memory using tracemalloc."""

    def __init__(self):
        self._was_running: bool = False
        self._initial_memory: Optional[int] = None

    @property
    def name(self) -> str:
        return "python_memory"

    def setup(self) -> None:
        self._was_running = tracemalloc.is_tracing()
        if not self._was_running:
            tracemalloc.start()

    def start(self) -> None:
        # Reset peak to measure only this execution
        tracemalloc.reset_peak()
        current, _ = tracemalloc.get_traced_memory()
        self._initial_memory = current

    def stop(self) -> MetricResult:
        current, peak = tracemalloc.get_traced_memory()
        return MetricResult(
            name=self.name,
            value=peak,
            unit="bytes",
            metadata={
                "current": current,
                "peak": peak,
                "delta": current - self._initial_memory,
            },
        )

    def cleanup(self) -> None:
        if not self._was_running:
            tracemalloc.stop()
        self._initial_memory = None

    def is_available(self) -> bool:
        return True  # Available in Python 3.4+


class ProcessMemoryCollector(MetricCollector):
    """Collects total process memory using psutil."""

    def __init__(self):
        self._process: Optional[object] = None
        self._initial_rss: Optional[int] = None
        self._peak_rss: int = 0

    @property
    def name(self) -> str:
        return "process_memory"

    def setup(self) -> None:
        if PSUTIL_AVAILABLE:
            self._process = psutil.Process(os.getpid())

    def start(self) -> None:
        if self._process:
            mem_info = self._process.memory_info()
            self._initial_rss = mem_info.rss
            self._peak_rss = mem_info.rss

    def stop(self) -> MetricResult:
        if self._process:
            mem_info = self._process.memory_info()
            final_rss = mem_info.rss
            self._peak_rss = max(self._peak_rss, final_rss)

            return MetricResult(
                name=self.name,
                value=self._peak_rss,
                unit="bytes",
                metadata={
                    "rss": final_rss,
                    "vms": mem_info.vms,
                    "delta": final_rss - self._initial_rss,
                },
            )
        else:
            return MetricResult(
                name=self.name, value=None, unit="bytes", metadata={"available": False}
            )

    def cleanup(self) -> None:
        self._process = None
        self._initial_rss = None
        self._peak_rss = 0

    def is_available(self) -> bool:
        return PSUTIL_AVAILABLE
