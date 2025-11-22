"""Data models for benchmark storage."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class Environment:
    """System environment metadata."""

    environment_id: Optional[int]
    python_version: str
    platform: str
    processor: str
    cpu_count: int
    memory_total: int
    hostname: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkRun:
    """Benchmark run metadata."""

    run_id: Optional[int]
    timestamp: datetime
    git_commit_hash: Optional[str]
    git_branch: Optional[str]
    git_is_dirty: bool
    environment_id: int
    configurations: Dict[str, str] = field(default_factory=dict)


@dataclass
class Benchmark:
    """Benchmark definition."""

    benchmark_id: Optional[int]
    name: str
    description: Optional[str]
    benchmark_type: str  # 'function' or 'shell'
    category: Optional[str]
    created_at: datetime


@dataclass
class Measurement:
    """Single measurement."""

    measurement_id: Optional[int]
    run_id: int
    benchmark_id: int
    iteration: int
    wall_time: Optional[float]
    cpu_time: Optional[float]
    peak_memory: Optional[int]
    current_memory: Optional[int]
    read_bytes: Optional[int]
    write_bytes: Optional[int]
    exit_code: Optional[int]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkStatistics:
    """Aggregated statistics for a benchmark run."""

    stat_id: Optional[int]
    run_id: int
    benchmark_id: int
    sample_count: int
    mean_wall_time: float
    median_wall_time: float
    stddev_wall_time: float
    min_wall_time: float
    max_wall_time: float
    p95_wall_time: float
    p99_wall_time: float
    mean_cpu_time: Optional[float]
    mean_memory: Optional[int]
    peak_memory: Optional[int]
    total_read_bytes: Optional[int]
    total_write_bytes: Optional[int]


@dataclass
class BenchmarkComparison:
    """Comparison between two benchmark runs."""

    comparison_id: Optional[int]
    baseline_run_id: int
    comparison_run_id: int
    benchmark_id: int
    speedup_factor: float
    memory_ratio: float
    is_significant: bool
    p_value: float
    created_at: datetime
