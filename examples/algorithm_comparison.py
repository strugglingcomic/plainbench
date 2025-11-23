#!/usr/bin/env python3
"""
Algorithm Comparison Example

This example demonstrates a complete real-world benchmarking workflow:
- Comparing different sorting algorithm implementations
- Statistical analysis of results
- Detecting performance differences
- Best practices for algorithm benchmarking

Algorithms compared:
1. Python's built-in sorted() (Timsort)
2. Bubble sort (naive implementation)
3. Quick sort (recursive implementation)
4. Insertion sort

Run this file:
    python examples/algorithm_comparison.py

Results stored in ./benchmarks.db
"""

import random
import sys
from plainbench import benchmark, BenchmarkDatabase


# Algorithm implementations

@benchmark(
    name="sort_builtin",
    warmup=5,
    runs=20,
    metrics=['wall_time', 'cpu_time'],
    isolation='moderate'
)
def builtin_sort(data):
    """
    Python's built-in sorted() - Timsort algorithm.

    Timsort is a hybrid stable sorting algorithm derived from
    merge sort and insertion sort.

    Expected: O(n log n) average and worst case
    """
    return sorted(data)


@benchmark(
    name="sort_bubble",
    warmup=3,
    runs=15,
    metrics=['wall_time', 'cpu_time'],
    isolation='moderate'
)
def bubble_sort(data):
    """
    Bubble sort - simple but inefficient.

    Expected: O(n²) average and worst case
    Note: Much slower than others, use small datasets!
    """
    arr = data.copy()
    n = len(arr)

    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break

    return arr


