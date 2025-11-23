#!/usr/bin/env python3
"""
Shell Command Benchmarking Examples

This example demonstrates:
- Basic shell command benchmarking
- Different monitoring modes (snapshot vs continuous)
- Timeout handling
- Multiple commands comparison
- Process resource monitoring

Run this file directly:
    python examples/shell_commands.py

Note: Some examples use common Unix commands (find, ls, sleep)
"""

import sys
from plainbench.shell import benchmark_shell


def example_1_basic():
    """
    Example 1: Basic shell command benchmark.

    Uses snapshot monitoring (start and end measurements only).
    """
    print("Example 1: Basic shell command")
    print("-" * 60)

    result = benchmark_shell(
        command='ls -la',
        warmup=1,
        runs=5
    )

    print(f"  Command: ls -la")
    print(f"  Mean wall time: {result.statistics.wall_time.mean:.4f}s")
    print(f"  Std deviation: {result.statistics.wall_time.stddev:.4f}s")
    print(f"  Min: {result.statistics.wall_time.min:.4f}s")
    print(f"  Max: {result.statistics.wall_time.max:.4f}s")
    print()


def example_2_continuous_monitoring():
    """
    Example 2: Continuous monitoring of a longer-running command.

    Monitors process metrics at regular intervals.
    """
    print("Example 2: Continuous monitoring")
    print("-" * 60)

    result = benchmark_shell(
        command='find /usr -name "*.py" 2>/dev/null | head -100',
        warmup=0,
        runs=3,
        monitoring_mode='continuous',
        monitoring_interval=0.05  # Sample every 50ms
    )

    print(f"  Command: find /usr -name '*.py' (limited)")
    print(f"  Mean wall time: {result.statistics.wall_time.mean:.3f}s")
    print(f"  Peak memory: {result.statistics.peak_memory.mean / 1024 / 1024:.2f} MB")

    if result.statistics.cpu_percent.mean > 0:
        print(f"  Mean CPU usage: {result.statistics.cpu_percent.mean:.1f}%")

    print()


def example_3_timeout():
    """
    Example 3: Command with timeout.

    Demonstrates timeout handling for long-running commands.
    """
    print("Example 3: Command with timeout")
    print("-" * 60)

    try:
        result = benchmark_shell(
            command='sleep 0.2',  # Short sleep for demo
            timeout=1.0,  # 1 second timeout
            runs=3
        )
        print(f"  Command: sleep 0.2")
        print(f"  Mean wall time: {result.statistics.wall_time.mean:.3f}s")
        print(f"  All runs completed within timeout")
    except Exception as e:
        print(f"  Command timed out: {e}")

    print()


def example_4_capture_output():
    """
    Example 4: Benchmark with output capture.

    Captures stdout/stderr from the command.
    """
    print("Example 4: Capture command output")
    print("-" * 60)

    result = benchmark_shell(
        command='echo "Hello from PlainBench"',
        capture_output=True,
        runs=3
    )

    print(f"  Command: echo 'Hello from PlainBench'")
    print(f"  Mean wall time: {result.statistics.wall_time.mean:.5f}s")

    # Show output from first run
    if result.runs:
        first_run = result.runs[0]
        if hasattr(first_run, 'stdout') and first_run.stdout:
            print(f"  Output: {first_run.stdout.strip()}")

    print()


def example_5_compare_commands():
    """
    Example 5: Compare different command implementations.

    Benchmark multiple approaches to the same task.
    """
    print("Example 5: Compare different commands")
    print("-" * 60)

    # Approach 1: Using find
    result1 = benchmark_shell(
        command='find . -name "*.py" -type f 2>/dev/null | wc -l',
        runs=5
    )

    # Approach 2: Using ls and grep
    result2 = benchmark_shell(
        command='ls -R | grep -c "\.py$" 2>/dev/null || echo 0',
        runs=5
    )

    print(f"  Method 1 (find): {result1.statistics.wall_time.mean:.4f}s ± {result1.statistics.wall_time.stddev:.4f}s")
    print(f"  Method 2 (ls + grep): {result2.statistics.wall_time.mean:.4f}s ± {result2.statistics.wall_time.stddev:.4f}s")

    # Determine winner
    if result1.statistics.wall_time.mean < result2.statistics.wall_time.mean:
        diff = result2.statistics.wall_time.mean - result1.statistics.wall_time.mean
        speedup = result2.statistics.wall_time.mean / result1.statistics.wall_time.mean
        print(f"  Winner: find ({diff:.4f}s faster, {speedup:.2f}x speedup)")
    else:
        diff = result1.statistics.wall_time.mean - result2.statistics.wall_time.mean
        speedup = result1.statistics.wall_time.mean / result2.statistics.wall_time.mean
        print(f"  Winner: ls + grep ({diff:.4f}s faster, {speedup:.2f}x speedup)")

    print()


