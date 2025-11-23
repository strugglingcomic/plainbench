"""
Process monitoring for shell commands.

Provides both snapshot and continuous monitoring modes using psutil.
"""

import time
import threading
from typing import Optional, Dict, Any
import psutil


class ProcessMonitor:
    """
    Monitor process resource usage during execution.

    Supports two modes:
    - snapshot: Capture metrics at start and end
    - continuous: Poll metrics at regular intervals to track peaks
    """

    def __init__(
        self,
        process: psutil.Process,
        mode: str = "snapshot",
        interval: float = 0.1
    ):
        """
        Initialize process monitor.

        Args:
            process: psutil.Process to monitor
            mode: Monitoring mode ('snapshot' or 'continuous')
            interval: Polling interval for continuous mode (seconds)
        """
        self.process = process
        self.mode = mode
        self.interval = interval

        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

        # Collected metrics
        self._initial_io: Optional[Any] = None
        self._final_io: Optional[Any] = None
        self._peak_memory: int = 0
        self._cpu_samples: list = []
        self._memory_samples: list = []

    def start(self) -> None:
        """Start monitoring the process."""
        # Capture initial I/O counters if available
        try:
            self._initial_io = self.process.io_counters()
        except (AttributeError, OSError, ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
            # ValueError can occur on some Linux systems with unusual /proc format
            self._initial_io = None

        if self.mode == "continuous":
            self._monitoring = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
        elif self.mode == "snapshot":
            # Just capture initial state
            try:
                mem_info = self.process.memory_info()
                self._peak_memory = mem_info.rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def stop(self) -> Dict[str, Any]:
        """
        Stop monitoring and return collected metrics.

        Returns:
            Dictionary of metrics collected during monitoring
        """
        if self.mode == "continuous":
            self._monitoring = False
            if self._monitor_thread:
                self._monitor_thread.join(timeout=1.0)

        # Capture final I/O counters
        try:
            self._final_io = self.process.io_counters()
        except (AttributeError, OSError, ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
            # ValueError can occur on some Linux systems with unusual /proc format
            self._final_io = None

        # For snapshot mode, capture final memory
        if self.mode == "snapshot":
            try:
                mem_info = self.process.memory_info()
                self._peak_memory = max(self._peak_memory, mem_info.rss)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return self._get_metrics()

    def _monitor_loop(self) -> None:
        """Continuous monitoring loop (runs in separate thread)."""
        while self._monitoring:
            try:
                # Sample memory
                mem_info = self.process.memory_info()
                self._memory_samples.append(mem_info.rss)
                self._peak_memory = max(self._peak_memory, mem_info.rss)

                # Sample CPU (non-blocking)
                try:
                    cpu_percent = self.process.cpu_percent(interval=0)
                    if cpu_percent is not None:
                        self._cpu_samples.append(cpu_percent)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break

                time.sleep(self.interval)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process terminated
                break

    def _get_metrics(self) -> Dict[str, Any]:
        """Compile collected metrics into a dictionary."""
        metrics: Dict[str, Any] = {
            "peak_memory": self._peak_memory if self._peak_memory > 0 else None,
        }

        # I/O metrics (calculate delta)
        if self._initial_io and self._final_io:
            try:
                metrics["read_bytes"] = self._final_io.read_bytes - self._initial_io.read_bytes
                metrics["write_bytes"] = self._final_io.write_bytes - self._initial_io.write_bytes
            except AttributeError:
                # Some platforms don't have all I/O fields
                pass

        # CPU metrics (only available in continuous mode)
        if self._cpu_samples:
            metrics["cpu_percent"] = sum(self._cpu_samples) / len(self._cpu_samples)

        return metrics
