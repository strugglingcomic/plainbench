"""Base metric collector interface and result dataclass."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class MetricResult:
    """Result from a single metric measurement."""

    name: str
    value: Any
    unit: str
    metadata: Optional[dict] = None


class MetricCollector(ABC):
    """Abstract base class for metric collectors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the metric."""
        pass

    @abstractmethod
    def setup(self) -> None:
        """Setup before measurement (e.g., start tracemalloc)."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Start measurement (called just before execution)."""
        pass

    @abstractmethod
    def stop(self) -> MetricResult:
        """Stop measurement and return result."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup after measurement."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if metric is available on current platform."""
        pass
