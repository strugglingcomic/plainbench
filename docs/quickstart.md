# PlainBench Quick Start Guide

**Get started with PlainBench in 5 minutes**

---

## Installation

```bash
# Install from source (until PyPI package is available)
git clone https://github.com/yourusername/plainbench.git
cd plainbench
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Requirements

- Python 3.8 or higher
- SQLite 3 (included with Python)
- psutil (for process metrics)

---

## 5-Minute Tutorial

### Step 1: Your First Benchmark

Create a file `my_benchmark.py`:

```python
from plainbench import benchmark

@benchmark()
def fibonacci(n):
    """Calculate fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Run it!
result = fibonacci(20)
print(f"Result: {result}")
```

Run it:

```bash
python my_benchmark.py
```

That's it! Benchmark data is automatically stored in `./benchmarks.db`.

### Step 2: View Your Results

```python
from plainbench import BenchmarkDatabase

db = BenchmarkDatabase("./benchmarks.db")
db.initialize()

# Get latest run
latest = db.get_latest_run()
print(f"Benchmark: {latest.benchmark_name}")

# Get statistics
stats = db.get_statistics(run_id=latest.run_id)
for stat in stats:
    if stat.metric_name == 'wall_time':
        print(f"Mean time: {stat.mean:.6f}s")
        print(f"Std dev: {stat.stddev:.6f}s")

db.close()
```

### Step 3: Customize Your Benchmark

```python
@benchmark(
    name="my_custom_benchmark",
    warmup=5,                    # 5 warmup iterations
    runs=20,                     # 20 measurement runs
    metrics=['wall_time', 'python_memory'],
    isolation='moderate',        # CPU pinning + GC control
    disable_gc=True             # Disable GC during measurement
)
def my_function(n):
    return [i**2 for i in range(n)]

result = my_function(10000)
```

---

## Common Use Cases

### Compare Algorithms

```python
from plainbench import benchmark

@benchmark(name="bubble_sort")
def bubble_sort(data):
    # Your implementation
    return sorted_data

@benchmark(name="quick_sort")
def quick_sort(data):
    # Your implementation
    return sorted_data

# Run both
test_data = [5, 2, 8, 1, 9]
bubble_sort(test_data)
quick_sort(test_data)

# Compare in database
from plainbench.analysis import compare_runs
comparison = compare_runs(
    database="./benchmarks.db",
    baseline_run_id=1,
    current_run_id=2
)
```

### Benchmark Shell Commands

```python
from plainbench.shell import benchmark_shell

result = benchmark_shell(
    command='find . -name "*.py"',
    warmup=1,
    runs=10
)

print(f"Mean time: {result.statistics.wall_time.mean:.3f}s")
print(f"Std dev: {result.statistics.wall_time.stddev:.3f}s")
```

### Detect Performance Regressions

```python
from plainbench.analysis import detect_regressions

# Compare current performance to baseline
regressions = detect_regressions(
    database="./benchmarks.db",
    baseline_run_id=1,
    current_run_id=2,
    threshold=0.05  # 5% slowdown threshold
)

if regressions:
    print("⚠️  Performance regressions detected!")
    for reg in regressions:
        print(f"  {reg.metric_name}: {reg.change_percent:+.2f}% slower")
else:
    print("✓ No regressions detected")
```

---

## Available Metrics

PlainBench can collect multiple performance metrics:

| Metric | Description | Availability |
|--------|-------------|--------------|
| `wall_time` | Total elapsed time | All platforms |
| `cpu_time` | CPU time (excludes I/O wait) | All platforms |
| `python_memory` | Python heap memory usage | All platforms |
| `process_memory` | Total process memory (RSS) | All platforms |
| `disk_io` | Disk I/O operations | Linux (full), others (limited) |
| `cpu_usage` | CPU utilization percentage | All platforms |

### Default Metrics

By default, these metrics are collected:
- `wall_time`
- `cpu_time`
- `python_memory`

### Custom Metrics

```python
@benchmark(
    metrics=['wall_time', 'process_memory', 'disk_io']
)
def my_io_intensive_function():
    # Your code here
    pass
```

---

## Isolation Levels

PlainBench provides three isolation levels for reproducible benchmarks:

### Minimal (Default)
- Basic garbage collection control
- Fast, low overhead
- Good for development

```python
@benchmark(isolation='minimal')
def my_function():
    pass
```

### Moderate (Recommended)
- CPU pinning to specific cores
- Process priority adjustment
- PYTHONHASHSEED for reproducibility
- Garbage collection control
- Best balance for CI/CD

```python
@benchmark(isolation='moderate')
def my_function():
    pass
```

### Maximum
- Subprocess execution
- Environment cleanup
- System state validation
- Best reproducibility, higher overhead
- Ideal for research and critical benchmarks

```python
@benchmark(isolation='maximum')
def my_function():
    pass
```

---

## Configuration

### Decorator Parameters

```python
@benchmark(
    name="custom_name",          # Benchmark name (default: function name)
    warmup=3,                    # Warmup iterations (default: 3)
    runs=10,                     # Measurement runs (default: 10)
    metrics=['wall_time'],       # Metrics to collect
    isolation='minimal',         # Isolation level
    disable_gc=True,            # Disable GC during measurement
    database="./my_bench.db"    # Database location
)
```

### Configuration File

Create `plainbench.yaml`:

```yaml
general:
  default_isolation: moderate
  default_metrics:
    - wall_time
    - cpu_time
    - python_memory

execution:
  warmup_runs: 3
  measurement_runs: 10
  disable_gc: true

storage:
  database_path: "./benchmarks.db"
```

---

## Troubleshooting

### Issue: Benchmark data not saved

**Solution:** Make sure the database directory exists and is writable.

```python
import os
os.makedirs("./benchmark_data", exist_ok=True)

@benchmark(database="./benchmark_data/benchmarks.db")
def my_function():
    pass
```

### Issue: High variance in results

**Solutions:**
1. Increase warmup iterations
2. Increase measurement runs
3. Use higher isolation level
4. Close other applications

```python
@benchmark(
    warmup=10,          # More warmup
    runs=50,            # More runs
    isolation='moderate' # Higher isolation
)
def my_function():
    pass
```

### Issue: Function too slow to benchmark

**Solution:** Use fewer runs or smaller input data

```python
@benchmark(runs=5)  # Fewer runs
def slow_function():
    pass
```

### Issue: Memory metrics not available

**Solution:** Install psutil

```bash
pip install psutil
```

---

## Next Steps

### Learn More
- [User Guide](user-guide.md) - Complete reference and advanced features
- [Examples](../examples/README.md) - Working examples for common scenarios
- [Architecture](architecture/technical-specification.md) - Technical details

### Run Examples

```bash
# Basic decorator usage
python examples/basic_decorator.py

# Shell command benchmarking
python examples/shell_commands.py

# Algorithm comparison
python examples/algorithm_comparison.py

# Database queries
python examples/database_queries.py
```

### Explore the Database

```bash
sqlite3 benchmarks.db

# List all runs
SELECT run_id, benchmark_name, timestamp FROM benchmark_runs;

# View statistics
SELECT * FROM benchmark_statistics WHERE run_id = 1;
```

---

## Quick Reference

### Import Statements

```python
from plainbench import benchmark, BenchmarkDatabase, BenchmarkConfig
from plainbench.shell import benchmark_shell
from plainbench.analysis import compare_runs, detect_regressions
```

### Decorator Syntax

```python
@benchmark()                                    # Minimal
@benchmark(runs=20)                            # Custom runs
@benchmark(isolation='moderate')               # With isolation
@benchmark(metrics=['wall_time', 'memory'])   # Custom metrics
```

### Database Operations

```python
db = BenchmarkDatabase("./benchmarks.db")
db.initialize()

latest = db.get_latest_run()                   # Latest run
all_runs = db.get_all_runs()                   # All runs
measurements = db.get_measurements(run_id=1)   # Measurements
stats = db.get_statistics(run_id=1)            # Statistics
history = db.get_benchmark_history("name")     # History

db.close()
```

### Analysis Operations

```python
from plainbench.analysis import compare_runs, detect_regressions

# Compare runs
comparison = compare_runs(
    database="./benchmarks.db",
    baseline_run_id=1,
    current_run_id=2
)

# Detect regressions
regressions = detect_regressions(
    database="./benchmarks.db",
    baseline_run_id=1,
    current_run_id=2,
    threshold=0.05
)
```

---

## Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/plainbench/issues)
- **Documentation:** [Full Documentation](../README.md)
- **Examples:** [examples/](../examples/)

---

**Ready to benchmark? Start with `examples/basic_decorator.py`!**
