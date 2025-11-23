"""
Data structures for shell command benchmark results.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union


@dataclass
class ShellCommandResult:
    """Result from a single shell command execution."""

    command: Union[str, List[str]]
    exit_code: int
    wall_time: float
    stdout: Optional[str] = None
    stderr: Optional[str] = None

    # Resource metrics
    peak_memory: Optional[int] = None  # Peak RSS in bytes
    cpu_percent: Optional[float] = None
    read_bytes: Optional[int] = None
    write_bytes: Optional[int] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ShellBenchmarkResult:
    """Aggregated results from benchmarking a shell command."""

    command: Union[str, List[str]]
    exit_code: int
    iterations: int

    # Timing statistics
    mean_time: float
    median_time: float
    stddev_time: float
    min_time: float
    max_time: float

    # Memory statistics (in bytes)
    mean_memory: Optional[int] = None
    peak_memory: Optional[int] = None

    # I/O statistics (in bytes)
    total_read_bytes: Optional[int] = None
    total_write_bytes: Optional[int] = None

    # Output from last run
    stdout: Optional[str] = None
    stderr: Optional[str] = None

    # Raw measurements
    raw_measurements: List[ShellCommandResult] = field(default_factory=list)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