@benchmark(
    name="sort_quicksort",
    warmup=5,
    runs=20,
    metrics=['wall_time', 'cpu_time'],
    isolation='moderate'
)
def quick_sort(data):
    """
    Quicksort - efficient divide and conquer algorithm.

    Expected: O(n log n) average case, O(n²) worst case
    """
    def _quicksort(arr):
        if len(arr) <= 1:
            return arr

        pivot = arr[len(arr) // 2]
        left = [x for x in arr if x < pivot]
        middle = [x for x in arr if x == pivot]
        right = [x for x in arr if x > pivot]

        return _quicksort(left) + middle + _quicksort(right)

    return _quicksort(data.copy())


@benchmark(
    name="sort_insertion",
    warmup=3,
    runs=15,
    metrics=['wall_time', 'cpu_time'],
    isolation='moderate'
)
def insertion_sort(data):
    """
    Insertion sort - efficient for small datasets.

    Expected: O(n²) average and worst case
    But efficient for small or nearly-sorted data
    """
    arr = data.copy()

    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1

        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1

        arr[j + 1] = key

    return arr


def run_benchmarks():
    """Run all sorting algorithm benchmarks."""
    print("Algorithm Comparison: Sorting Algorithms")
    print("=" * 70)
    print()

    # Test with different data sizes
    # Note: Bubble sort and insertion sort are O(n²), so use smaller data
    small_size = 100
    medium_size = 1000

    print(f"Testing with two dataset sizes:")
    print(f"  Small:  {small_size} elements (all algorithms)")
    print(f"  Medium: {medium_size} elements (efficient algorithms only)")
    print()

    # Create test data
    small_data = [random.randint(1, 1000) for _ in range(small_size)]
    medium_data = [random.randint(1, 10000) for _ in range(medium_size)]

    print("Running benchmarks with SMALL dataset ({} elements)".format(small_size))
    print("-" * 70)

    # Test all algorithms with small dataset
    print("  1. Built-in sort (Timsort)...")
    result1 = builtin_sort(small_data)
    print(f"     ✓ Sorted {len(result1)} elements")

    print("  2. Bubble sort...")
    result2 = bubble_sort(small_data)
    print(f"     ✓ Sorted {len(result2)} elements")

    print("  3. Quicksort...")
    result3 = quick_sort(small_data)
    print(f"     ✓ Sorted {len(result3)} elements")

    print("  4. Insertion sort...")
    result4 = insertion_sort(small_data)
    print(f"     ✓ Sorted {len(result4)} elements")

    print()
    print("Running benchmarks with MEDIUM dataset ({} elements)".format(medium_size))
    print("-" * 70)

    # Test only efficient algorithms with medium dataset
    print("  1. Built-in sort (Timsort)...")
    builtin_sort(medium_data)
    print(f"     ✓ Sorted {len(medium_data)} elements")

    print("  2. Quicksort...")
    quick_sort(medium_data)
    print(f"     ✓ Sorted {len(medium_data)} elements")

    print()
    print("Skipping Bubble sort and Insertion sort for medium dataset")
    print("(O(n²) algorithms are too slow for {} elements)".format(medium_size))
    print()


def analyze_results():
    """Analyze and compare the benchmark results."""
    print("Analysis of Results")
    print("=" * 70)
    print()

    db = BenchmarkDatabase("./benchmarks.db")
    db.initialize()

    # Get benchmarks for sorting algorithms
    sort_benchmarks = [
        'sort_builtin',
        'sort_bubble',
        'sort_quicksort',
        'sort_insertion'
    ]

    results = {}

    for name in sort_benchmarks:
        history = db.get_benchmark_history(name=name, limit=1)
        if history:
            run = history[0]
            stats = db.get_statistics(run_id=run.run_id)

            wall_time = None
            for stat in stats:
                if stat.metric_name == 'wall_time':
                    wall_time = stat
                    break

            if wall_time:
                results[name] = {
                    'run': run,
                    'wall_time': wall_time
                }

    db.close()

    if not results:
        print("No benchmark results found!")
        print("Make sure to run the benchmarks first.")
        return

    # Display results
    print("Sorting Algorithm Performance Comparison")
    print()
    print(f"{'Algorithm':<20} {'Mean Time':<15} {'Std Dev':<15} {'Min':<12} {'Max':<12}")
    print("-" * 74)

    sorted_results = sorted(results.items(), key=lambda x: x[1]['wall_time'].mean)

    for name, data in sorted_results:
        wt = data['wall_time']
        algo_name = name.replace('sort_', '').capitalize()
        print(f"{algo_name:<20} {wt.mean:<15.6f} {wt.stddev:<15.6f} {wt.min:<12.6f} {wt.max:<12.6f}")

    print()
    print("-" * 74)
    print()

    # Calculate speedups
    if len(sorted_results) > 1:
        print("Speedup Analysis (vs. slowest algorithm):")
        print()

        slowest_time = sorted_results[-1][1]['wall_time'].mean
        fastest_name = sorted_results[0][0].replace('sort_', '').capitalize()
        fastest_time = sorted_results[0][1]['wall_time'].mean

        for name, data in sorted_results:
            algo_name = name.replace('sort_', '').capitalize()
            mean_time = data['wall_time'].mean
            speedup = slowest_time / mean_time

            stars = '*' * min(int(speedup), 50)
            print(f"  {algo_name:<15} {speedup:>6.2f}x faster {stars}")

        print()
        print(f"Winner: {fastest_name} ({slowest_time/fastest_time:.1f}x faster than slowest)")
        print()

    # Statistical insights
    print("Statistical Insights:")
    print()

    for name, data in sorted_results:
        algo_name = name.replace('sort_', '').capitalize()
        wt = data['wall_time']

        # Coefficient of variation
        cv = (wt.stddev / wt.mean) * 100

        print(f"  {algo_name}:")
        print(f"    Consistency (CV): {cv:.2f}%", end="")
        if cv < 5:
            print(" - Very consistent")
        elif cv < 10:
            print(" - Reasonably consistent")
        else:
            print(" - High variability")

        # Check for outliers (simple check using IQR approximation)
        range_ratio = (wt.max - wt.min) / wt.mean if wt.mean > 0 else 0
        print(f"    Range ratio: {range_ratio:.2f}", end="")
        if range_ratio > 0.5:
            print(" - Possible outliers")
        else:
            print(" - Stable")

        print()


def conclusions():
    """Display conclusions and best practices."""
    print("Conclusions and Best Practices")
    print("=" * 70)
    print()

    print("Key Findings:")
    print()
    print("  1. Algorithm Complexity Matters:")
    print("     - O(n log n) algorithms (Timsort, Quicksort) vastly outperform")
    print("       O(n²) algorithms (Bubble, Insertion) for larger datasets")
    print()
    print("  2. Built-in Functions Are Optimized:")
    print("     - Python's sorted() (Timsort) is highly optimized in C")
    print("     - Often faster than pure Python implementations")
    print()
    print("  3. Benchmark Design:")
    print("     - Use appropriate dataset sizes for each algorithm")
    print("     - Consider time complexity when choosing test sizes")
    print("     - Use isolation for consistent results")
    print()
    print("  4. Statistical Analysis:")
    print("     - Multiple runs provide confidence in results")
    print("     - Warmup iterations handle cache effects")
    print("     - Standard deviation indicates consistency")
    print()

    print("Best Practices for Algorithm Benchmarking:")
    print()
    print("  ✓ Use the same input data for all algorithms")
    print("  ✓ Test with multiple data sizes")
    print("  ✓ Consider worst-case, average-case, and best-case inputs")
    print("  ✓ Use isolation to reduce measurement noise")
    print("  ✓ Run sufficient iterations for statistical significance")
    print("  ✓ Verify correctness before benchmarking performance")
    print("  ✓ Document the testing methodology")
    print()


def main():
    """Main entry point."""
    try:
        # Verify results correctness before benchmarking
        print("Verifying algorithm correctness...")
        test_data = [5, 2, 8, 1, 9, 3]
        expected = [1, 2, 3, 5, 8, 9]

        assert builtin_sort.__wrapped__(test_data.copy()) == expected
        assert bubble_sort.__wrapped__(test_data.copy()) == expected
        assert quick_sort.__wrapped__(test_data.copy()) == expected
        assert insertion_sort.__wrapped__(test_data.copy()) == expected

        print("✓ All algorithms produce correct results")
        print()

        # Run the benchmarks
        run_benchmarks()

        # Analyze results
        analyze_results()

        # Show conclusions
        conclusions()

        print("=" * 70)
        print("Algorithm comparison complete!")
        print()
        print("Database: ./benchmarks.db")
        print("Use examples/database_queries.py to explore the data further")
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
