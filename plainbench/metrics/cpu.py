"""CPU metric collector using psutil."""

import os
from typing import Optional

from .base import MetricCollector, MetricResult

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class CPUCollector(MetricCollector):
    """Collects CPU usage metrics using psutil."""

    def __init__(self):
        self._process: Optional[object] = None
        self._initial_times = None

    @property
    def name(self) -> str:
        return "cpu_usage"

    def setup(self) -> None:
        if PSUTIL_AVAILABLE:
            self._process = psutil.Process(os.getpid())

    def start(self) -> None:
        if self._process:
            try:
                self._initial_times = self._process.cpu_times()
            except (AttributeError, OSError):
                self._initial_times = None

    def stop(self) -> MetricResult:
        if self._process and self._initial_times:
            try:
                final_times = self._process.cpu_times()
                user_time = final_times.user - self._initial_times.user
                system_time = final_times.system - self._initial_times.system
                total_time = user_time + system_time

                return MetricResult(
                    name=self.name,
                    value=total_time,
                    unit="seconds",
                    metadata={
                        "user_time": user_time,
                        "system_time": system_time,
                    },
                )
            except (AttributeError, OSError):
                pass

        return MetricResult(
            name=self.name, value=None, unit="seconds", metadata={"available": False}
        )

    def cleanup(self) -> None:
        self._process = None
        self._initial_times = None

    def is_available(self) -> bool:
        return PSUTIL_AVAILABLE
