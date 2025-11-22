"""Metric registry for managing metric collectors."""

from typing import Dict, List, Type

from .base import MetricCollector


class MetricRegistry:
    """Registry for metric collectors, allowing custom metrics."""

    def __init__(self):
        self._collectors: Dict[str, Type[MetricCollector]] = {}

    def register(self, name: str, collector_class: Type[MetricCollector]) -> None:
        """Register a metric collector."""
        if not issubclass(collector_class, MetricCollector):
            raise TypeError(f"{collector_class} must inherit from MetricCollector")
        self._collectors[name] = collector_class

    def get(self, name: str) -> Type[MetricCollector]:
        """Get a metric collector class by name."""
        if name not in self._collectors:
            raise KeyError(f"Metric collector '{name}' not registered")
        return self._collectors[name]

    def get_all(self) -> Dict[str, Type[MetricCollector]]:
        """Get all registered metric collectors."""
        return self._collectors.copy()

    def create_collectors(self, names: List[str]) -> List[MetricCollector]:
        """Create instances of metric collectors by name."""
        collectors = []
        for name in names:
            collector_class = self.get(name)
            collector = collector_class()
            if collector.is_available():
                collectors.append(collector)
        return collectors


# Global registry instance
_registry = MetricRegistry()


def register_metric(name: str, collector_class: Type[MetricCollector]) -> None:
    """Register a custom metric collector."""
    _registry.register(name, collector_class)


def get_metric_registry() -> MetricRegistry:
    """Get the global metric registry."""
    return _registry


# Register built-in metrics
from .timing import CPUTimeCollector, WallTimeCollector
from .memory import ProcessMemoryCollector, TraceMallocCollector
from .io import IOCollector
from .cpu import CPUCollector

_registry.register("wall_time", WallTimeCollector)
_registry.register("cpu_time", CPUTimeCollector)
_registry.register("python_memory", TraceMallocCollector)
_registry.register("process_memory", ProcessMemoryCollector)
_registry.register("disk_io", IOCollector)
_registry.register("cpu_usage", CPUCollector)
