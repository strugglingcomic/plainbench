#!/usr/bin/env python3
"""
Database Queries and Analysis Example

This example demonstrates:
- Querying benchmark results from the database
- Comparing different benchmark runs
- Analyzing historical trends
- Exporting results for further analysis

Prerequisites:
    Run other examples first to populate the database:
    python examples/basic_decorator.py
    python examples/algorithm_comparison.py

Run this file:
    python examples/database_queries.py
"""

import sys
from datetime import datetime
from plainbench import BenchmarkDatabase


def example_1_latest_run():
    """Query the most recent benchmark run."""
    print("Example 1: Query Latest Run")
    print("-" * 70)

    db = BenchmarkDatabase("./benchmarks.db")
    db.initialize()

    latest_run = db.get_latest_run()

    if latest_run:
        print(f"  Run ID: {latest_run.run_id}")
        print(f"  Benchmark: {latest_run.benchmark_name}")
        print(f"  Timestamp: {latest_run.timestamp}")
        print(f"  Warmup runs: {latest_run.warmup_runs}")
        print(f"  Measurement runs: {latest_run.measurement_runs}")

        # Get git info if available
        if latest_run.git_commit:
            print(f"  Git commit: {latest_run.git_commit[:8]}")
            print(f"  Git branch: {latest_run.git_branch}")
            print(f"  Git dirty: {latest_run.git_dirty}")
    else:
        print("  No benchmark runs found in database")

    db.close()
    print()


def example_2_all_runs():
    """List all benchmark runs in the database."""
    print("Example 2: List All Runs")
    print("-" * 70)

    db = BenchmarkDatabase("./benchmarks.db")
    db.initialize()

    all_runs = db.get_all_runs()

    print(f"  Total runs: {len(all_runs)}")
    print()

    if all_runs:
        print(f"  {'ID':<5} {'Benchmark Name':<30} {'Runs':<6} {'Timestamp'}")
        print("  " + "-" * 68)

        for run in all_runs[:20]:  # Show first 20
            timestamp = run.timestamp[:19] if run.timestamp else 'N/A'
            print(f"  {run.run_id:<5} {run.benchmark_name:<30} {run.measurement_runs:<6} {timestamp}")

        if len(all_runs) > 20:
            print(f"  ... and {len(all_runs) - 20} more")

    db.close()
    print()


def example_3_measurements():
    """Get detailed measurements for a specific run."""
    print("Example 3: Query Measurements")
    print("-" * 70)

    db = BenchmarkDatabase("./benchmarks.db")
    db.initialize()

    latest_run = db.get_latest_run()

    if not latest_run:
        print("  No runs found")
        db.close()
        print()
        return

    measurements = db.get_measurements(run_id=latest_run.run_id)

    print(f"  Run ID: {latest_run.run_id}")
    print(f"  Benchmark: {latest_run.benchmark_name}")
    print(f"  Total measurements: {len(measurements)}")
    print()

    if measurements:
        # Group by metric type
        by_metric = {}
        for m in measurements:
            if m.metric_name not in by_metric:
                by_metric[m.metric_name] = []
            by_metric[m.metric_name].append(m.value)

        for metric_name, values in by_metric.items():
            print(f"  {metric_name}:")
            print(f"    Values: {len(values)}")
            print(f"    Sample: {values[:5]}")  # Show first 5
            print()

    db.close()
    print()


