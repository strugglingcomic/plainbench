#!/usr/bin/env python3
"""
Isolation Strategy Comparison Example

This example demonstrates:
- The three isolation levels (minimal, moderate, maximum)
- How isolation affects reproducibility
- Comparing the same workload with different isolation
- Analyzing variance and consistency

Run this file directly:
    python examples/isolation_comparison.py

Results stored in ./benchmarks.db
"""

import sys
from plainbench import benchmark, BenchmarkDatabase


# The same computational workload benchmarked with different isolation levels

@benchmark(
    name="workload_minimal",
    isolation="minimal",
    runs=20,
    warmup=3
)
def compute_with_minimal_isolation(n=50000):
    """
    Minimal isolation: Basic GC control only.

    - Garbage collection disabled during measurement
    - No CPU pinning or priority changes
    - Fastest, but most variable
    - Good for quick comparisons during development
    """
    return sum(i**2 for i in range(n))


@benchmark(
    name="workload_moderate",
    isolation="moderate",
    runs=20,
    warmup=3
)
def compute_with_moderate_isolation(n=50000):
    """
    Moderate isolation: CPU pinning + priority + GC control.

    - CPU affinity set to specific cores
    - Process priority increased (if permissions allow)
    - PYTHONHASHSEED set for reproducibility
    - GC disabled during measurement
    - Better reproducibility, minimal overhead
    - Good for CI/CD and performance testing
    """
    return sum(i**2 for i in range(n))


@benchmark(
    name="workload_maximum",
    isolation="maximum",
    runs=20,
    warmup=3
)
def compute_with_maximum_isolation(n=50000):
    """
    Maximum isolation: Full environment cleanup.

    - Subprocess execution
    - Environment variable cleanup
    - System state validation
    - Comprehensive isolation checks
    - Best reproducibility, highest overhead
    - Ideal for research and regression tracking
    """
    return sum(i**2 for i in range(n))


def run_isolation_comparison():
    """
    Run the same workload with all three isolation levels
    and compare the results.
    """
    print("PlainBench Isolation Strategy Comparison")
    print("=" * 70)
    print()
    print("Running the same workload with three different isolation levels:")
    print("  1. Minimal   - Basic GC control")
    print("  2. Moderate  - + CPU pinning, priority")
    print("  3. Maximum   - + subprocess, environment cleanup")
    print()
    print("Each benchmark runs 20 times after 3 warmup iterations")
    print("=" * 70)
    print()

    # Run all three benchmarks
    print("Running benchmark with MINIMAL isolation...")
    result_minimal = compute_with_minimal_isolation()
    print(f"  Completed: result = {result_minimal}")
    print()

    print("Running benchmark with MODERATE isolation...")
    result_moderate = compute_with_moderate_isolation()
    print(f"  Completed: result = {result_moderate}")
    print()

    print("Running benchmark with MAXIMUM isolation...")
    result_maximum = compute_with_maximum_isolation()
    print(f"  Completed: result = {result_maximum}")
    print()

    print("-" * 70)
    print()

    return result_minimal, result_moderate, result_maximum


def analyze_results():
    """
    Query and analyze the benchmark results from the database.
    """
    print("Analyzing Results from Database")
    print("=" * 70)
    print()

    try:
        db = BenchmarkDatabase("./benchmarks.db")
        db.initialize()

        # Get the three most recent runs
        recent_runs = db.get_all_runs(limit=3)

        if len(recent_runs) < 3:
            print("Error: Not enough benchmark runs found in database")
            print("Make sure to run the benchmarks first")
            db.close()
            return

        # Sort by name to get consistent ordering
        run_data = {}
        for run in recent_runs:
            measurements = db.get_measurements(run_id=run.run_id)
            stats = db.get_statistics(run_id=run.run_id)
            run_data[run.benchmark_name] = {
                'run': run,
                'measurements': measurements,
                'stats': stats
            }

        db.close()

        # Display results for each isolation level
        for name in ['workload_minimal', 'workload_moderate', 'workload_maximum']:
            if name not in run_data:
                continue

            data = run_data[name]
            stats = data['stats']

            # Find wall_time statistics
            wall_time_stats = None
            for stat in stats:
                if stat.metric_name == 'wall_time':
                    wall_time_stats = stat
                    break

            if not wall_time_stats:
                continue

            isolation_level = name.replace('workload_', '').upper()
            print(f"{isolation_level} Isolation:")
            print(f"  Mean:   {wall_time_stats.mean:.6f}s")
            print(f"  Median: {wall_time_stats.median:.6f}s")
            print(f"  Stddev: {wall_time_stats.stddev:.6f}s")
            print(f"  Min:    {wall_time_stats.min:.6f}s")
            print(f"  Max:    {wall_time_stats.max:.6f}s")
            print(f"  95th percentile: {wall_time_stats.p95:.6f}s")

            # Coefficient of Variation (relative standard deviation)
            cv = (wall_time_stats.stddev / wall_time_stats.mean) * 100
            print(f"  Coefficient of Variation: {cv:.2f}%")
            print()

        print("-" * 70)
        print()

        # Summary and insights
        print("Isolation Level Comparison:")
        print()

        # Get CV for each level
        cvs = {}
        for name in ['workload_minimal', 'workload_moderate', 'workload_maximum']:
            if name in run_data:
                for stat in run_data[name]['stats']:
                    if stat.metric_name == 'wall_time':
                        cv = (stat.stddev / stat.mean) * 100
                        cvs[name] = cv
                        break

        print("Reproducibility (lower CV = more consistent):")
        for name, cv in sorted(cvs.items(), key=lambda x: x[1]):
            level = name.replace('workload_', '').capitalize()
            stars = '*' * int(10 - (cv * 2))  # Visual indicator
            print(f"  {level:10s}: {cv:5.2f}% {stars}")

        print()
        print("Interpretation:")
        print("  - Lower CV means more consistent/reproducible results")
        print("  - Higher isolation typically = lower CV but more overhead")
        print("  - Choose isolation level based on your needs:")
        print("      * Minimal: Quick development comparisons")
        print("      * Moderate: CI/CD and performance testing")
        print("      * Maximum: Research and critical benchmarks")
        print()

    except Exception as e:
        print(f"Error analyzing results: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    try:
        # Run the benchmarks
        run_isolation_comparison()

        # Analyze and display results
        analyze_results()

        print("=" * 70)
        print("Isolation comparison complete!")
        print()
        print("Key Findings:")
        print("  - All isolation levels produce the same computational result")
        print("  - Higher isolation typically shows lower variance")
        print("  - Maximum isolation has the most overhead but best reproducibility")
        print("  - Choose isolation based on your requirements")
        print()
        print("Database: ./benchmarks.db")
        print()

    except ImportError as e:
        print(f"Error: {e}")
        print()
        print("Make sure PlainBench is installed:")
        print("  pip install -e .")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
