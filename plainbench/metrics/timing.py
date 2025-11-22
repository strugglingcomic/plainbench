"""Timing metric collectors using time.perf_counter() and time.process_time()."""

import time
from typing import Optional

from .base import MetricCollector, MetricResult


class WallTimeCollector(MetricCollector):
    """Collects wall clock time using time.perf_counter()."""

    def __init__(self):
        self._start_time: Optional[float] = None

    @property
    def name(self) -> str:
        return "wall_time"

    def setup(self) -> None:
        pass  # No setup needed

    def start(self) -> None:
        self._start_time = time.perf_counter()

    def stop(self) -> MetricResult:
        end_time = time.perf_counter()
        elapsed = end_time - self._start_time
        return MetricResult(name=self.name, value=elapsed, unit="seconds")

    def cleanup(self) -> None:
        self._start_time = None

    def is_available(self) -> bool:
        return True


class CPUTimeCollector(MetricCollector):
    """Collects CPU time using time.process_time()."""

    def __init__(self):
        self._start_time: Optional[float] = None

    @property
    def name(self) -> str:
        return "cpu_time"

    def setup(self) -> None:
        pass

    def start(self) -> None:
        self._start_time = time.process_time()

    def stop(self) -> MetricResult:
        end_time = time.process_time()
        elapsed = end_time - self._start_time
        return MetricResult(name=self.name, value=elapsed, unit="seconds")

    def cleanup(self) -> None:
        self._start_time = None

    def is_available(self) -> bool:
        return True
