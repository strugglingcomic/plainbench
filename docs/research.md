# PlainBench: Research Report on Python Benchmarking Best Practices

**Date:** 2025-11-22
**Purpose:** Research best practices for building a Python benchmarking framework that supports method decorators, black-box shell command benchmarking, SQLite-backed storage, and isolated testing environments.

---

## Table of Contents

1. [Python Benchmarking Best Practices](#1-python-benchmarking-best-practices)
2. [System Metrics Collection for Shell Commands](#2-system-metrics-collection-for-shell-commands)
3. [Isolation Strategies](#3-isolation-strategies)
4. [Benchmarking Framework Design Patterns](#4-benchmarking-framework-design-patterns)
5. [Recommendations for PlainBench](#5-recommendations-for-plainbench)
6. [References](#references)

---

## 1. Python Benchmarking Best Practices

### 1.1 Standard Libraries and Tools

#### Core Timing Tools

**timeit Module**
- The `timeit` module is the standard library solution for measuring execution time
- Usage: `python -m timeit your_code()`
- By default, `timeit()` temporarily turns off garbage collection during timing to make measurements more comparable
- Best for: Quick, one-off benchmarks of small code snippets

**time.perf_counter()**
- **Recommended** timing function for benchmarking (Python 3.3+)
- Provides the highest resolution available from the system's hardware clock
- **Monotonic**: Values always increase and are unaffected by system time changes
- **Not adjustable**: Immune to NTP or manual clock adjustments
- Higher precision than `time.time()`

**Why NOT use time.time():**
- Adjustable (can jump backwards)
- Non-monotonic (affected by system clock changes)
- Lower resolution
- Should be avoided for benchmarking

**Why NOT use time.monotonic():**
- While monotonic, doesn't guarantee high resolution
- `time.perf_counter()` is specifically designed for benchmarking with highest available resolution

**time.process_time()**
- Measures CPU time (user + system) excluding sleep time
- Useful for measuring actual compute work vs. wall clock time

#### Testing Frameworks

**pytest-benchmark**
- Integrates seamlessly with pytest
- Provides a `benchmark` fixture (callable object)
- Groups tests into rounds calibrated to the chosen timer
- Tracks regressions and compares different implementations
- Stores historical data for comparison
- Automatically handles warmup and statistical analysis
- Reports mean, median, standard deviation, min/max times

**pyperf**
- Developed by the Python Software Foundation
- Rigorous statistical analysis with Student's t-test (alpha=0.95)
- Uses median and MAD (median absolute deviation) as robust statistics
- Supports CPU pinning via `--affinity` option
- Environment variable inheritance via `--inherit-environ`
- Designed for reproducible benchmarks
- Provides commands to analyze and compare results

**pyperformance**
- Python Performance Benchmark Suite
- Built on top of pyperf
- Standard benchmarks for Python implementations
- Useful as reference for framework design

### 1.2 Measuring Different Metrics

#### Timing Measurements

**Wall Clock Time:**
```python
import time

start = time.perf_counter()
# Code to benchmark
end = time.perf_counter()
elapsed = end - start
```

**CPU Time (excluding sleep):**
```python
import time

start = time.process_time()
# Code to benchmark
end = time.process_time()
cpu_time = end - start
```

#### CPU Usage

**For Current Process:**
```python
import psutil
import os

process = psutil.Process(os.getpid())
cpu_percent = process.cpu_percent(interval=1.0)
cpu_times = process.cpu_times()  # user, system, etc.
```

**Key Metrics:**
- `cpu_percent()`: Percentage of CPU used (requires interval for accuracy)
- `cpu_times()`: Detailed breakdown of user vs. system time
- `cpu_affinity()`: Which CPUs the process can run on

#### Memory Consumption

**tracemalloc (Built-in, Python 3.4+)**

Best for tracking Python-level allocations:

```python
import tracemalloc

tracemalloc.start()

# Code to benchmark
current, peak = tracemalloc.get_traced_memory()

print(f"Current memory: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")

tracemalloc.stop()
```

**Key Features:**
- `get_traced_memory()`: Returns `(current, peak)` tuple in bytes
- `reset_peak()`: Reset peak counter (Python 3.9+) for measuring specific sections
- `take_snapshot()`: Capture detailed allocation info for analysis
- **Limitation**: Only tracks Python heap allocations, not C library allocations

**psutil (Process-level)**

For total process memory including C allocations:

```python
import psutil
import os

process = psutil.Process(os.getpid())
mem_info = process.memory_info()
print(f"RSS: {mem_info.rss / 1024 / 1024:.1f} MB")
print(f"VMS: {mem_info.vms / 1024 / 1024:.1f} MB")
```

**Key Metrics:**
- `rss`: Resident Set Size (physical memory)
- `vms`: Virtual Memory Size
- `memory_percent()`: Percentage of total system memory

**memory_profiler**

Line-by-line memory profiling:

```python
from memory_profiler import profile

@profile
def my_function():
    # Code here
    pass
```

Provides detailed per-line memory increment information.

#### Disk I/O and Storage Usage

**Process-level I/O:**
```python
import psutil

process = psutil.Process()
io_counters = process.io_counters()
print(f"Read bytes: {io_counters.read_bytes}")
print(f"Write bytes: {io_counters.write_bytes}")
print(f"Read count: {io_counters.read_count}")
print(f"Write count: {io_counters.write_count}")
```

**System-level I/O:**
```python
import psutil

io_before = psutil.disk_io_counters()
# Code to benchmark
io_after = psutil.disk_io_counters()

read_bytes = io_after.read_bytes - io_before.read_bytes
write_bytes = io_after.write_bytes - io_before.write_bytes
```

**Platform Support:**
- Linux: Full support for per-process I/O counters
- macOS/FreeBSD: Limited support
- Windows: Partial support

**Note:** For accurate per-process I/O on Linux, may need appropriate permissions.

### 1.3 Decorator-Based Benchmarking

#### Basic Timing Decorator

```python
import time
import functools

def benchmark(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__}: {end - start:.6f}s")
        return result
    return wrapper

@benchmark
def my_function():
    # Code here
    pass
```

#### Comprehensive Monitoring Decorator

The **metrit** library provides a decorator for comprehensive CPU, RAM, and I/O monitoring:

```python
from metrit import metrify

@metrify
def my_function():
    # Code here
    pass
```

Features:
- Adaptive refresh rate to minimize overhead for long-running functions
- Tracks CPU, memory, and I/O metrics
- Minimal overhead through intelligent sampling

#### Custom Multi-Metric Decorator Pattern

```python
import time
import tracemalloc
import psutil
import functools
from dataclasses import dataclass

@dataclass
class BenchmarkResult:
    wall_time: float
    cpu_time: float
    peak_memory: int
    read_bytes: int
    write_bytes: int

def benchmark_all(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Setup
        process = psutil.Process()
        io_before = process.io_counters()
        tracemalloc.start()
        wall_start = time.perf_counter()
        cpu_start = time.process_time()

        # Execute
        result = func(*args, **kwargs)

        # Measure
        cpu_time = time.process_time() - cpu_start
        wall_time = time.perf_counter() - wall_start
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        io_after = process.io_counters()

        metrics = BenchmarkResult(
            wall_time=wall_time,
            cpu_time=cpu_time,
            peak_memory=peak_memory,
            read_bytes=io_after.read_bytes - io_before.read_bytes,
            write_bytes=io_after.write_bytes - io_before.write_bytes
        )

        # Store metrics (to database, etc.)

        return result
    return wrapper
```

### 1.4 Minimizing Measurement Overhead

#### Best Practices

1. **Disable Garbage Collection During Measurement**
   ```python
   import gc

   gc.collect()  # Clean up before benchmark
   gc.disable()
   # Benchmark code
   gc.enable()
   ```

2. **Disable Program Output**
   - Avoid `print()` statements during benchmarking
   - Disable or redirect logging
   - I/O operations are slow and add noise

3. **Use Lightweight Timing Functions**
   - `time.perf_counter()` has minimal overhead
   - Avoid calling timing functions too frequently in tight loops

4. **Minimize State Capture**
   - Only collect metrics you need
   - Use sampling for continuous metrics vs. before/after snapshots
   - Consider decorator overhead: approximately one extra function call

5. **Profile the Profiler**
   - cProfile has lower overhead than profile (written in C)
   - tracemalloc has some overhead; consider disabling for production
   - psutil sampling adds overhead proportional to sample frequency

#### Decorator Overhead

Based on research:
- Pure decorator overhead: one extra function call (~100-200 nanoseconds)
- Actual overhead depends on measurement operations performed
- For short-lived functions, measurement overhead can exceed execution time
- Solution: Only benchmark functions that run long enough for overhead to be negligible

### 1.5 Warmup Periods and Statistical Significance

#### Warmup Periods

**Why Warmup is Needed:**
- JIT compilation (PyPy, Numba)
- CPU cache warming
- OS page faults on first access
- Python's internal optimizations

**Implementing Warmup:**

```python
def benchmark_with_warmup(func, warmup=3, runs=10):
    # Warmup
    for _ in range(warmup):
        func()

    # Actual measurements
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append(end - start)

    return times
```

**pytest-benchmark Approach:**
- Automatically runs one warmup iteration per worker
- Configurable via `--benchmark-warmup` option

**pyperf Recommendations:**
- Analyze warmup values manually
- Usually skipping the first value is enough
- For PyPy, may need to skip many more values
- Each worker runs benchmark once to warmup before actual measurement

#### Statistical Significance

**Sample Size:**
- Should be large enough to reduce random effects:
  - ASLR (Address Space Layout Randomization)
  - Python randomized hash function
  - Background processes
  - CPU frequency scaling

**Recommended Approach:**
- Multiple runs × multiple values per run
- Example: 5 runs × 20 values = 100 total samples
- Goal: Uniform distribution of samples

**Statistical Methods:**

**pytest-benchmark:**
- Reports mean, median, stddev, min, max
- IQR (Interquartile Range) for outlier detection
- Comparison against historical data

**pyperf:**
- Uses Student's two-sample, two-tailed t-test (alpha=0.95)
- Reports median and MAD (median absolute deviation)
- MAD is robust against outliers
- Determines if two benchmark results are significantly different

**Key Statistics to Report:**

1. **Mean**: Average execution time (most common metric)
2. **Median**: Middle value (robust against outliers)
3. **Standard Deviation**: Consistency measure (lower = more consistent)
4. **Min/Max**: Range of values
5. **Percentiles**: 95th, 99th percentile for latency analysis

**Example Statistical Analysis:**
```python
import statistics

def analyze_results(times):
    return {
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'stdev': statistics.stdev(times),
        'min': min(times),
        'max': max(times),
        'p95': statistics.quantiles(times, n=20)[18],  # 95th percentile
        'p99': statistics.quantiles(times, n=100)[98],  # 99th percentile
    }
```

---

## 2. System Metrics Collection for Shell Commands

### 2.1 Measuring External Process Metrics

When benchmarking external shell commands, we need to measure child process metrics from the parent Python process.

### 2.2 Using resource Module

#### Basic Usage with RUSAGE_CHILDREN

```python
import subprocess
import resource

usage_start = resource.getrusage(resource.RUSAGE_CHILDREN)
subprocess.call(["your_command"])
usage_end = resource.getrusage(resource.RUSAGE_CHILDREN)

cpu_time = usage_end.ru_utime - usage_start.ru_utime
sys_time = usage_end.ru_stime - usage_start.ru_stime
max_rss = usage_end.ru_maxrss - usage_start.ru_maxrss
```

#### Available Metrics from getrusage()

```python
ru_utime      # User time (seconds)
ru_stime      # System time (seconds)
ru_maxrss     # Maximum RSS (KB on Linux, bytes on macOS)
ru_ixrss      # Shared memory size (deprecated)
ru_idrss      # Unshared data size (deprecated)
ru_isrss      # Unshared stack size (deprecated)
ru_minflt     # Page faults not requiring I/O
ru_majflt     # Page faults requiring I/O
ru_nswap      # Times swapped out (deprecated)
ru_inblock    # Block input operations
ru_oublock    # Block output operations
ru_msgsnd     # IPC messages sent
ru_msgrcv     # IPC messages received
ru_nsignals   # Signals received
ru_nvcsw      # Voluntary context switches
ru_nivcsw     # Involuntary context switches
```

#### Critical Limitations of RUSAGE_CHILDREN

1. **Fork-then-exec Problem:**
   - When using `subprocess`, Python forks itself, then execs the command
   - Memory measurements may capture the forked Python process, not the actual subprocess
   - Solution: Use multiprocessing wrapper (see below)

2. **Only Direct Children:**
   - Only captures direct child processes
   - Does NOT capture grandchildren
   - Shell commands with pipes or complex scripts may spawn additional processes that aren't measured

3. **Aggregate Measurements:**
   - Returns sum of all terminated children since last call
   - Running multiple subprocesses concurrently produces combined results
   - Need to isolate subprocess calls for accurate per-command metrics

4. **Platform Differences:**
   - `ru_maxrss` units differ: KB on Linux, bytes on macOS
   - Some fields deprecated on modern systems
   - Not available on Windows

### 2.3 Using psutil for Process Monitoring

psutil is the recommended cross-platform solution for monitoring subprocess metrics.

#### Real-time Monitoring Approach

```python
import psutil
import subprocess
import time

# Start subprocess
proc = subprocess.Popen(['your_command'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)

# Wrap with psutil
ps_proc = psutil.Process(proc.pid)

# Monitor while running
max_memory = 0
cpu_samples = []

while proc.poll() is None:
    try:
        mem = ps_proc.memory_info().rss
        cpu = ps_proc.cpu_percent(interval=0.1)
        max_memory = max(max_memory, mem)
        cpu_samples.append(cpu)
    except psutil.NoSuchProcess:
        break
    time.sleep(0.1)

# Wait for completion
proc.wait()

print(f"Max memory: {max_memory / 1024 / 1024:.1f} MB")
print(f"Avg CPU: {sum(cpu_samples) / len(cpu_samples):.1f}%")
```

**Limitations:**
- Sampling approach can miss brief spikes
- Not suitable for very short-lived processes
- Overhead from monitoring loop

#### Before/After Snapshot Approach

```python
import psutil
import subprocess

proc = subprocess.Popen(['your_command'])
ps_proc = psutil.Process(proc.pid)

# Wait for process to complete
proc.wait()

# Get final stats
mem_info = ps_proc.memory_info()
cpu_times = ps_proc.cpu_times()
io_counters = ps_proc.io_counters()

print(f"RSS: {mem_info.rss / 1024 / 1024:.1f} MB")
print(f"User time: {cpu_times.user:.2f}s")
print(f"System time: {cpu_times.system:.2f}s")
print(f"Read bytes: {io_counters.read_bytes}")
print(f"Write bytes: {io_counters.write_bytes}")
```

**Better for short-lived processes but loses peak memory information.**

### 2.4 Hybrid Approach: multiprocessing + resource

Most accurate method for measuring subprocess resource usage:

```python
import subprocess
import resource
import multiprocessing

def run_subprocess_with_resource_tracking(cmd):
    """Run in a multiprocessing.Process to get accurate RUSAGE_CHILDREN."""
    subprocess.run(cmd, shell=True)

def measure_subprocess(cmd):
    # Create wrapper process
    process = multiprocessing.Process(
        target=run_subprocess_with_resource_tracking,
        args=(cmd,)
    )

    # Start and wait
    process.start()
    process.join()

    # Get resource usage from this process's children
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)

    return {
        'user_time': usage.ru_utime,
        'system_time': usage.ru_stime,
        'max_rss': usage.ru_maxrss,
        'block_input': usage.ru_inblock,
        'block_output': usage.ru_oublock,
    }
```

**Advantages:**
- Accurate resource measurement
- Avoids fork-then-exec memory confusion
- Isolated per-command measurement

**Disadvantages:**
- Additional overhead from multiprocessing
- More complex implementation

### 2.5 Measuring Disk I/O

#### Using psutil

```python
import psutil

process = psutil.Process(pid)
io = process.io_counters()

print(f"Read bytes: {io.read_bytes}")
print(f"Write bytes: {io.write_bytes}")
print(f"Read count: {io.read_count}")
print(f"Write count: {io.write_count}")
```

**Platform Support:**
- Linux: Full support
- Windows: Partial support
- macOS/FreeBSD: Limited or no support for per-process I/O

#### Continuous Monitoring (iotop-style)

```python
import psutil
import time

def monitor_io(pid, interval=1.0):
    """Monitor I/O like iotop."""
    process = psutil.Process(pid)
    io_before = process.io_counters()

    time.sleep(interval)

    io_after = process.io_counters()

    read_rate = (io_after.read_bytes - io_before.read_bytes) / interval
    write_rate = (io_after.write_bytes - io_before.write_bytes) / interval

    return {
        'read_mb_per_sec': read_rate / (1024 * 1024),
        'write_mb_per_sec': write_rate / (1024 * 1024),
    }
```

Reference implementation: [psutil/scripts/iotop.py](https://github.com/giampaolo/psutil/blob/master/scripts/iotop.py)

### 2.6 Recommended Approach for PlainBench

**For black-box shell command benchmarking:**

1. **Use psutil for cross-platform compatibility**
2. **Implement both snapshot and monitoring modes:**
   - Snapshot: Fast, low overhead, good for short commands
   - Monitoring: Captures peak usage, good for long-running commands
3. **Fallback to resource module on Linux for additional metrics**
4. **Provide configuration for sampling interval**
5. **Handle platform differences gracefully**

**Metrics to Capture:**
- Wall time (subprocess completion time)
- User CPU time
- System CPU time
- Peak memory (RSS)
- Disk read/write bytes
- Exit code and stdout/stderr

---

## 3. Isolation Strategies

Benchmark isolation prevents "noisy neighbor" contamination from other processes, system activities, and non-deterministic performance variations.

### 3.1 Isolation Approaches Comparison

#### 3.1.1 OS-Level Process Isolation

**Description:** Use standard OS process isolation via subprocess.

**Pros:**
- Built into OS, no additional tools needed
- Lightweight overhead
- Simple implementation
- Works everywhere Python runs

**Cons:**
- Minimal isolation from system interference
- Shared CPU cores (subject to scheduler)
- Shared memory (can be swapped)
- Shared I/O bandwidth
- No resource limits enforcement

**Use Case:** Default baseline; suitable when running benchmarks on otherwise idle machines.

#### 3.1.2 cgroups (Control Groups)

**Description:** Linux kernel feature for resource limiting, accounting, and isolation.

**Pros:**
- Fine-grained resource limits (CPU, memory, I/O)
- Process accounting and monitoring
- Can isolate without full containerization
- Lower overhead than VMs or containers
- Used by Docker internally

**Cons:**
- Linux-only (cgroups v1/v2)
- Requires root or specific permissions
- Complex API
- Cross-platform tools needed

**Implementation:**

cgroups allow you to allocate CPU shares, memory limits, and block I/O bandwidth to individual containers (or processes).

**Docker with cgroup isolation:**
```bash
# Create separate cgroup for benchmarks
docker run --rm \
  --cpus="2.0" \
  --memory="4g" \
  --memory-swap="4g" \
  --cgroup-parent=benchmark-cgroup \
  python:3.11 python benchmark.py
```

**Direct cgroup usage (requires root):**
```python
import os

# Example: limit memory to 1GB
cgroup_path = '/sys/fs/cgroup/memory/benchmark'
os.makedirs(cgroup_path, exist_ok=True)

with open(f'{cgroup_path}/memory.limit_in_bytes', 'w') as f:
    f.write(str(1024 * 1024 * 1024))  # 1GB

with open(f'{cgroup_path}/cgroup.procs', 'w') as f:
    f.write(str(os.getpid()))
```

**Use Case:** Ideal for Linux servers; provides isolation without container overhead.

#### 3.1.3 Docker Containers with Fixed Resources

**Description:** Run benchmarks in Docker containers with constrained resources.

**Pros:**
- Portable across Linux systems
- Reproducible environment (dependencies frozen in image)
- Well-documented resource limits
- Isolation from host system
- Can use different Linux distributions

**Cons:**
- Container overhead (though minimal)
- Requires Docker daemon
- Additional complexity
- Not available on all systems (Windows/macOS use VMs)
- Python may not respect container limits without configuration

**Resource Constraints:**
```bash
docker run --rm \
  --cpus="2.0" \             # 2 CPU cores
  --memory="4g" \            # 4GB RAM
  --memory-swap="4g" \       # Disable swap
  --pids-limit=100 \         # Process limit
  --ulimit nofile=1024:1024 \  # File descriptor limit
  python:3.11 python benchmark.py
```

**Python Memory Limit Issue:**

Python sees the entire host's resources and may try to allocate more memory than allowed, causing the process to be killed by Linux OOM killer.

**Solution:** Read actual limits from cgroup:
```python
import os

def get_memory_limit():
    """Get actual memory limit in container."""
    try:
        with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
            limit = int(f.read().strip())
            # Check if it's the "no limit" value
            if limit > (1 << 62):
                return None
            return limit
    except FileNotFoundError:
        return None

# Use this to configure Python memory usage
```

**Use Case:** Best for CI/CD pipelines and reproducible benchmarking across different machines.

#### 3.1.4 Virtual Environments (venv/virtualenv)

**Description:** Python virtual environments for dependency isolation.

**Pros:**
- Standard Python tooling
- Isolates Python packages
- No special permissions needed
- Cross-platform

**Cons:**
- Does NOT isolate system resources
- Does NOT prevent CPU/memory interference
- Only isolates Python dependencies
- Not suitable for performance isolation

**Use Case:** Essential for dependency management, but NOT sufficient for performance isolation alone.

### 3.2 CPU Pinning and NUMA Awareness

#### CPU Pinning

**Why It Matters:**
- Process migration between cores causes cache invalidation
- NUMA systems have non-uniform memory access latency
- Reduces performance variance

**Using taskset (Linux):**
```bash
# Pin to CPU cores 0-3
taskset -c 0-3 python benchmark.py
```

**Using psutil:**
```python
import psutil
import os

# Pin to specific cores
process = psutil.Process(os.getpid())
process.cpu_affinity([0, 1, 2, 3])  # Cores 0-3
```

**Using pyperf:**
```bash
python -m pyperf run --affinity=0,1,2,3 benchmark.py
```

**Recommendation:** Always use CPU pinning via `--affinity` to avoid noise from process migration.

#### NUMA Systems

On NUMA (Non-Uniform Memory Access) systems:
- Memory access latency depends on which CPU socket it's near
- CPU pinning is critical for consistent performance
- Consider using `numactl` to bind both CPU and memory to same node

```bash
numactl --cpunodebind=0 --membind=0 python benchmark.py
```

### 3.3 System Tuning for Benchmarking

#### Disable Dynamic CPU Features

**Intel Turbo Boost:**
- Dynamically increases CPU frequency
- Creates performance variance
- Disable from BIOS/UEFI or:
```bash
echo 1 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo
```

**AMD Turbo Core:**
```bash
echo 0 | sudo tee /sys/devices/system/cpu/cpufreq/boost
```

**Hyper-Threading:**
- Can cause variance due to resource sharing
- Consider disabling from BIOS for most consistent results

#### CPU Governor

Set CPU to performance mode (maximum frequency):
```bash
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

#### Address Space Layout Randomization (ASLR)

Disable ASLR for more consistent benchmarks:
```bash
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space
```

**Note:** This has security implications; only disable for benchmarking on isolated systems.

#### Disable Python Hash Randomization

```bash
export PYTHONHASHSEED=0
python benchmark.py
```

### 3.4 Recommendations for PlainBench

**For a Local Development Tool:**

**Minimal Isolation (Default):**
- Use standard Python subprocess
- Recommend running on idle machine
- Provide warnings about potential interference
- Easy setup, no special permissions

**Moderate Isolation (Recommended):**
- CPU pinning via psutil
- Set CPU governor to performance
- Disable Python hash randomization
- Works on most systems without root

**Maximum Isolation (Optional/Advanced):**
- Docker containers with resource limits (if available)
- cgroups on Linux (if root access)
- System tuning (Turbo Boost, ASLR, etc.)
- Requires setup, but most reproducible

**Configuration Approach:**
```python
# Example configuration
isolation_config = {
    'level': 'moderate',  # 'minimal', 'moderate', 'maximum'
    'cpu_affinity': [0, 1, 2, 3],
    'disable_gc': True,
    'warmup_runs': 3,
}
```

**Trade-offs:**
- Minimal: Easy setup, variable results
- Moderate: Good balance for local development
- Maximum: Best reproducibility, requires infrastructure

---

## 4. Benchmarking Framework Design Patterns

### 4.1 API Structure Comparison

#### 4.1.1 pytest-benchmark

**Design Pattern:** Fixture-based integration with pytest

```python
def test_my_function(benchmark):
    # Simple usage
    result = benchmark(my_function, arg1, arg2)

    # Or as context manager
    with benchmark:
        result = my_function(arg1, arg2)
```

**Key Design Decisions:**
- Integrates with existing test framework
- Automatic discovery via pytest
- Fixtures for dependency injection
- Declarative configuration
- Stores results in JSON files
- Built-in comparison and regression detection

**Configuration:**
```ini
[pytest]
addopts =
    --benchmark-warmup=on
    --benchmark-min-rounds=5
    --benchmark-max-time=1.0
```

**Strengths:**
- Familiar to pytest users
- Low friction for adoption
- Good for unit-level benchmarks

**Weaknesses:**
- Tied to pytest ecosystem
- Not ideal for standalone benchmarking tool

#### 4.1.2 Locust

**Design Pattern:** User class-based load testing

```python
from locust import User, task, between

class MyUser(User):
    wait_time = between(1, 3)

    @task
    def my_task(self):
        # Perform operation
        pass

    @task(3)  # Weight: 3x more likely
    def another_task(self):
        pass
```

**Key Design Decisions:**
- OOP design with User classes
- Declarative task weighting
- Built for distributed load testing
- Web UI for real-time monitoring
- Event-driven metrics collection

**Strengths:**
- Excellent for load/stress testing
- Distributed execution
- Real-time visualization

**Weaknesses:**
- Heavy framework
- Focused on HTTP/web testing
- Overkill for function benchmarking

#### 4.1.3 pyperf

**Design Pattern:** Command-line focused with Runner API

```python
import pyperf

runner = pyperf.Runner()
runner.bench_func('my_benchmark', my_function, arg1, arg2)
```

**Key Design Decisions:**
- Minimal API surface
- Statistical rigor (t-tests, median, MAD)
- Multiple processes for isolation
- JSON result storage
- Comparison tools

**Strengths:**
- Rigorous statistical analysis
- Designed for reproducibility
- Excellent for language benchmarks

**Weaknesses:**
- Limited to function benchmarking
- Less flexible for complex scenarios

### 4.2 Database Schema Design for Benchmark Results

#### 4.2.1 Core Entities

**Benchmark Runs:**
```sql
CREATE TABLE benchmark_runs (
    run_id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    git_commit_hash TEXT,
    git_branch TEXT,
    environment_id INTEGER,
    FOREIGN KEY (environment_id) REFERENCES environments(environment_id)
);
```

**Environments:**
```sql
CREATE TABLE environments (
    environment_id INTEGER PRIMARY KEY,
    python_version TEXT,
    platform TEXT,
    processor TEXT,
    cpu_count INTEGER,
    memory_total INTEGER,
    disk_type TEXT,
    metadata_json TEXT  -- Additional flexible metadata
);
```

**Benchmarks:**
```sql
CREATE TABLE benchmarks (
    benchmark_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    benchmark_type TEXT,  -- 'function', 'shell_command'
    category TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);
```

**Measurements:**
```sql
CREATE TABLE measurements (
    measurement_id INTEGER PRIMARY KEY,
    run_id INTEGER,
    benchmark_id INTEGER,
    iteration INTEGER,  -- Which iteration within the run
    wall_time REAL,
    cpu_time REAL,
    peak_memory INTEGER,
    current_memory INTEGER,
    read_bytes INTEGER,
    write_bytes INTEGER,
    exit_code INTEGER,  -- For shell commands
    metadata_json TEXT,  -- Flexible additional metrics
    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(benchmark_id)
);

CREATE INDEX idx_measurements_run ON measurements(run_id);
CREATE INDEX idx_measurements_benchmark ON measurements(benchmark_id);
```

#### 4.2.2 Time-Series Schema Pattern

For storing metrics over time (suitable for continuous monitoring):

```sql
CREATE TABLE metric_types (
    metric_type_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    unit TEXT,
    description TEXT
);

CREATE TABLE time_series_metrics (
    metric_id INTEGER PRIMARY KEY,
    benchmark_id INTEGER,
    run_id INTEGER,
    metric_type_id INTEGER,
    timestamp REAL,  -- Relative time from benchmark start
    value REAL,
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(benchmark_id),
    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (metric_type_id) REFERENCES metric_types(metric_type_id)
);

CREATE INDEX idx_time_series_benchmark_run ON time_series_metrics(benchmark_id, run_id);
CREATE INDEX idx_time_series_timestamp ON time_series_metrics(timestamp);
```

**Advantages:**
- Flexible: new metrics only require new row in metric_types
- Supports continuous monitoring (many samples per benchmark)
- Queries can be optimized with clustered index on timestamp

**Disadvantages:**
- More complex queries
- Higher storage for many metrics
- Join performance considerations

#### 4.2.3 Statistical Aggregates

```sql
CREATE TABLE benchmark_statistics (
    stat_id INTEGER PRIMARY KEY,
    run_id INTEGER,
    benchmark_id INTEGER,
    sample_count INTEGER,
    mean_time REAL,
    median_time REAL,
    stddev_time REAL,
    min_time REAL,
    max_time REAL,
    p95_time REAL,
    p99_time REAL,
    mean_memory INTEGER,
    peak_memory INTEGER,
    total_read_bytes INTEGER,
    total_write_bytes INTEGER,
    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(benchmark_id),
    UNIQUE(run_id, benchmark_id)
);
```

**Use Case:** Pre-computed aggregates for faster comparison queries.

#### 4.2.4 Comparison Schema

```sql
CREATE TABLE benchmark_comparisons (
    comparison_id INTEGER PRIMARY KEY,
    baseline_run_id INTEGER,
    comparison_run_id INTEGER,
    benchmark_id INTEGER,
    speedup_factor REAL,  -- comparison_time / baseline_time
    memory_ratio REAL,
    is_significant BOOLEAN,  -- Based on t-test or other statistical test
    p_value REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (baseline_run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (comparison_run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(benchmark_id)
);
```

### 4.3 Query Patterns

#### Get Latest Benchmark Results

```sql
SELECT
    b.name,
    bs.mean_time,
    bs.stddev_time,
    bs.peak_memory
FROM benchmark_statistics bs
JOIN benchmarks b ON bs.benchmark_id = b.benchmark_id
JOIN benchmark_runs br ON bs.run_id = br.run_id
WHERE br.timestamp = (
    SELECT MAX(timestamp) FROM benchmark_runs
)
ORDER BY b.name;
```

#### Compare Against Baseline

```sql
SELECT
    b.name,
    baseline.mean_time as baseline_time,
    current.mean_time as current_time,
    (current.mean_time - baseline.mean_time) / baseline.mean_time * 100 as pct_change
FROM benchmarks b
JOIN benchmark_statistics baseline
    ON b.benchmark_id = baseline.benchmark_id
JOIN benchmark_statistics current
    ON b.benchmark_id = current.benchmark_id
WHERE baseline.run_id = ? -- baseline run
  AND current.run_id = ?  -- current run
ORDER BY pct_change DESC;
```

#### Trend Analysis

```sql
SELECT
    br.timestamp,
    b.name,
    bs.mean_time,
    bs.peak_memory
FROM benchmark_statistics bs
JOIN benchmarks b ON bs.benchmark_id = b.benchmark_id
JOIN benchmark_runs br ON bs.run_id = br.run_id
WHERE b.name = ?
  AND br.timestamp >= datetime('now', '-30 days')
ORDER BY br.timestamp;
```

### 4.4 Configuration and Reproducibility

#### Configuration Storage

```sql
CREATE TABLE configurations (
    config_id INTEGER PRIMARY KEY,
    run_id INTEGER,
    key TEXT,
    value TEXT,
    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id)
);

-- Example data
INSERT INTO configurations (run_id, key, value) VALUES
(1, 'isolation_level', 'moderate'),
(1, 'cpu_affinity', '[0,1,2,3]'),
(1, 'warmup_runs', '3'),
(1, 'disable_gc', 'true'),
(1, 'PYTHONHASHSEED', '0');
```

#### Environment Variables

```sql
CREATE TABLE environment_variables (
    env_var_id INTEGER PRIMARY KEY,
    run_id INTEGER,
    name TEXT,
    value TEXT,
    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id)
);
```

#### Dependency Tracking

```sql
CREATE TABLE dependencies (
    dep_id INTEGER PRIMARY KEY,
    environment_id INTEGER,
    package_name TEXT,
    package_version TEXT,
    FOREIGN KEY (environment_id) REFERENCES environments(environment_id)
);
```

### 4.5 Result Comparison Best Practices

#### Statistical Comparison

Use statistical tests to determine if differences are significant:

```python
from scipy import stats

def compare_benchmarks(baseline_samples, current_samples, alpha=0.05):
    """Compare two benchmark results using t-test."""
    t_stat, p_value = stats.ttest_ind(baseline_samples, current_samples)

    baseline_mean = statistics.mean(baseline_samples)
    current_mean = statistics.mean(current_samples)

    speedup = baseline_mean / current_mean
    is_significant = p_value < alpha

    return {
        'speedup': speedup,
        'p_value': p_value,
        'is_significant': is_significant,
        'baseline_mean': baseline_mean,
        'current_mean': current_mean,
    }
```

#### Regression Detection

```python
def detect_regressions(comparisons, threshold=0.05):
    """Detect performance regressions."""
    regressions = []
    for comp in comparisons:
        if comp['speedup'] < (1 - threshold) and comp['is_significant']:
            regressions.append({
                'benchmark': comp['name'],
                'slowdown_pct': (1 - comp['speedup']) * 100,
                'p_value': comp['p_value'],
            })
    return regressions
```

---

## 5. Recommendations for PlainBench

Based on the research, here are specific recommendations for building PlainBench:

### 5.1 Core Libraries

**Required:**
- `time` (perf_counter, process_time) - Timing measurements
- `tracemalloc` - Memory profiling
- `psutil` - Process and system metrics
- `sqlite3` - Database backend
- `dataclasses` - Data structures for results

**Optional but Recommended:**
- `resource` - Additional metrics on Unix systems
- `multiprocessing` - Isolation for subprocess measurements
- `scipy` - Statistical analysis (t-tests)
- `click` or `argparse` - CLI interface

### 5.2 Architecture Recommendations

#### Decorator API for Functions

```python
from plainbench import benchmark

@benchmark(
    warmup=3,
    runs=10,
    isolation='moderate',
    metrics=['time', 'memory', 'cpu', 'io']
)
def my_function():
    # Function code
    pass
```

#### Shell Command API

```python
from plainbench import benchmark_shell

results = benchmark_shell(
    command='sqlite3 test.db < queries.sql',
    warmup=1,
    runs=5,
    metrics=['time', 'memory', 'io'],
    isolation='maximum',
)
```

### 5.3 Metrics Collection Strategy

**For Decorated Functions:**
1. Use `time.perf_counter()` for wall time
2. Use `time.process_time()` for CPU time
3. Use `tracemalloc` for memory (with reset_peak for accuracy)
4. Use `psutil.Process()` for I/O counters
5. Disable GC during measurement
6. Support both before/after and continuous monitoring

**For Shell Commands:**
1. Use `psutil.Popen()` wrapper for monitoring
2. Fallback to `resource.getrusage(RUSAGE_CHILDREN)` on Unix
3. Use multiprocessing wrapper for accurate resource tracking
4. Support both snapshot and continuous monitoring modes
5. Capture stdout/stderr optionally

### 5.4 Database Schema

Use the hybrid approach:
- **measurements table** for raw samples
- **benchmark_statistics table** for pre-computed aggregates
- **configurations table** for reproducibility
- **environments table** for system metadata
- Add indexes for common query patterns

### 5.5 Isolation Strategy

**Three-tier approach:**

1. **Minimal** (default):
   - Subprocess isolation only
   - Warning about potential interference
   - No special requirements

2. **Moderate** (recommended):
   - CPU pinning via psutil
   - Disable GC during measurement
   - Set PYTHONHASHSEED
   - Requires no root access

3. **Maximum** (optional):
   - Docker containers (if available)
   - cgroups (on Linux with permissions)
   - System tuning (CPU governor, Turbo Boost)
   - Best for CI/CD

### 5.6 Statistical Rigor

1. **Warmup:** Default 3 iterations, configurable
2. **Runs:** Default 10 iterations, configurable
3. **Statistics:** Report mean, median, stddev, min, max, p95, p99
4. **Comparison:** Use t-test for significance (alpha=0.05)
5. **Outlier handling:** Use median and MAD for robustness

### 5.7 Configuration Management

Store configuration with each benchmark run:
- Isolation level
- CPU affinity
- Warmup/run counts
- Environment variables
- Git commit hash
- System information
- Python version
- Package dependencies

### 5.8 CLI Design

```bash
# Run benchmarks
plainbench run tests/benchmarks/

# Run with configuration
plainbench run --isolation=maximum --warmup=5 --runs=20

# Compare against baseline
plainbench compare --baseline=main --current=HEAD

# Show results
plainbench show --run-id=123

# Export results
plainbench export --format=json --output=results.json
```

### 5.9 Platform Support

**Primary:** Linux
**Secondary:** macOS
**Limited:** Windows (psutil limitations on I/O metrics)

Handle platform differences gracefully:
- Detect available features
- Provide warnings for unsupported metrics
- Graceful degradation

### 5.10 Error Handling

- Validate isolation requirements before running
- Check for permission issues
- Provide clear error messages
- Support dry-run mode
- Validate database schema

---

## References

### Python Benchmarking Best Practices
- [How to Benchmark (Python) Code](https://switowski.com/blog/how-to-benchmark-python-code/)
- [Python Benchmarking Best Practices - Super Fast Python](https://superfastpython.com/python-benchmarking-best-practices/)
- [pytest-benchmark · PyPI](https://pypi.org/project/pytest-benchmark/)
- [How to benchmark Python code with pytest-benchmark | Bencher](https://bencher.dev/learn/benchmarking/python/pytest-benchmark/)
- [Benchmarking and Profiling in Python | Medium](https://medium.com/@hasanshahjahan/benchmarking-and-profiling-in-python-dd4db60e3149)

### Decorators and Profiling
- [Python Timer Functions: Three Ways to Monitor Your Code – Real Python](https://realpython.com/python-timer/)
- [Benchmark Decorator in Python - Super Fast Python](https://superfastpython.com/benchmark-decorator/)
- [GitHub - mcrespoae/metrit](https://github.com/mcrespoae/metrit)
- [Performance and Profiling — System Development With Python](https://uwpce-pythoncert.github.io/SystemDevelopment/profiling.html)

### Process Monitoring with psutil
- [psutil documentation](https://psutil.readthedocs.io/en/latest/)
- [psutil · PyPI](https://pypi.org/project/psutil/)
- [GitHub - giampaolo/psutil](https://github.com/giampaolo/psutil)
- [Measuring the CPU and Memory Usage for Python subprocess | ValarMorghulis.IO](https://valarmorghulis.io/tech/202505-measuring-cpu-memory-python-subprocess/)
- [System Monitoring Made Easy with Python's Psutil Library | Medium](https://umeey.medium.com/system-monitoring-made-easy-with-pythons-psutil-library-4b9add95a443)

### Isolation Strategies
- [Resource constraints | Docker Docs](https://docs.docker.com/engine/containers/resource_constraints/)
- [Managing Docker Resources with Cgroups: A Practical Guide | Medium](https://medium.com/@maheshwar.ramkrushna/managing-docker-resources-with-cgroups-a-practical-guide-169289c80451)
- [Container Isolation: Understanding Namespaces and Control Groups in Docker - DEV Community](https://dev.to/hexshift/container-isolation-understanding-namespaces-and-control-groups-in-docker-318b)
- [Making Python respect Docker memory limits | Carlos Becker](https://carlosbecker.com/posts/python-docker-limits/)

### Framework Design
- [Locust - A modern load testing framework](https://locust.io/)
- [pytest-benchmark · PyPI](https://pypi.org/project/pytest-benchmark/)
- [GitHub - ionelmc/pytest-benchmark](https://github.com/ionelmc/pytest-benchmark)
- [Load Testing with Locust | Better Stack Community](https://betterstack.com/community/guides/testing/locust-explained/)

### Memory Profiling
- [tracemalloc — Trace memory allocations](https://docs.python.org/3/library/tracemalloc.html)
- [Memory profiling in Python with tracemalloc - Simple Talk](https://www.red-gate.com/simple-talk/development/python/memory-profiling-in-python-with-tracemalloc/)
- [Python: profile total memory allocated with tracemalloc - Adam Johnson](https://adamj.eu/tech/2024/08/30/python-profile-total-memory-tracemalloc/)
- [How To Trace Memory Allocation in Python - KDnuggets](https://www.kdnuggets.com/how-to-trace-memory-allocation-in-python)

### Statistical Analysis
- [Run a benchmark — pyperf](https://pyperf.readthedocs.io/en/latest/run_benchmark.html)
- [Analyze benchmark results — pyperf](https://pyperf.readthedocs.io/en/latest/analyze.html)
- [Python Benchmarking With pyperf - Super Fast Python](https://superfastpython.com/python-benchmark-pyperf/)
- [How To Measure And Improve Code Efficiency with Pytest Benchmark | Pytest with Eric](https://pytest-with-eric.com/pytest-best-practices/pytest-benchmark/)

### Resource Module
- [resource — Resource usage information](https://docs.python.org/3/library/resource.html)
- [Python Examples of resource.getrusage](https://www.programcreek.com/python/example/2580/resource.getrusage)
- [resource — System Resource Management](https://pymotw.com/3/resource/)

### Disk I/O Monitoring
- [psutil/scripts/iotop.py at master · giampaolo/psutil](https://github.com/giampaolo/psutil/blob/master/scripts/iotop.py)
- [Python disk IO logger in tutorial – JakeMakes](https://jakemakes.eu/python-disk-io-logger-in-tutorial/)

### Reproducibility
- [microbench · PyPI](https://pypi.org/project/microbench/)
- [Tune the system for benchmarks — pyperf](https://pyperf.readthedocs.io/en/latest/system.html)
- [GitHub - alubbock/microbench](https://github.com/alubbock/microbench)
- [Microbench: automated metadata management for systems biology benchmarking and reproducibility in Python | Bioinformatics](https://academic.oup.com/bioinformatics/article/38/20/4823/6674506)

### Timing Functions
- [Python time.time() vs time.perf_counter() - Super Fast Python](https://superfastpython.com/time-time-vs-time-perf_counter/)
- [PEP 418 – Add monotonic time, performance counter, and process time functions](https://peps.python.org/pep-0418/)
- [Benchmark Python with time.perf_counter() - Super Fast Python](https://superfastpython.com/benchmark-time-perf-counter/)
- [5 Built-In Timers in Python: Differences and Usages | Medium](https://medium.com/techtofreedom/5-built-in-timers-in-python-differences-and-usages-596c4c815457)

### SQLite Performance
- [Evaluating SQLite Performance by Testing All Parameters](https://ericdraken.com/sqlite-performance-testing/)
- [SQLite Database Speed Comparison](https://sqlite.org/speed.html)
- [Why SQLite Performance Tuning made Bencher 1200x Faster | Bencher](https://bencher.dev/learn/engineering/sqlite-performance-tuning/)
- [SQLite performance tuning - phiresky's blog](https://phiresky.github.io/blog/2020/sqlite-performance-tuning/)

### Database Schema Design
- [Relational Database schema design for metric storage - Stack Overflow](https://stackoverflow.com/questions/54823674/relational-database-schema-design-for-metric-storage)
- [Best practices for database benchmarking | Aerospike](https://aerospike.com/blog/best-practices-for-database-benchmarking/)

---

**End of Research Report**