def example_6_resource_intensive():
    """
    Example 6: Monitor resource usage of intensive command.

    Demonstrates memory and CPU monitoring.
    """
    print("Example 6: Resource-intensive command monitoring")
    print("-" * 60)

    # Create a more resource-intensive command
    result = benchmark_shell(
        command='python3 -c "x = [i**2 for i in range(100000)]; print(len(x))"',
        warmup=1,
        runs=5,
        monitoring_mode='continuous',
        monitoring_interval=0.01,  # High-frequency sampling
        capture_output=False
    )

    print(f"  Command: Python list comprehension")
    print(f"  Mean wall time: {result.statistics.wall_time.mean:.4f}s")
    print(f"  Peak memory: {result.statistics.peak_memory.mean / 1024 / 1024:.2f} MB")

    if hasattr(result.statistics, 'io_read') and result.statistics.io_read.mean > 0:
        print(f"  I/O Read: {result.statistics.io_read.mean / 1024:.2f} KB")

    if hasattr(result.statistics, 'io_write') and result.statistics.io_write.mean > 0:
        print(f"  I/O Write: {result.statistics.io_write.mean / 1024:.2f} KB")

    print()


def example_7_multiple_runs():
    """
    Example 7: Statistical significance with many runs.

    More runs provide better statistical confidence.
    """
    print("Example 7: Statistical significance (many runs)")
    print("-" * 60)

    result = benchmark_shell(
        command='python3 -c "print(sum(range(10000)))"',
        warmup=5,  # More warmup for JIT
        runs=50,   # Many runs for better statistics
        capture_output=False
    )

    stats = result.statistics.wall_time
    print(f"  Command: Python sum calculation")
    print(f"  Runs: {len(result.runs)}")
    print(f"  Mean: {stats.mean:.5f}s")
    print(f"  Median: {stats.median:.5f}s")
    print(f"  Std dev: {stats.stddev:.5f}s")
    print(f"  95th percentile: {stats.p95:.5f}s")
    print(f"  99th percentile: {stats.p99:.5f}s")
    print(f"  Range: [{stats.min:.5f}s, {stats.max:.5f}s]")

    # Coefficient of variation (relative std dev)
    cv = (stats.stddev / stats.mean) * 100
    print(f"  Coefficient of variation: {cv:.2f}%")

    if cv < 5:
        print(f"  Conclusion: Very consistent results (CV < 5%)")
    elif cv < 10:
        print(f"  Conclusion: Reasonably consistent (CV < 10%)")
    else:
        print(f"  Conclusion: High variability (CV >= 10%)")

    print()


def main():
    """Run all shell command benchmark examples."""
    print("PlainBench Shell Command Benchmarking Examples")
    print("=" * 60)
    print()

    try:
        example_1_basic()
        example_2_continuous_monitoring()
        example_3_timeout()
        example_4_capture_output()
        example_5_compare_commands()
        example_6_resource_intensive()
        example_7_multiple_runs()

        print("=" * 60)
        print("All shell command benchmarks completed successfully!")
        print()
        print("Key takeaways:")
        print("  - Snapshot mode: Fast, minimal overhead")
        print("  - Continuous mode: Detailed resource tracking")
        print("  - Timeouts: Prevent runaway commands")
        print("  - Warmup: Important for consistent results")
        print("  - Many runs: Better statistical confidence")
        print()

    except ImportError as e:
        print(f"Error: {e}")
        print()
        print("Make sure PlainBench is installed:")
        print("  pip install -e .")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