def example_4_statistics():
    """Query pre-computed statistics for a run."""
    print("Example 4: Query Statistics")
    print("-" * 70)

    db = BenchmarkDatabase("./benchmarks.db")
    db.initialize()

    latest_run = db.get_latest_run()

    if not latest_run:
        print("  No runs found")
        db.close()
        print()
        return

    stats = db.get_statistics(run_id=latest_run.run_id)

    print(f"  Run ID: {latest_run.run_id}")
    print(f"  Benchmark: {latest_run.benchmark_name}")
    print()

    for stat in stats:
        print(f"  {stat.metric_name}:")
        print(f"    Mean:   {stat.mean:.6f}")
        print(f"    Median: {stat.median:.6f}")
        print(f"    Stddev: {stat.stddev:.6f}")
        print(f"    Min:    {stat.min:.6f}")
        print(f"    Max:    {stat.max:.6f}")
        print(f"    P95:    {stat.p95:.6f}")
        print(f"    P99:    {stat.p99:.6f}")
        print()

    db.close()
    print()


def example_5_benchmark_history():
    """Get historical data for a specific benchmark."""
    print("Example 5: Benchmark History")
    print("-" * 70)

    db = BenchmarkDatabase("./benchmarks.db")
    db.initialize()

    # Get all unique benchmark names
    all_runs = db.get_all_runs()

    if not all_runs:
        print("  No runs found")
        db.close()
        print()
        return

    # Pick the most common benchmark name
    names = {}
    for run in all_runs:
        names[run.benchmark_name] = names.get(run.benchmark_name, 0) + 1

    if not names:
        print("  No benchmarks found")
        db.close()
        print()
        return

    benchmark_name = max(names.items(), key=lambda x: x[1])[0]

    history = db.get_benchmark_history(name=benchmark_name, limit=10)

    print(f"  Benchmark: {benchmark_name}")
    print(f"  Historical runs: {len(history)}")
    print()

    if history:
        print(f"  {'Run ID':<8} {'Timestamp':<20} {'Isolation':<12} {'Runs'}")
        print("  " + "-" * 68)

        for run in history:
            timestamp = run.timestamp[:19] if run.timestamp else 'N/A'
            isolation = run.isolation_level or 'N/A'
            print(f"  {run.run_id:<8} {timestamp:<20} {isolation:<12} {run.measurement_runs}")

    db.close()
    print()


def example_6_compare_runs():
    """Compare two benchmark runs using the analysis module."""
    print("Example 6: Compare Two Runs")
    print("-" * 70)

    try:
        from plainbench.analysis import compare_runs

        db = BenchmarkDatabase("./benchmarks.db")
        db.initialize()

        all_runs = db.get_all_runs()

        if len(all_runs) < 2:
            print("  Need at least 2 runs to compare")
            print("  Run some benchmarks first!")
            db.close()
            print()
            return

        # Compare the two most recent runs
        baseline_run = all_runs[1]
        current_run = all_runs[0]

        print(f"  Baseline: Run {baseline_run.run_id} ({baseline_run.benchmark_name})")
        print(f"  Current:  Run {current_run.run_id} ({current_run.benchmark_name})")
        print()

        comparison = compare_runs(
            database="./benchmarks.db",
            baseline_run_id=baseline_run.run_id,
            current_run_id=current_run.run_id
        )

        print(f"  Comparison Results:")
        print(f"    Same benchmark: {comparison.baseline_name == comparison.current_name}")
        print()

        # Show metric comparisons
        for metric_name, metric_comp in comparison.metrics.items():
            print(f"  {metric_name}:")
            print(f"    Baseline mean: {metric_comp.baseline_mean:.6f}")
            print(f"    Current mean:  {metric_comp.current_mean:.6f}")
            print(f"    Change:        {metric_comp.change_percent:+.2f}%")
            print(f"    Significant:   {metric_comp.is_significant}")

            if metric_comp.change_percent > 0:
                print(f"    Status:        SLOWER")
            elif metric_comp.change_percent < 0:
                print(f"    Status:        FASTER")
            else:
                print(f"    Status:        NO CHANGE")
            print()

        db.close()

    except ImportError:
        print("  Analysis module not available")
        print()


