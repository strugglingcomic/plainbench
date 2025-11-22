"""I/O metric collector using psutil."""

import os
from typing import Optional

from .base import MetricCollector, MetricResult

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class IOCollector(MetricCollector):
    """Collects disk I/O metrics using psutil."""

    def __init__(self):
        self._process: Optional[object] = None
        self._initial_io = None

    @property
    def name(self) -> str:
        return "disk_io"

    def setup(self) -> None:
        if PSUTIL_AVAILABLE:
            self._process = psutil.Process(os.getpid())

    def start(self) -> None:
        if self._process:
            try:
                self._initial_io = self._process.io_counters()
            except (AttributeError, OSError):
                # Not available on this platform
                self._initial_io = None

    def stop(self) -> MetricResult:
        if self._initial_io is None:
            return MetricResult(
                name=self.name, value=None, unit="bytes", metadata={"available": False}
            )

        try:
            final_io = self._process.io_counters()
            read_bytes = final_io.read_bytes - self._initial_io.read_bytes
            write_bytes = final_io.write_bytes - self._initial_io.write_bytes

            return MetricResult(
                name=self.name,
                value=read_bytes + write_bytes,
                unit="bytes",
                metadata={
                    "read_bytes": read_bytes,
                    "write_bytes": write_bytes,
                    "read_count": final_io.read_count - self._initial_io.read_count,
                    "write_count": final_io.write_count - self._initial_io.write_count,
                },
            )
        except (AttributeError, OSError):
            return MetricResult(
                name=self.name, value=None, unit="bytes", metadata={"available": False}
            )

    def cleanup(self) -> None:
        self._process = None
        self._initial_io = None

    def is_available(self) -> bool:
        """Check if I/O counters are available on this platform."""
        if not PSUTIL_AVAILABLE:
            return False
        try:
            process = psutil.Process(os.getpid())
            process.io_counters()
            return True
        except (AttributeError, OSError):
            return False  # Not available on macOS, limited on Windows
