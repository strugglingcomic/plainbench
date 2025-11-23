# PlainBench User Guide

**Complete guide to using PlainBench for Python and shell command benchmarking**

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Decorator System](#decorator-system)
4. [Shell Command Benchmarking](#shell-command-benchmarking)
5. [Isolation Strategies](#isolation-strategies)
6. [Database Operations](#database-operations)
7. [Statistical Analysis](#statistical-analysis)
8. [Best Practices](#best-practices)
9. [Advanced Topics](#advanced-topics)
10. [Troubleshooting](#troubleshooting)

---

## Introduction

PlainBench is a comprehensive Python benchmarking framework designed for:

- **Function benchmarking** via decorators with minimal overhead
- **Shell command benchmarking** with process monitoring
- **Historical tracking** in SQLite database
- **Statistical analysis** with significance testing
- **Reproducible results** with multiple isolation levels

### Key Features

- Zero infrastructure - single SQLite database file
- Comprehensive metrics (timing, memory, CPU, I/O)
- Three-tier isolation strategy for reproducibility
- Built-in statistical analysis and regression detection
- Platform-aware with graceful degradation

---

## Installation

### From Source

```bash
git clone https://github.com/yourusername/plainbench.git
cd plainbench
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

This includes testing and development dependencies:
- pytest
- pytest-cov
- black
- ruff
- mypy

### Requirements

- Python 3.8+
- SQLite 3 (included with Python)
- psutil (for process metrics)
- pydantic (for configuration)

---

## Decorator System

The `@benchmark` decorator is the primary way to benchmark Python functions.

### Basic Usage

```python
from plainbench import benchmark

@benchmark()
def my_function(n):
    return sum(range(n))

result = my_function(1000000)  # Function runs normally, data saved
```

### Decorator Parameters

```python
@benchmark(
    name: Optional[str] = None,           # Benchmark name (default: function name)
    warmup: int = 3,                      # Warmup iterations
    runs: int = 10,                       # Measurement iterations
    metrics: List[str] = None,            # Metrics to collect
    isolation: str = 'minimal',           # Isolation level
    disable_gc: bool = True,              # Disable GC during measurement
    database: str = './benchmarks.db'     # Database location
)
```

### Examples

#### Custom Warmup and Runs

```python
@benchmark(warmup=5, runs=20)
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

#### Custom Metrics

```python
@benchmark(
    metrics=['wall_time', 'python_memory', 'disk_io']
)
def file_processing():
    with open('data.txt', 'w') as f:
        f.write('x' * 1000000)
```

#### Named Benchmarks

```python
@benchmark(name="sort_builtin_v1")
def sort_data(data):
    return sorted(data)

# Later, update implementation
@benchmark(name="sort_builtin_v2")
def sort_data_v2(data):
    return sorted(data, key=lambda x: x)

# Compare v1 vs v2 in database
```

#### Custom Database

```python
@benchmark(database="./my_project_benchmarks.db")
def my_benchmark():
    # Separate database for this project
    pass
```

### Available Metrics

| Metric | Description | Platform Support |
|--------|-------------|------------------|
| `wall_time` | Total elapsed time (monotonic clock) | All |
| `cpu_time` | CPU time (excludes I/O wait) | All |
| `python_memory` | Python heap memory via tracemalloc | All |
| `process_memory` | Total process memory (RSS) | All |
| `disk_io` | Disk read/write operations | Linux (full), others (limited) |
| `cpu_usage` | CPU utilization percentage | All |

**Default metrics:** `['wall_time', 'cpu_time', 'python_memory']`

### How It Works

1. **Warmup Phase**: Function runs `warmup` times to warm up caches and JIT
2. **Measurement Phase**: Function runs `runs` times with metrics collected
3. **Statistics Computation**: Mean, median, stddev, percentiles calculated
4. **Storage**: Results saved to SQLite database with metadata

### Decorator Behavior

The decorated function:
- Returns the same value as the original function
- Can be called multiple times (each call creates a new benchmark run)
- Preserves function metadata (name, docstring, signature)
- Can be used with positional and keyword arguments

```python
@benchmark()
def add(a, b):
    """Add two numbers."""
    return a + b

result = add(5, 3)      # Works normally
result = add(a=5, b=3)  # Keyword args work too
print(add.__doc__)       # Docstring preserved
```

---

## Shell Command Benchmarking

Benchmark shell commands and external processes with detailed monitoring.

### Basic Usage

```python
from plainbench.shell import benchmark_shell

result = benchmark_shell(
    command='ls -la',
    warmup=1,
    runs=5
)

print(f"Mean time: {result.statistics.wall_time.mean:.3f}s")
```

### Parameters

```python
benchmark_shell(
    command: Union[str, List[str]],      # Command to execute
    shell: bool = True,                  # Use shell execution
    capture_output: bool = False,        # Capture stdout/stderr
    timeout: Optional[float] = None,     # Timeout in seconds
    warmup: int = 1,                     # Warmup runs
    runs: int = 10,                      # Measurement runs
    monitoring_mode: str = 'snapshot',   # 'snapshot' or 'continuous'
    monitoring_interval: float = 0.1     # Sampling interval (continuous mode)
)
```

### Monitoring Modes

#### Snapshot Mode (Default)

Measures resource usage at start and end only. Fast, minimal overhead.

```python
result = benchmark_shell(
    'find /usr -name "*.py" | wc -l',
    monitoring_mode='snapshot'
)
```

#### Continuous Mode

Samples resource usage at regular intervals during execution.

```python
result = benchmark_shell(
    'python long_script.py',
    monitoring_mode='continuous',
    monitoring_interval=0.05  # Sample every 50ms
)

# Access peak memory usage
print(f"Peak memory: {result.statistics.peak_memory.mean / 1024 / 1024:.2f} MB")
```

### Examples

#### Command with Timeout

```python
result = benchmark_shell(
    'sleep 10',
    timeout=5.0,  # Will timeout after 5 seconds
    runs=3
)
```

#### Capture Output

```python
result = benchmark_shell(
    'echo "Hello World"',
    capture_output=True,
    runs=5
)

# Access output from first run
if result.runs:
    print(f"Output: {result.runs[0].stdout}")
```

#### Compare Commands

```python
# Approach 1
result1 = benchmark_shell('grep -r "pattern" .')

# Approach 2
result2 = benchmark_shell('find . -name "*.py" -exec grep "pattern" {} +')

# Compare
if result1.statistics.wall_time.mean < result2.statistics.wall_time.mean:
    print("grep -r is faster")
else:
    print("find -exec is faster")
```

### Metrics Collected

Shell command benchmarks collect:
- `wall_time`: Total execution time
- `exit_code`: Process exit code
- `peak_memory`: Peak memory usage (continuous mode)
- `cpu_percent`: CPU utilization (continuous mode)
- `io_read`: Bytes read (platform-dependent)
- `io_write`: Bytes written (platform-dependent)

---

## Isolation Strategies

PlainBench provides three isolation levels for reproducible benchmarks.

### Minimal Isolation (Default)

**What it does:**
- Disables garbage collection during measurement
- Basic subprocess isolation

**Use when:**
- Quick development comparisons
- Overhead must be minimal
- Relative performance is more important than absolute

```python
@benchmark(isolation='minimal')
def quick_test():
    return sum(range(10000))
```

### Moderate Isolation (Recommended)

**What it does:**
- Everything in minimal, plus:
- CPU affinity to specific cores
- Process priority adjustment (if permissions allow)
- PYTHONHASHSEED set for hash randomization control
- More comprehensive GC control

**Use when:**
- Running in CI/CD environments
- Need good reproducibility
- Acceptable overhead (~5-10%)

```python
@benchmark(isolation='moderate')
def performance_test():
    return sum(range(10000))
```

**Platform Support:**
- Linux: Full support (CPU pinning, priority)
- macOS: Partial support (no CPU pinning)
- Windows: Partial support (priority only)

### Maximum Isolation

**What it does:**
- Everything in moderate, plus:
- Subprocess execution with clean environment
- Environment variable cleanup
- System state validation
- Comprehensive isolation checks

**Use when:**
- Research and publication
- Critical performance measurements
- Maximum reproducibility required
- Overhead is acceptable (~10-20%)

```python
@benchmark(isolation='maximum')
def critical_benchmark():
    return sum(range(10000))
```

### Comparison Example

See `examples/isolation_comparison.py` for a complete comparison showing how isolation affects variance.

### Choosing Isolation Level

| Use Case | Recommended Level | Reason |
|----------|------------------|---------|
| Development | Minimal | Fast iteration |
| CI/CD | Moderate | Good balance |
| Performance tuning | Moderate | Consistent results |
| Research | Maximum | Best reproducibility |
| A/B testing | Moderate | Fair comparison |
| Production monitoring | Minimal | Low overhead |

---

## Database Operations

All benchmark results are stored in SQLite with comprehensive metadata.

### Database Schema

```
benchmark_runs
├── run_id (PRIMARY KEY)
├── benchmark_name
├── timestamp
├── warmup_runs
├── measurement_runs
├── isolation_level
├── git_commit
├── git_branch
├── git_dirty
└── ... (environment metadata)

measurements
├── run_id (FOREIGN KEY)
├── metric_name
├── value
└── timestamp

benchmark_statistics
├── run_id (FOREIGN KEY)
├── metric_name
├── mean
├── median
├── stddev
├── min
├── max
├── p95
└── p99
```

### Opening Database

```python
from plainbench import BenchmarkDatabase

db = BenchmarkDatabase("./benchmarks.db")
db.initialize()  # Creates schema if needed

# ... operations ...

db.close()
```

### Querying Runs

```python
# Get latest run
latest_run = db.get_latest_run()
print(f"Run {latest_run.run_id}: {latest_run.benchmark_name}")

# Get all runs
all_runs = db.get_all_runs()
for run in all_runs:
    print(f"{run.run_id}: {run.benchmark_name} at {run.timestamp}")

# Get runs with limit
recent_runs = db.get_all_runs(limit=10)

# Get specific run by ID
run = db.get_run(run_id=5)
```

### Querying Measurements

```python
# Get all measurements for a run
measurements = db.get_measurements(run_id=1)

# Group by metric
by_metric = {}
for m in measurements:
    if m.metric_name not in by_metric:
        by_metric[m.metric_name] = []
    by_metric[m.metric_name].append(m.value)

# Analyze
for metric, values in by_metric.items():
    print(f"{metric}: {len(values)} measurements")
```

### Querying Statistics

```python
# Get pre-computed statistics
stats = db.get_statistics(run_id=1)

for stat in stats:
    print(f"{stat.metric_name}:")
    print(f"  Mean: {stat.mean}")
    print(f"  Stddev: {stat.stddev}")
    print(f"  95th percentile: {stat.p95}")
```

### Benchmark History

```python
# Get history for a specific benchmark
history = db.get_benchmark_history(
    name="fibonacci",
    limit=20
)

# Analyze trend over time
for run in history:
    stats = db.get_statistics(run_id=run.run_id)
    wall_time = next(s for s in stats if s.metric_name == 'wall_time')
    print(f"{run.timestamp}: {wall_time.mean:.6f}s")
```

### Example: Export to JSON

```python
import json

db = BenchmarkDatabase("./benchmarks.db")
db.initialize()

run = db.get_latest_run()
stats = db.get_statistics(run_id=run.run_id)

export_data = {
    'run_id': run.run_id,
    'benchmark_name': run.benchmark_name,
    'timestamp': run.timestamp,
    'statistics': {
        stat.metric_name: {
            'mean': stat.mean,
            'median': stat.median,
            'stddev': stat.stddev
        }
        for stat in stats
    }
}

with open('benchmark_results.json', 'w') as f:
    json.dump(export_data, f, indent=2)

db.close()
```

---

## Statistical Analysis

PlainBench includes comprehensive statistical analysis tools.

### Comparing Runs

```python
from plainbench.analysis import compare_runs

comparison = compare_runs(
    database="./benchmarks.db",
    baseline_run_id=1,
    current_run_id=2,
    alpha=0.05  # Significance level (95% confidence)
)

print(f"Baseline: {comparison.baseline_name}")
print(f"Current: {comparison.current_name}")

for metric_name, metric_comp in comparison.metrics.items():
    print(f"\n{metric_name}:")
    print(f"  Baseline: {metric_comp.baseline_mean:.6f}")
    print(f"  Current: {metric_comp.current_mean:.6f}")
    print(f"  Change: {metric_comp.change_percent:+.2f}%")
    print(f"  Significant: {metric_comp.is_significant}")
    print(f"  P-value: {metric_comp.p_value:.4f}")
```

### Detecting Regressions

```python
from plainbench.analysis import detect_regressions

regressions = detect_regressions(
    database="./benchmarks.db",
    baseline_run_id=1,
    current_run_id=2,
    threshold=0.05  # 5% slowdown threshold
)

if regressions:
    print("⚠️  REGRESSIONS DETECTED!")
    for reg in regressions:
        print(f"  {reg.metric_name}: {reg.change_percent:+.2f}% slower")
        print(f"    Threshold: {threshold * 100}%")
        print(f"    Significant: {reg.is_significant}")
else:
    print("✓ No performance regressions")
```

### Statistical Tests

PlainBench uses:
- **Welch's t-test** for comparing means (doesn't assume equal variance)
- **Significance level (alpha)** defaults to 0.05 (95% confidence)
- **Multiple measurements** for statistical power

### Interpreting Results

**Change Percentage:**
- Positive = current is slower (regression)
- Negative = current is faster (improvement)
- Near zero = no significant change

**Statistical Significance:**
- `is_significant=True`: Change is statistically significant
- `is_significant=False`: Change could be due to random variation

**P-value:**
- < 0.05: Strong evidence of real difference
- > 0.05: Insufficient evidence of difference

### Example: Trend Analysis

```python
from plainbench import BenchmarkDatabase

db = BenchmarkDatabase("./benchmarks.db")
db.initialize()

history = db.get_benchmark_history("my_function", limit=50)

times = []
for run in history:
    stats = db.get_statistics(run_id=run.run_id)
    wall_time = next(s for s in stats if s.metric_name == 'wall_time')
    times.append(wall_time.mean)

# Simple trend detection
if len(times) >= 3:
    recent_avg = sum(times[:10]) / 10
    older_avg = sum(times[-10:]) / 10

    if recent_avg > older_avg * 1.1:
        print("⚠️  Performance degradation detected over time")
    elif recent_avg < older_avg * 0.9:
        print("✓ Performance improvement over time")
    else:
        print("→ Stable performance over time")

db.close()
```

---

## Best Practices

### 1. Benchmark Design

**DO:**
- ✓ Use appropriate input sizes
- ✓ Test multiple scenarios (best/average/worst case)
- ✓ Verify correctness before benchmarking
- ✓ Document test methodology
- ✓ Use consistent isolation levels for comparisons

**DON'T:**
- ✗ Benchmark with trivial inputs
- ✗ Change implementation without re-benchmarking
- ✗ Compare results from different isolation levels
- ✗ Ignore statistical significance
- ✗ Benchmark unrealistic workloads

### 2. Choosing Parameters

**Warmup Iterations:**
- Small functions: 3-5
- Large functions: 1-2
- JIT-compiled code: 10+

**Measurement Runs:**
- Quick checks: 10
- Standard: 20-50
- Critical measurements: 100+

**Isolation Level:**
- Development: minimal
- CI/CD: moderate
- Production: moderate
- Research: maximum

### 3. Metrics Selection

Choose metrics based on what you're optimizing:

**CPU-bound workloads:**
- `wall_time`
- `cpu_time`

**Memory-intensive:**
- `python_memory`
- `process_memory`

**I/O-intensive:**
- `wall_time`
- `disk_io`

**Comprehensive:**
- All metrics (slower but complete picture)

### 4. Statistical Rigor

**For reliable results:**
1. Run enough iterations (20+)
2. Use appropriate warmup (3+)
3. Check coefficient of variation (< 10% is good)
4. Use significance testing for comparisons
5. Report confidence intervals

**Coefficient of Variation:**
```python
cv = (stddev / mean) * 100
# < 5%: Very consistent
# 5-10%: Reasonably consistent
# > 10%: High variability, need more runs or better isolation
```

### 5. Database Management

**DO:**
- ✓ Use descriptive benchmark names
- ✓ Include git commit in metadata
- ✓ Separate databases for different projects
- ✓ Regular backups of benchmark databases
- ✓ Document configuration changes

**DON'T:**
- ✗ Mix different benchmark versions in same database
- ✗ Delete historical data
- ✗ Change isolation without noting it

### 6. CI/CD Integration

```yaml
# Example GitHub Actions workflow
- name: Run Benchmarks
  run: |
    python -m pytest benchmarks/ --benchmark-only
    python scripts/check_regressions.py

# check_regressions.py
from plainbench.analysis import detect_regressions

regressions = detect_regressions(
    database="./benchmarks.db",
    baseline_run_id=get_baseline_run(),
    current_run_id=get_current_run(),
    threshold=0.10  # 10% regression threshold
)

if regressions:
    print("::error::Performance regressions detected")
    sys.exit(1)
```

---

## Advanced Topics

### Custom Metrics

(Note: This feature may require implementing custom metric collectors)

```python
from plainbench.metrics import MetricCollector, MetricResult

class CustomMetric(MetricCollector):
    def setup(self):
        # Initialize
        pass

    def start(self):
        # Start collecting
        self.start_value = get_custom_metric()

    def stop(self) -> MetricResult:
        # Stop and return result
        end_value = get_custom_metric()
        return MetricResult(
            metric_name='custom_metric',
            value=end_value - self.start_value,
            unit='custom_unit'
        )

# Register custom metric
from plainbench.metrics import get_metric_registry
registry = get_metric_registry()
registry.register('custom_metric', CustomMetric)

# Use in benchmarks
@benchmark(metrics=['wall_time', 'custom_metric'])
def my_function():
    pass
```

### Database Migrations

PlainBench uses SQLite with a simple schema. To migrate data:

```python
import sqlite3

# Backup
import shutil
shutil.copy('benchmarks.db', 'benchmarks.db.backup')

# Custom query
conn = sqlite3.connect('benchmarks.db')
cursor = conn.cursor()

# Example: Add custom metadata
cursor.execute('''
    ALTER TABLE benchmark_runs
    ADD COLUMN custom_field TEXT
''')

conn.commit()
conn.close()
```

### Programmatic Execution

Run benchmarks programmatically without decorators:

```python
from plainbench.decorators import benchmark

# Create benchmark manually
bench = benchmark(warmup=5, runs=20)

# Apply to function
benchmarked_func = bench(my_function)

# Run
result = benchmarked_func(arguments)
```

---

## Troubleshooting

### High Variance

**Symptoms:** Standard deviation > 10% of mean

**Solutions:**
1. Increase warmup iterations
2. Use higher isolation level
3. Close background applications
4. Check system load
5. Increase number of runs

### Permission Errors

**Symptoms:** Cannot set CPU affinity or priority

**Solutions:**
1. Run with appropriate permissions (may need sudo on Linux)
2. Use lower isolation level
3. Platform may not support feature (check warnings)

### Memory Metrics Not Available

**Symptoms:** `python_memory` or `process_memory` = 0

**Solutions:**
1. Install psutil: `pip install psutil`
2. Check platform support
3. Verify tracemalloc is enabled

### Database Locked

**Symptoms:** `sqlite3.OperationalError: database is locked`

**Solutions:**
1. Close all database connections
2. Ensure WAL mode is enabled (automatic)
3. Don't access database from multiple processes simultaneously

### Slow Benchmarks

**Symptoms:** Benchmarks take too long

**Solutions:**
1. Reduce number of runs
2. Use smaller input data
3. Reduce warmup iterations
4. Use snapshot mode for shell commands

---

## Summary

PlainBench provides:

1. **@benchmark decorator** for Python functions
2. **benchmark_shell()** for shell commands
3. **Three isolation levels** for reproducibility
4. **SQLite storage** for historical tracking
5. **Statistical analysis** with significance testing

For more information:
- [Quick Start](quickstart.md)
- [Examples](../examples/README.md)
- [Technical Specification](architecture/technical-specification.md)

Happy benchmarking!
