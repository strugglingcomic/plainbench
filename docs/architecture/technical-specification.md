# PlainBench Technical Specification

**Version:** 1.0
**Date:** 2025-11-22
**Status:** Design Phase

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Components](#core-components)
3. [API Design](#api-design)
4. [Data Models](#data-models)
5. [Extension Points](#extension-points)
6. [Implementation Phases](#implementation-phases)
7. [Performance Considerations](#performance-considerations)
8. [Platform Support](#platform-support)

---

## System Overview

### Purpose

PlainBench is a Python benchmarking framework designed to provide:
- **Fine-grained benchmarking** of Python functions via decorators
- **Black-box benchmarking** of shell commands
- **Multiple metrics**: timing, CPU usage, memory, disk I/O
- **SQLite-backed storage** for historical analysis and comparisons
- **Configurable isolation** strategies for reproducible results
- **Statistical analysis** with significance testing

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      PlainBench CLI                         │
│  (run, compare, show, export, init)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
     ┌───────────────┴───────────────┐
     │                               │
┌────▼─────┐                   ┌────▼──────┐
│ Decorator│                   │   Shell   │
│  System  │                   │  Runner   │
└────┬─────┘                   └────┬──────┘
     │                               │
     └───────────────┬───────────────┘
                     │
            ┌────────▼─────────┐
            │ Metrics Collectors│
            │ - Timing          │
            │ - Memory          │
            │ - CPU             │
            │ - I/O             │
            └────────┬──────────┘
                     │
            ┌────────▼─────────┐
            │ Isolation Layer   │
            │ (Minimal/Moderate/│
            │     Maximum)      │
            └────────┬──────────┘
                     │
     ┌───────────────┴────────────────┐
     │                                │
┌────▼─────┐                   ┌─────▼──────┐
│ Storage  │                   │  Analysis  │
│ (SQLite) │◄──────────────────┤  Engine    │
│          │                   │            │
└──────────┘                   └────────────┘
```

### Key Design Principles

1. **Minimal Overhead**: Measurement overhead should be negligible compared to execution time
2. **Extensible**: Easy to add custom metrics and isolation strategies
3. **Type-Safe**: Use type hints and dataclasses throughout
4. **Platform-Aware**: Graceful degradation on platforms with limited features
5. **Statistical Rigor**: Proper warmup, multiple runs, and statistical testing
6. **Reproducible**: Capture environment metadata for reproducibility

---

## Core Components

### 1. Metrics Collectors

#### 1.1 Base Metric Collector

**File:** `plainbench/metrics/base.py`

```python
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
```

**Rationale:** Based on research, this lifecycle (setup → start → stop → cleanup) provides:
- Clean separation of setup overhead from measurement
- Resource management (tracemalloc, psutil handles)
- Platform detection

#### 1.2 Timing Collector

**File:** `plainbench/metrics/timing.py`

```python
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
        return MetricResult(
            name=self.name,
            value=elapsed,
            unit="seconds"
        )

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
        return MetricResult(
            name=self.name,
            value=elapsed,
            unit="seconds"
        )

    def cleanup(self) -> None:
        self._start_time = None

    def is_available(self) -> bool:
        return True
```

**Design Decision:** Use `time.perf_counter()` for wall time (research recommendation) and `time.process_time()` for CPU time.

#### 1.3 Memory Collector

**File:** `plainbench/metrics/memory.py`

```python
import tracemalloc
import psutil
import os
from typing import Optional, Tuple
from .base import MetricCollector, MetricResult


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
                "delta": current - self._initial_memory
            }
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
        self._process: Optional[psutil.Process] = None
        self._initial_rss: Optional[int] = None
        self._peak_rss: int = 0

    @property
    def name(self) -> str:
        return "process_memory"

    def setup(self) -> None:
        self._process = psutil.Process(os.getpid())

    def start(self) -> None:
        mem_info = self._process.memory_info()
        self._initial_rss = mem_info.rss
        self._peak_rss = mem_info.rss

    def stop(self) -> MetricResult:
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
                "delta": final_rss - self._initial_rss
            }
        )

    def cleanup(self) -> None:
        self._process = None
        self._initial_rss = None
        self._peak_rss = 0

    def is_available(self) -> bool:
        try:
            import psutil
            return True
        except ImportError:
            return False
```

**Design Decision:** Provide both tracemalloc (Python heap) and psutil (total process) collectors, as they serve different purposes (research finding).

#### 1.4 I/O Collector

**File:** `plainbench/metrics/io.py`

```python
import psutil
import os
from typing import Optional
from .base import MetricCollector, MetricResult


class IOCollector(MetricCollector):
    """Collects disk I/O metrics using psutil."""

    def __init__(self):
        self._process: Optional[psutil.Process] = None
        self._initial_io = None

    @property
    def name(self) -> str:
        return "disk_io"

    def setup(self) -> None:
        self._process = psutil.Process(os.getpid())

    def start(self) -> None:
        try:
            self._initial_io = self._process.io_counters()
        except (AttributeError, OSError):
            # Not available on this platform
            self._initial_io = None

    def stop(self) -> MetricResult:
        if self._initial_io is None:
            return MetricResult(
                name=self.name,
                value=None,
                unit="bytes",
                metadata={"available": False}
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
                }
            )
        except (AttributeError, OSError):
            return MetricResult(
                name=self.name,
                value=None,
                unit="bytes",
                metadata={"available": False}
            )

    def cleanup(self) -> None:
        self._process = None
        self._initial_io = None

    def is_available(self) -> bool:
        """Check if I/O counters are available on this platform."""
        try:
            process = psutil.Process(os.getpid())
            process.io_counters()
            return True
        except (AttributeError, OSError):
            return False  # Not available on macOS, limited on Windows
```

**Platform Handling:** Research shows I/O counters are fully available on Linux, limited elsewhere. This implementation handles unavailability gracefully.

#### 1.5 Metric Registry

**File:** `plainbench/metrics/registry.py`

```python
from typing import Dict, Type, List
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
```

**Extension Point:** Users can register custom metrics via `register_metric()`.

### 2. Decorator System

**File:** `plainbench/decorators/benchmark.py`

```python
import functools
import gc
from typing import Callable, List, Optional, Any
from dataclasses import dataclass
from ..metrics.registry import get_metric_registry
from ..storage.database import BenchmarkDatabase
from ..storage.models import BenchmarkRun, Measurement
from ..isolation.factory import create_isolation_strategy
from ..config.settings import BenchmarkConfig


def benchmark(
    name: Optional[str] = None,
    warmup: int = 3,
    runs: int = 10,
    metrics: Optional[List[str]] = None,
    isolation: str = "minimal",
    disable_gc: bool = True,
    store: bool = True,
    database: Optional[str] = None,
    **kwargs
) -> Callable:
    """
    Decorator for benchmarking Python functions.

    Args:
        name: Benchmark name (defaults to function name)
        warmup: Number of warmup iterations
        runs: Number of measurement iterations
        metrics: List of metrics to collect (default: ['wall_time', 'cpu_time', 'python_memory'])
        isolation: Isolation strategy ('minimal', 'moderate', 'maximum')
        disable_gc: Disable garbage collection during measurement
        store: Store results in database
        database: Database path (default: from config)
        **kwargs: Additional configuration options

    Example:
        @benchmark(warmup=5, runs=20, metrics=['wall_time', 'python_memory'])
        def my_function(n):
            return sum(range(n))
    """

    def decorator(func: Callable) -> Callable:
        benchmark_name = name or func.__name__

        # Default metrics
        if metrics is None:
            metric_names = ['wall_time', 'cpu_time', 'python_memory']
        else:
            metric_names = metrics

        @functools.wraps(func)
        def wrapper(*args, **func_kwargs) -> Any:
            # Create metric collectors
            registry = get_metric_registry()
            collectors = registry.create_collectors(metric_names)

            # Setup collectors
            for collector in collectors:
                collector.setup()

            # Warmup phase
            for _ in range(warmup):
                func(*args, **func_kwargs)

            # Measurement phase
            measurements = []

            for iteration in range(runs):
                # Disable GC if requested
                if disable_gc:
                    gc.collect()
                    gc.disable()

                try:
                    # Start metrics
                    for collector in collectors:
                        collector.start()

                    # Execute function
                    result = func(*args, **func_kwargs)

                    # Stop metrics
                    metric_results = {}
                    for collector in collectors:
                        metric_result = collector.stop()
                        metric_results[metric_result.name] = metric_result

                    measurements.append(metric_results)

                finally:
                    if disable_gc:
                        gc.enable()

            # Cleanup collectors
            for collector in collectors:
                collector.cleanup()

            # Store results if requested
            if store:
                db_path = database or BenchmarkConfig.get_default_database()
                db = BenchmarkDatabase(db_path)
                db.store_benchmark_results(
                    benchmark_name=benchmark_name,
                    measurements=measurements,
                    metadata={
                        'warmup': warmup,
                        'runs': runs,
                        'isolation': isolation,
                        'disable_gc': disable_gc,
                    }
                )

            return result

        # Attach metadata for introspection
        wrapper._is_benchmark = True
        wrapper._benchmark_name = benchmark_name
        wrapper._benchmark_config = {
            'warmup': warmup,
            'runs': runs,
            'metrics': metric_names,
            'isolation': isolation,
        }

        return wrapper

    return decorator
```

**Key Features:**
- Based on research best practices (warmup, GC control, multiple runs)
- Configurable metrics via registry
- Automatic database persistence
- Minimal overhead (single function call + metrics)

### 3. Shell Command Runner

**File:** `plainbench/shell/runner.py`

```python
import subprocess
import psutil
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from ..metrics.base import MetricResult


@dataclass
class ShellBenchmarkResult:
    """Result from benchmarking a shell command."""
    command: str
    exit_code: int
    wall_time: float
    stdout: Optional[str]
    stderr: Optional[str]
    metrics: Dict[str, MetricResult]
    iterations: int


def benchmark_shell(
    command: str,
    warmup: int = 1,
    runs: int = 5,
    metrics: Optional[List[str]] = None,
    capture_output: bool = False,
    timeout: Optional[float] = None,
    shell: bool = True,
    monitoring_interval: float = 0.1,
) -> ShellBenchmarkResult:
    """
    Benchmark a shell command.

    Args:
        command: Shell command to execute
        warmup: Number of warmup executions
        runs: Number of measurement executions
        metrics: Metrics to collect (default: ['wall_time', 'peak_memory', 'io'])
        capture_output: Capture stdout/stderr
        timeout: Command timeout in seconds
        shell: Execute via shell
        monitoring_interval: Sampling interval for continuous monitoring

    Returns:
        ShellBenchmarkResult with aggregated metrics

    Example:
        result = benchmark_shell(
            'sqlite3 test.db "SELECT * FROM users LIMIT 1000"',
            runs=10,
            metrics=['wall_time', 'peak_memory', 'io']
        )
    """

    if metrics is None:
        metrics = ['wall_time', 'peak_memory', 'io']

    # Warmup
    for _ in range(warmup):
        subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            timeout=timeout
        )

    # Measurements
    all_measurements = []

    for _ in range(runs):
        measurement = _run_and_measure(
            command=command,
            capture_output=capture_output,
            timeout=timeout,
            shell=shell,
            monitoring_interval=monitoring_interval,
            metrics=metrics
        )
        all_measurements.append(measurement)

    # Aggregate results
    aggregated_metrics = _aggregate_measurements(all_measurements)

    # Get last run's output for reference
    last_measurement = all_measurements[-1]

    return ShellBenchmarkResult(
        command=command,
        exit_code=last_measurement['exit_code'],
        wall_time=aggregated_metrics['wall_time']['mean'],
        stdout=last_measurement.get('stdout'),
        stderr=last_measurement.get('stderr'),
        metrics=aggregated_metrics,
        iterations=runs
    )


def _run_and_measure(
    command: str,
    capture_output: bool,
    timeout: Optional[float],
    shell: bool,
    monitoring_interval: float,
    metrics: List[str]
) -> Dict[str, Any]:
    """Run command once and collect metrics."""

    # Start process
    start_time = time.perf_counter()

    proc = subprocess.Popen(
        command,
        shell=shell,
        stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
        stderr=subprocess.PIPE if capture_output else subprocess.DEVNULL,
    )

    # Monitor with psutil
    ps_proc = psutil.Process(proc.pid)

    peak_memory = 0
    io_start = None
    io_end = None

    # Get initial I/O if available
    try:
        io_start = ps_proc.io_counters()
    except (AttributeError, psutil.NoSuchProcess):
        io_start = None

    # Monitor while running
    while proc.poll() is None:
        try:
            mem = ps_proc.memory_info().rss
            peak_memory = max(peak_memory, mem)

            # Check timeout
            if timeout and (time.perf_counter() - start_time) > timeout:
                proc.kill()
                raise subprocess.TimeoutExpired(command, timeout)

            time.sleep(monitoring_interval)
        except psutil.NoSuchProcess:
            break

    # Get final I/O if available
    try:
        io_end = ps_proc.io_counters()
    except (AttributeError, psutil.NoSuchProcess):
        io_end = None

    end_time = time.perf_counter()
    wall_time = end_time - start_time

    # Get output
    stdout, stderr = proc.communicate()

    # Build measurement
    measurement = {
        'exit_code': proc.returncode,
        'wall_time': wall_time,
        'peak_memory': peak_memory,
    }

    if capture_output:
        measurement['stdout'] = stdout.decode('utf-8', errors='replace')
        measurement['stderr'] = stderr.decode('utf-8', errors='replace')

    if io_start and io_end:
        measurement['read_bytes'] = io_end.read_bytes - io_start.read_bytes
        measurement['write_bytes'] = io_end.write_bytes - io_start.write_bytes

    return measurement


def _aggregate_measurements(measurements: List[Dict[str, Any]]) -> Dict[str, Dict]:
    """Aggregate measurements into statistics."""
    import statistics

    aggregated = {}

    # Collect all numeric metrics
    metric_values = {}
    for measurement in measurements:
        for key, value in measurement.items():
            if isinstance(value, (int, float)):
                if key not in metric_values:
                    metric_values[key] = []
                metric_values[key].append(value)

    # Calculate statistics
    for metric_name, values in metric_values.items():
        aggregated[metric_name] = {
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0,
            'min': min(values),
            'max': max(values),
        }

    return aggregated
```

**Design Decision:** Based on research, use psutil for cross-platform monitoring with continuous sampling to capture peak memory.

### 4. Isolation Strategies

**File:** `plainbench/isolation/base.py`

```python
from abc import ABC, abstractmethod
from typing import Callable, Any, Dict


class IsolationStrategy(ABC):
    """Abstract base class for isolation strategies."""

    @abstractmethod
    def apply(self) -> None:
        """Apply isolation settings."""
        pass

    @abstractmethod
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with isolation."""
        pass

    @abstractmethod
    def restore(self) -> None:
        """Restore original settings."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about isolation configuration."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if isolation strategy is available."""
        pass
```

**File:** `plainbench/isolation/moderate.py`

```python
import os
import gc
import psutil
from typing import Callable, Any, Dict, Optional, List
from .base import IsolationStrategy


class ModerateIsolation(IsolationStrategy):
    """
    Moderate isolation strategy.

    Features:
    - CPU pinning to specific cores
    - Disable garbage collection
    - Set PYTHONHASHSEED for reproducibility
    """

    def __init__(self, cpu_affinity: Optional[List[int]] = None):
        self._cpu_affinity = cpu_affinity or [0, 1]
        self._original_affinity: Optional[List[int]] = None
        self._gc_was_enabled: bool = False
        self._original_hashseed: Optional[str] = None

    def apply(self) -> None:
        """Apply moderate isolation settings."""
        # Save original settings
        try:
            process = psutil.Process()
            self._original_affinity = process.cpu_affinity()
            # Set CPU affinity
            process.cpu_affinity(self._cpu_affinity)
        except (AttributeError, OSError):
            # CPU affinity not supported on this platform
            pass

        # Set Python hash seed for reproducibility
        self._original_hashseed = os.environ.get('PYTHONHASHSEED')
        os.environ['PYTHONHASHSEED'] = '0'

        # Disable GC
        self._gc_was_enabled = gc.isenabled()
        gc.collect()
        gc.disable()

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with isolation applied."""
        return func(*args, **kwargs)

    def restore(self) -> None:
        """Restore original settings."""
        # Restore CPU affinity
        if self._original_affinity is not None:
            try:
                process = psutil.Process()
                process.cpu_affinity(self._original_affinity)
            except (AttributeError, OSError):
                pass

        # Restore hash seed
        if self._original_hashseed is not None:
            os.environ['PYTHONHASHSEED'] = self._original_hashseed
        else:
            os.environ.pop('PYTHONHASHSEED', None)

        # Restore GC
        if self._gc_was_enabled:
            gc.enable()

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about isolation configuration."""
        return {
            'strategy': 'moderate',
            'cpu_affinity': self._cpu_affinity,
            'gc_disabled': not self._gc_was_enabled,
            'pythonhashseed': '0',
        }

    def is_available(self) -> bool:
        """Check if moderate isolation is available."""
        return True  # Always available, gracefully degrades
```

**Rationale:** Based on research recommendations for local development benchmarking.

### 5. SQLite Storage

**File:** `plainbench/storage/schema.py`

```python
"""SQLite database schema for PlainBench."""

# Schema version for migrations
SCHEMA_VERSION = 1

CREATE_TABLES = """
-- Environments: system metadata
CREATE TABLE IF NOT EXISTS environments (
    environment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    python_version TEXT NOT NULL,
    platform TEXT NOT NULL,
    processor TEXT,
    cpu_count INTEGER,
    memory_total INTEGER,
    hostname TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT
);

-- Benchmark runs: execution metadata
CREATE TABLE IF NOT EXISTS benchmark_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    git_commit_hash TEXT,
    git_branch TEXT,
    git_is_dirty BOOLEAN,
    environment_id INTEGER NOT NULL,
    FOREIGN KEY (environment_id) REFERENCES environments(environment_id)
);

-- Benchmarks: benchmark definitions
CREATE TABLE IF NOT EXISTS benchmarks (
    benchmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    benchmark_type TEXT NOT NULL,  -- 'function' or 'shell'
    category TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Measurements: raw measurement data
CREATE TABLE IF NOT EXISTS measurements (
    measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    benchmark_id INTEGER NOT NULL,
    iteration INTEGER NOT NULL,
    wall_time REAL,
    cpu_time REAL,
    peak_memory INTEGER,
    current_memory INTEGER,
    read_bytes INTEGER,
    write_bytes INTEGER,
    exit_code INTEGER,
    metadata_json TEXT,
    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(benchmark_id)
);

-- Benchmark statistics: pre-computed aggregates
CREATE TABLE IF NOT EXISTS benchmark_statistics (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    benchmark_id INTEGER NOT NULL,
    sample_count INTEGER NOT NULL,
    mean_wall_time REAL,
    median_wall_time REAL,
    stddev_wall_time REAL,
    min_wall_time REAL,
    max_wall_time REAL,
    p95_wall_time REAL,
    p99_wall_time REAL,
    mean_cpu_time REAL,
    mean_memory INTEGER,
    peak_memory INTEGER,
    total_read_bytes INTEGER,
    total_write_bytes INTEGER,
    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(benchmark_id),
    UNIQUE(run_id, benchmark_id)
);

-- Configurations: benchmark configuration
CREATE TABLE IF NOT EXISTS configurations (
    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id)
);

-- Benchmark comparisons: stored comparisons
CREATE TABLE IF NOT EXISTS benchmark_comparisons (
    comparison_id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseline_run_id INTEGER NOT NULL,
    comparison_run_id INTEGER NOT NULL,
    benchmark_id INTEGER NOT NULL,
    speedup_factor REAL,
    memory_ratio REAL,
    is_significant BOOLEAN,
    p_value REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (baseline_run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (comparison_run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(benchmark_id)
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES = """
-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_measurements_run
    ON measurements(run_id);

CREATE INDEX IF NOT EXISTS idx_measurements_benchmark
    ON measurements(benchmark_id);

CREATE INDEX IF NOT EXISTS idx_measurements_run_benchmark
    ON measurements(run_id, benchmark_id);

CREATE INDEX IF NOT EXISTS idx_benchmark_runs_timestamp
    ON benchmark_runs(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_benchmark_runs_git_branch
    ON benchmark_runs(git_branch);

CREATE INDEX IF NOT EXISTS idx_configurations_run
    ON configurations(run_id);

CREATE INDEX IF NOT EXISTS idx_comparisons_runs
    ON benchmark_comparisons(baseline_run_id, comparison_run_id);
"""
```

**Design Decision:** Schema based on research findings for storing both raw measurements and pre-computed statistics for query performance.

---

## API Design

### Python Decorator API

```python
from plainbench import benchmark

# Basic usage
@benchmark()
def sort_list(n):
    return sorted([n - i for i in range(n)])

# Custom configuration
@benchmark(
    name="custom_sort",
    warmup=5,
    runs=20,
    metrics=['wall_time', 'python_memory', 'cpu_time'],
    isolation='moderate',
    disable_gc=True
)
def optimized_sort(n):
    return sorted([n - i for i in range(n)])

# Multiple metrics
@benchmark(metrics=['wall_time', 'python_memory', 'process_memory', 'disk_io'])
def process_data():
    # ... implementation
    pass
```

### Shell Command API

```python
from plainbench import benchmark_shell

# Basic usage
result = benchmark_shell('ls -la')

# With configuration
result = benchmark_shell(
    command='sqlite3 test.db < queries.sql',
    warmup=2,
    runs=10,
    metrics=['wall_time', 'peak_memory', 'io'],
    capture_output=True,
    timeout=30.0
)

print(f"Mean time: {result.wall_time:.3f}s")
print(f"Exit code: {result.exit_code}")
```

### Configuration API

```python
from plainbench.config import BenchmarkConfig

# Load from file
config = BenchmarkConfig.from_file('plainbench.yaml')

# Programmatic configuration
config = BenchmarkConfig(
    default_warmup=3,
    default_runs=10,
    default_isolation='moderate',
    database_path='./benchmarks.db',
    cpu_affinity=[0, 1, 2, 3],
    regression_threshold=0.05
)

# Use configuration
@benchmark(config=config)
def my_function():
    pass
```

### Query and Comparison API

```python
from plainbench import BenchmarkDatabase
from plainbench.analysis import compare_runs, detect_regressions

# Open database
db = BenchmarkDatabase('./benchmarks.db')

# Get latest results
latest = db.get_latest_run()
print(latest.benchmarks)

# Compare two runs
comparison = compare_runs(
    baseline_run_id=1,
    current_run_id=2,
    database=db
)

for result in comparison:
    print(f"{result.name}: {result.speedup:.2f}x")

# Detect regressions
regressions = detect_regressions(
    baseline_run_id=1,
    current_run_id=2,
    threshold=0.05,  # 5% slowdown threshold
    database=db
)

if regressions:
    print("Performance regressions detected:")
    for reg in regressions:
        print(f"  {reg.name}: {reg.slowdown_pct:.1f}% slower")
```

### CLI Command Structure

```bash
# Run benchmarks
plainbench run                          # Run all benchmarks in current directory
plainbench run tests/benchmarks/        # Run specific directory
plainbench run -k "test_sort"          # Run matching pattern
plainbench run --isolation=maximum      # Use maximum isolation

# Compare results
plainbench compare --baseline=main --current=HEAD
plainbench compare --baseline-run=1 --current-run=2
plainbench compare --show-only-regressions

# Show results
plainbench show                         # Show latest run
plainbench show --run-id=5             # Show specific run
plainbench show --benchmark="sort_list" # Show specific benchmark history

# Export results
plainbench export --format=json --output=results.json
plainbench export --format=csv --run-id=5
plainbench export --format=html --output=report.html

# Initialize
plainbench init                         # Create example benchmark suite
plainbench init --template=queue        # Use specific template
```

---

## Data Models

**File:** `plainbench/storage/models.py`

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime


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
```

---

## Extension Points

### 1. Custom Metrics

Users can add custom metric collectors:

```python
from plainbench.metrics import MetricCollector, MetricResult, register_metric

class NetworkIOCollector(MetricCollector):
    """Custom collector for network I/O."""

    @property
    def name(self) -> str:
        return "network_io"

    def setup(self) -> None:
        # Initialize network monitoring
        pass

    def start(self) -> None:
        # Start capturing network I/O
        pass

    def stop(self) -> MetricResult:
        # Return network I/O measurements
        return MetricResult(
            name=self.name,
            value=12345,
            unit="bytes"
        )

    def cleanup(self) -> None:
        pass

    def is_available(self) -> bool:
        return True

# Register custom metric
register_metric('network_io', NetworkIOCollector)

# Use in benchmarks
@benchmark(metrics=['wall_time', 'network_io'])
def api_call():
    # Make API call
    pass
```

### 2. Custom Isolation Strategies

```python
from plainbench.isolation import IsolationStrategy, register_isolation

class CustomIsolation(IsolationStrategy):
    """Custom isolation strategy."""

    def apply(self) -> None:
        # Apply custom isolation
        pass

    def execute(self, func, *args, **kwargs):
        # Execute with isolation
        return func(*args, **kwargs)

    def restore(self) -> None:
        # Restore settings
        pass

    def get_metadata(self) -> Dict[str, Any]:
        return {'strategy': 'custom'}

    def is_available(self) -> bool:
        return True

# Register and use
register_isolation('custom', CustomIsolation)

@benchmark(isolation='custom')
def my_function():
    pass
```

### 3. Custom Storage Backends (Future)

```python
from plainbench.storage import StorageBackend

class PostgreSQLBackend(StorageBackend):
    """PostgreSQL storage backend."""

    def store_benchmark(self, benchmark):
        # Store in PostgreSQL
        pass

    def query_benchmarks(self, filters):
        # Query PostgreSQL
        pass
```

---

## Implementation Phases

### Phase 0: Core Infrastructure (Weeks 1-2)
**Goal:** Foundational components

- [ ] Project setup (pyproject.toml, directory structure)
- [ ] Base metric collector interface
- [ ] Timing collectors (wall_time, cpu_time)
- [ ] Basic SQLite storage (schema, database class)
- [ ] Data models (dataclasses)
- [ ] Unit tests for core components

**Deliverables:**
- Working timing metrics
- SQLite database with schema
- Basic storage/retrieval

### Phase 1: Decorator System (Weeks 3-4)
**Goal:** Python function benchmarking

- [ ] @benchmark decorator implementation
- [ ] Memory collectors (tracemalloc, psutil)
- [ ] Metric registry system
- [ ] Warmup and multiple runs
- [ ] GC control integration
- [ ] Integration tests

**Deliverables:**
- Fully functional @benchmark decorator
- All core metrics working
- Examples directory with basic usage

### Phase 2: Shell Command Support (Weeks 5-6)
**Goal:** Black-box shell command benchmarking

- [ ] Shell runner implementation
- [ ] Process monitoring with psutil
- [ ] Resource module integration (Unix)
- [ ] Continuous vs. snapshot monitoring
- [ ] I/O metrics collector
- [ ] Platform-specific handling

**Deliverables:**
- benchmark_shell() function
- Cross-platform support
- Examples for shell commands

### Phase 3: Isolation Strategies (Week 7)
**Goal:** Reproducible benchmarking

- [ ] Isolation strategy interface
- [ ] Minimal isolation (subprocess)
- [ ] Moderate isolation (CPU pinning, GC)
- [ ] Maximum isolation (Docker/cgroups)
- [ ] Factory pattern for strategy selection
- [ ] Platform detection

**Deliverables:**
- Three isolation levels working
- Configuration options
- Documentation on isolation

### Phase 4: Analysis and Comparison (Weeks 8-9)
**Goal:** Statistical analysis and comparison

- [ ] Statistical computations (mean, median, stddev, percentiles)
- [ ] Pre-computed statistics storage
- [ ] Benchmark comparison with t-tests
- [ ] Regression detection
- [ ] Trend analysis queries
- [ ] Export functionality (JSON, CSV, HTML)

**Deliverables:**
- Analysis module
- Comparison functions
- Export formats

### Phase 5: CLI and Configuration (Weeks 10-11)
**Goal:** User-friendly interface

- [ ] CLI with Click
- [ ] Commands: run, compare, show, export, init
- [ ] Configuration file support (YAML/TOML)
- [ ] Environment metadata collection
- [ ] Git integration
- [ ] Pretty formatting for terminal
- [ ] Progress indicators

**Deliverables:**
- Complete CLI
- Configuration system
- User documentation

### Phase 6: Documentation and Examples (Week 12)
**Goal:** Production-ready release

- [ ] API documentation
- [ ] User guides
- [ ] Best practices guide
- [ ] Advanced examples (queue benchmark, algorithm comparison)
- [ ] CI/CD setup
- [ ] PyPI package preparation
- [ ] README and CONTRIBUTING guides

**Deliverables:**
- Complete documentation
- Published package
- Example projects

---

## Performance Considerations

### Measurement Overhead

**Target:** < 1% overhead for functions running > 100ms

**Strategies:**
1. Use lightweight timing functions (`time.perf_counter()`)
2. Minimize state capture
3. Disable unnecessary metrics
4. Use efficient data structures
5. Profile the profiler

### Database Performance

**SQLite Optimizations:**
```sql
-- WAL mode for concurrent reads
PRAGMA journal_mode=WAL;

-- Memory cache
PRAGMA cache_size=-64000;  -- 64MB

-- Synchronous mode
PRAGMA synchronous=NORMAL;

-- Batch inserts
BEGIN TRANSACTION;
-- Multiple INSERTs
COMMIT;
```

**Based on research:** These settings can provide 100x+ performance improvements for write-heavy workloads.

### Memory Usage

**Strategies:**
1. Stream large result sets
2. Use database cursors
3. Limit in-memory aggregation
4. Cleanup collectors after use

---

## Platform Support

### Primary Platform: Linux
- Full support for all features
- I/O metrics via psutil
- cgroups support for maximum isolation
- CPU pinning

### Secondary Platform: macOS
- Full timing and memory support
- Limited I/O metrics
- CPU pinning supported
- No cgroups (use Docker)

### Limited Platform: Windows
- Timing and memory support
- Partial I/O metrics
- Limited CPU pinning
- No cgroups (use Docker on WSL2)

### Graceful Degradation
```python
if not collector.is_available():
    logger.warning(f"Metric '{collector.name}' not available on this platform")
    # Skip collector
```

---

**End of Technical Specification**
