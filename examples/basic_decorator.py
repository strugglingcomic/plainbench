#!/usr/bin/env python3
"""
Basic PlainBench Decorator Usage Examples

This example demonstrates:
- Simple decorator usage
- Different isolation levels
- Custom metrics selection
- Multiple function benchmarking
- Database storage

Run this file directly to see the benchmarks in action:
    python examples/basic_decorator.py

Results are stored in ./benchmarks.db
"""

import time
from plainbench import benchmark


# Example 1: Basic decorator with defaults
@benchmark()
def simple_sum(n):
    """
    Simple benchmark with default settings.

    Defaults:
    - warmup: 3 iterations
    - runs: 10 iterations
    - metrics: ['wall_time', 'cpu_time', 'python_memory']
    - isolation: 'minimal'
    """
    return sum(range(n))


# Example 2: Custom warmup and runs
@benchmark(warmup=5, runs=20)
def list_comprehension(n):
    """
    Benchmark with custom warmup and measurement runs.

    More runs = better statistical confidence
    More warmup = warmer caches and JIT
    """
    return [i**2 for i in range(n)]


# Example 3: Specific metrics
@benchmark(
    name="memory_intensive",
    metrics=['wall_time', 'python_memory'],
    warmup=2,
    runs=5
)
def create_large_dict(n):
    """
    Benchmark focusing on memory metrics.

    We're only measuring wall time and Python memory usage
    to reduce measurement overhead.
    """
    return {i: str(i) * 100 for i in range(n)}


# Example 4: Multiple metrics
@benchmark(
    name="comprehensive_metrics",
    metrics=['wall_time', 'cpu_time', 'python_memory', 'process_memory'],
    runs=15
)
def string_operations(n):
    """
    Benchmark with comprehensive metrics.

    Measures:
    - wall_time: Total elapsed time
    - cpu_time: CPU time (excludes sleep)
    - python_memory: Python heap memory
    - process_memory: Total process memory (RSS)
    """
    result = []
    for i in range(n):
        result.append(f"Item {i}")
    return ''.join(result)


# Example 5: Named benchmark for easy identification
@benchmark(
    name="fibonacci_recursive",
    warmup=3,
    runs=10
)
def fibonacci(n):
    """
    Classic recursive fibonacci for demonstration.

    Named benchmarks make it easy to query results later.
    """
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)


# Example 6: Disable garbage collection during measurement
@benchmark(
    name="gc_disabled",
    disable_gc=True,
    runs=20
)
def allocation_heavy(n):
    """
    Benchmark with GC disabled during measurement.

    Useful for consistent timing when benchmarking
    allocation-heavy code.
    """
    return [list(range(100)) for _ in range(n)]


# Example 7: Custom database location
@benchmark(
    name="custom_db",
    database="./my_benchmarks.db",
    warmup=2,
    runs=5
)
def custom_database_example(n):
    """
    Store results in a custom database file.

    Useful for organizing different benchmark suites.
    """
    return sum(i**2 for i in range(n))


def main():
    """
    Run all benchmark examples.

    Expected output:
    - Each function runs normally and returns its result
    - Benchmark data is automatically stored in the database
    - No console output by default (silent operation)
    """
    print("PlainBench Basic Decorator Examples")
    print("=" * 60)
    print()

    print("Running Example 1: Simple sum with defaults...")
    result1 = simple_sum(10000)
    print(f"  Result: {result1}")
    print()

    print("Running Example 2: List comprehension with custom runs...")
    result2 = list_comprehension(5000)
    print(f"  Result length: {len(result2)}")
    print()

    print("Running Example 3: Memory-intensive operations...")
    result3 = create_large_dict(1000)
    print(f"  Created dict with {len(result3)} entries")
    print()

    print("Running Example 4: Comprehensive metrics...")
    result4 = string_operations(500)
    print(f"  Result length: {len(result4)} characters")
    print()

    print("Running Example 5: Recursive fibonacci...")
    result5 = fibonacci(15)
    print(f"  Fibonacci(15) = {result5}")
    print()

    print("Running Example 6: GC disabled during measurement...")
    result6 = allocation_heavy(100)
    print(f"  Created {len(result6)} lists")
    print()

    print("Running Example 7: Custom database location...")
    result7 = custom_database_example(10000)
    print(f"  Result: {result7}")
    print()

    print("=" * 60)
    print("All benchmarks completed!")
    print()
    print("Results stored in:")
    print("  - ./benchmarks.db (examples 1-6)")
    print("  - ./my_benchmarks.db (example 7)")
    print()
    print("Query results with:")
    print("  python -c \"")
    print("  from plainbench import BenchmarkDatabase")
    print("  db = BenchmarkDatabase('./benchmarks.db')")
    print("  db.initialize()")
    print("  runs = db.get_all_runs()")
    print("  for run in runs:")
    print("      print(f'Run {run.run_id}: {run.benchmark_name}')")
    print("  db.close()")
    print("  \"")


if __name__ == "__main__":
    main()
