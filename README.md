# PlainBench

**A Python benchmarking framework with decorator support, shell command benchmarking, and SQLite-backed storage for historical analysis.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## Overview

PlainBench is a comprehensive Python benchmarking framework designed for:

- **Fine-grained benchmarking** of Python functions via decorators
- **Black-box benchmarking** of shell commands and external processes
- **Multiple metrics**: timing, CPU usage, memory consumption, disk I/O
- **SQLite-backed storage** for historical analysis and regression detection
- **Configurable isolation** strategies for reproducible results
- **Statistical analysis** with significance testing

### Why PlainBench?

**Zero Infrastructure**: Single SQLite database file, no external services needed. Perfect for local development and CI/CD.

**Comprehensive Metrics**: Beyond just timing - track memory, CPU, I/O, and custom metrics with minimal overhead.

**Built for Comparison**: Design algorithms, compare implementations, and detect performance regressions automatically.

**Reproducible**: Captures environment metadata, git state, and configuration for reproducible benchmarks.

---

## Quick Start

### Installation

```bash
pip install plainbench
```

### Basic Usage

#### Benchmark Python Functions

```python
from plainbench import benchmark

@benchmark()
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Run the function - metrics are automatically collected
result = fibonacci(20)
```

#### Benchmark Shell Commands

```python
from plainbench import benchmark_shell

# Benchmark a shell command
result = benchmark_shell(
    'find . -name "*.py"',
    runs=10
)

print(f"Mean time: {result.wall_time:.3f}s")
```

#### Compare Implementations

```python
from plainbench import benchmark, compare_runs

@benchmark(name="sort_builtin")
def sort_with_builtin(data):
    return sorted(data)

@benchmark(name="sort_custom")
def sort_with_custom(data):
    # Your custom implementation
    return custom_quicksort(data)

# Results are stored in SQLite
# Compare later using CLI:
# $ plainbench compare --baseline-run=1 --current-run=2
```

---

## Features

### 🎯 Python Function Decorators

```python
from plainbench import benchmark

@benchmark(
    warmup=5,           # Warmup iterations
    runs=20,            # Measurement iterations
    metrics=['wall_time', 'python_memory', 'cpu_time'],
    isolation='moderate' # Isolation level
)
def process_data(n):
    return [i**2 for i in range(n)]
```

**Metrics Available:**
- `wall_time`: Wall clock time using `time.perf_counter()`
- `cpu_time`: CPU time (excluding sleep) using `time.process_time()`
- `python_memory`: Python heap memory via `tracemalloc`
- `process_memory`: Total process memory via `psutil`
- `disk_io`: Disk I/O operations (platform-dependent)

### 🐚 Shell Command Benchmarking

```python
from plainbench import benchmark_shell

# Benchmark with monitoring
result = benchmark_shell(
    command='sqlite3 test.db "SELECT * FROM users LIMIT 1000"',
    warmup=1,
    runs=10,
    metrics=['wall_time', 'peak_memory', 'io'],
    monitoring_interval=0.1  # Sample every 100ms
)
```

### 🔒 Isolation Strategies

PlainBench provides three levels of isolation:

**Minimal** (default):
- Basic subprocess isolation
- Quick and easy, suitable for general use

**Moderate** (recommended):
- CPU pinning to specific cores
- Garbage collection control
- PYTHONHASHSEED for reproducibility
- Good balance for local development

**Maximum** (CI/CD):
- Docker containers with resource limits
- cgroups on Linux
- System tuning (CPU governor, Turbo Boost)
- Best for reproducible CI/CD benchmarks

```python
@benchmark(isolation='moderate')
def critical_function():
    # Benchmarked with CPU pinning and GC control
    pass
```

### 📊 SQLite Storage & Analysis

All benchmark results are stored in SQLite with:
- Raw measurements for detailed analysis
- Pre-computed statistics for fast queries
- Environment metadata for reproducibility
- Git state tracking
- Configuration snapshots

```python
from plainbench import BenchmarkDatabase

db = BenchmarkDatabase('./benchmarks.db')

# Get latest results
latest = db.get_latest_run()

# Query historical data
history = db.get_benchmark_history('fibonacci')

# Compare runs
comparison = db.compare_runs(baseline_run_id=1, current_run_id=2)
```

### 📈 Statistical Analysis

```python
from plainbench.analysis import compare_runs, detect_regressions

# Compare with statistical significance testing
comparison = compare_runs(
    baseline_run_id=1,
    current_run_id=2,
    alpha=0.05  # 95% confidence
)

# Detect performance regressions
regressions = detect_regressions(
    baseline_run_id=1,
    current_run_id=2,
    threshold=0.05  # 5% slowdown threshold
)
```

**Statistics Provided:**
- Mean, median, standard deviation
- Min, max values
- 95th and 99th percentiles
- T-test for significance
- Regression detection

### ⚙️ Configuration

PlainBench supports flexible configuration via YAML/TOML files:

```yaml
# plainbench.yaml
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

isolation:
  moderate:
    cpu_affinity: [0, 1, 2, 3]
```

See [plainbench.yaml.example](plainbench.yaml.example) for full configuration options.

---

## CLI Usage

### Run Benchmarks

```bash
# Run all benchmarks in current directory
plainbench run

# Run specific directory
plainbench run tests/benchmarks/

# Run with configuration
plainbench run --isolation=maximum --warmup=5 --runs=20

# Run matching pattern
plainbench run -k "test_sort"
```

### Compare Results

```bash
# Compare two runs
plainbench compare --baseline-run=1 --current-run=2

# Compare git branches
plainbench compare --baseline=main --current=HEAD

# Show only regressions
plainbench compare --show-only-regressions
```