def example_7_detect_regressions():
    """Detect performance regressions."""
    print("Example 7: Detect Regressions")
    print("-" * 70)

    try:
        from plainbench.analysis import detect_regressions

        db = BenchmarkDatabase("./benchmarks.db")
        db.initialize()

        all_runs = db.get_all_runs()

        if len(all_runs) < 2:
            print("  Need at least 2 runs to detect regressions")
            db.close()
            print()
            return

        baseline_run = all_runs[1]
        current_run = all_runs[0]

        print(f"  Baseline: Run {baseline_run.run_id}")
        print(f"  Current:  Run {current_run.run_id}")
        print(f"  Threshold: 5% slowdown")
        print()

        regressions = detect_regressions(
            database="./benchmarks.db",
            baseline_run_id=baseline_run.run_id,
            current_run_id=current_run.run_id,
            threshold=0.05  # 5% threshold
        )

        if regressions:
            print(f"  REGRESSIONS DETECTED: {len(regressions)}")
            print()
            for regression in regressions:
                print(f"  Metric: {regression.metric_name}")
                print(f"    Slowdown: {regression.change_percent:+.2f}%")
                print(f"    Threshold exceeded: {abs(regression.change_percent) > 5}%")
                print()
        else:
            print("  No regressions detected!")
            print()

        db.close()

    except ImportError:
        print("  Analysis module not available")
        print()


def example_8_export_data():
    """Export benchmark data for external analysis."""
    print("Example 8: Export Data")
    print("-" * 70)

    import json

    db = BenchmarkDatabase("./benchmarks.db")
    db.initialize()

    latest_run = db.get_latest_run()

    if not latest_run:
        print("  No runs to export")
        db.close()
        print()
        return

    stats = db.get_statistics(run_id=latest_run.run_id)
    measurements = db.get_measurements(run_id=latest_run.run_id)

    # Build export data
    export_data = {
        'run_id': latest_run.run_id,
        'benchmark_name': latest_run.benchmark_name,
        'timestamp': latest_run.timestamp,
        'isolation_level': latest_run.isolation_level,
        'warmup_runs': latest_run.warmup_runs,
        'measurement_runs': latest_run.measurement_runs,
        'statistics': {},
        'measurements': {}
    }

    # Add statistics
    for stat in stats:
        export_data['statistics'][stat.metric_name] = {
            'mean': stat.mean,
            'median': stat.median,
            'stddev': stat.stddev,
            'min': stat.min,
            'max': stat.max,
            'p95': stat.p95,
            'p99': stat.p99
        }

    # Add measurements (grouped by metric)
    for m in measurements:
        if m.metric_name not in export_data['measurements']:
            export_data['measurements'][m.metric_name] = []
        export_data['measurements'][m.metric_name].append(m.value)

    # Save to file
    output_file = f"benchmark_run_{latest_run.run_id}.json"
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)

    print(f"  Exported run {latest_run.run_id} to: {output_file}")
    print(f"  Metrics: {len(export_data['statistics'])}")
    print(f"  Total measurements: {sum(len(v) for v in export_data['measurements'].values())}")

    db.close()
    print()


def main():
    """Run all database query examples."""
    print("PlainBench Database Queries and Analysis Examples")
    print("=" * 70)
    print()

    try:
        example_1_latest_run()
        example_2_all_runs()
        example_3_measurements()
        example_4_statistics()
        example_5_benchmark_history()
        example_6_compare_runs()
        example_7_detect_regressions()
        example_8_export_data()

        print("=" * 70)
        print("All database query examples completed!")
        print()
        print("Key Features Demonstrated:")
        print("  - Query latest and historical runs")
        print("  - Access measurements and statistics")
        print("  - Compare benchmark runs")
        print("  - Detect performance regressions")
        print("  - Export data for external analysis")
        print()
        print("Database location: ./benchmarks.db")
        print()

    except FileNotFoundError:
        print("Error: Database not found!")
        print()
        print("Run other examples first to create benchmark data:")
        print("  python examples/basic_decorator.py")
        print("  python examples/algorithm_comparison.py")
        print()
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