### Show Results

```bash
# Show latest run
plainbench show

# Show specific run
plainbench show --run-id=5

# Show benchmark history
plainbench show --benchmark="fibonacci"
```

### Export Results

```bash
# Export to JSON
plainbench export --format=json --output=results.json

# Export specific run to CSV
plainbench export --format=csv --run-id=5 --output=results.csv

# Generate HTML report
plainbench export --format=html --output=report.html
```

---

## Architecture

PlainBench is built with a modular architecture:

```
plainbench/
├── metrics/          # Metric collectors (timing, memory, CPU, I/O)
├── decorators/       # @benchmark decorator system
├── shell/            # Shell command benchmarking
├── isolation/        # Isolation strategies (minimal/moderate/maximum)
├── storage/          # SQLite database and data models
├── analysis/         # Statistical analysis and comparison
├── config/           # Configuration management
├── cli/              # Command-line interface
└── utils/            # Utilities (platform detection, git integration)
```

### Design Principles

1. **Minimal Overhead**: Measurement overhead < 1% for functions > 100ms
2. **Extensible**: Easy to add custom metrics and isolation strategies
3. **Type-Safe**: Type hints and dataclasses throughout
4. **Platform-Aware**: Graceful degradation on platforms with limited features
5. **Statistical Rigor**: Proper warmup, multiple runs, and significance testing
6. **Reproducible**: Captures environment metadata for reproducibility

For detailed architecture documentation, see:
- [Repository Structure](docs/architecture/repository-structure.md)
- [Technical Specification](docs/architecture/technical-specification.md)
- [Configuration Schema](docs/architecture/configuration-schema.md)

---

## Use Cases

### 1. Algorithm Comparison

Compare different sorting algorithms:

```python
@benchmark(name="bubble_sort")
def bubble_sort(arr):
    # Implementation
    pass

@benchmark(name="quicksort")
def quicksort(arr):
    # Implementation
    pass

@benchmark(name="timsort")
def timsort(arr):
    return sorted(arr)
```

### 2. Queue System Benchmarking

Benchmark different queue implementations (SQLite, Redis, RabbitMQ):

```python
@benchmark(name="sqlite_queue_enqueue", metrics=['wall_time', 'disk_io'])
def sqlite_queue_test():
    # Enqueue 10000 messages to SQLite queue
    pass

result = benchmark_shell(
    'redis-cli LPUSH myqueue $(seq 1 10000)',
    name="redis_queue_enqueue"
)
```

### 3. CI/CD Performance Regression Detection

```yaml
# .github/workflows/benchmark.yml
- name: Run Benchmarks
  run: |
    plainbench run --isolation=maximum
    plainbench compare --baseline=main --current=${{ github.sha }}
    plainbench export --format=json --output=benchmark-results.json
```

### 4. Database Query Optimization

```python
@benchmark(name="query_without_index")
def query_without_index():
    conn.execute("SELECT * FROM users WHERE email = ?", (email,))

@benchmark(name="query_with_index")
def query_with_index():
    # After adding index on email column
    conn.execute("SELECT * FROM users WHERE email = ?", (email,))
```

---

## Platform Support

- **Linux**: Full support (all metrics, cgroups, CPU pinning)
- **macOS**: Full timing and memory support, limited I/O metrics
- **Windows**: Timing and memory support, partial I/O metrics

PlainBench gracefully degrades on platforms with limited features.

---

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/plainbench.git
cd plainbench

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linters
ruff check .
black --check .
mypy plainbench
```

### Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run with coverage
pytest --cov=plainbench --cov-report=html

# Run specific test
pytest tests/unit/test_metrics.py::test_wall_time_collector
```

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas for Contribution

- Additional metric collectors
- Platform-specific optimizations
- Export formats (Markdown, Grafana, etc.)
- Web UI for results visualization
- Remote execution support
- Additional statistical tests

---

## Research & References

PlainBench is built on extensive research of Python benchmarking best practices. Key findings:

- Use `time.perf_counter()` for wall time (monotonic, high-resolution)
- Use `tracemalloc` for Python heap memory profiling
- Use `psutil` for cross-platform process metrics
- Proper warmup iterations to handle JIT and cache effects
- Statistical significance testing to validate results
- Three-tier isolation strategy (minimal/moderate/maximum)

For detailed research findings, see [docs/research.md](docs/research.md).

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Roadmap

### Phase 0 (Current): Core Infrastructure ✅
- [x] Metric collectors (timing, memory)
- [x] SQLite storage and schema
- [x] Data models
- [x] Architecture documentation

### Phase 1: Decorator System
- [ ] @benchmark decorator implementation
- [ ] All metric collectors
- [ ] Metric registry

### Phase 2: Shell Commands
- [ ] Shell command runner
- [ ] Process monitoring
- [ ] Platform-specific handling

### Phase 3: Isolation
- [ ] Minimal/moderate/maximum isolation
- [ ] CPU pinning
- [ ] Docker/cgroups support

### Phase 4: Analysis
- [ ] Statistical analysis
- [ ] Comparison and regression detection
- [ ] Export formats

### Phase 5: CLI & Configuration
- [ ] Complete CLI
- [ ] Configuration system
- [ ] Git integration

### Phase 6: Release
- [ ] Documentation
- [ ] Examples
- [ ] PyPI package

---

## Acknowledgments

Built with insights from:
- **pytest-benchmark**: Fixture-based benchmarking
- **pyperf**: Statistical rigor and methodology
- **psutil**: Cross-platform process monitoring
- **SQLite**: Research on WAL mode and performance optimization

---

**PlainBench** - Benchmark with confidence. 🚀
