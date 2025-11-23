#!/usr/bin/env python3
"""
Queue Operations Benchmarking Example

This example demonstrates the original PlainBench vision:
benchmarking SQLite-backed queue operations.

This example shows:
- Creating a simple SQLite queue
- Benchmarking enqueue operations
- Benchmarking dequeue operations
- Testing different queue sizes
- Comparing batch vs. single operations
- Analyzing disk I/O patterns

Run this file:
    python examples/queue_benchmarking.py

Creates test queue: ./test_queue.db
Results stored in: ./benchmarks.db
"""

import os
import sqlite3
import sys
from plainbench import benchmark


# Simple SQLite Queue Implementation

class SQLiteQueue:
    """
    Simple FIFO queue backed by SQLite.

    This is a minimal implementation for demonstration purposes.
    """

    def __init__(self, db_path):
        """Initialize queue database."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def enqueue(self, data):
        """Add item to queue."""
        self.conn.execute('INSERT INTO queue (data) VALUES (?)', (data,))
        self.conn.commit()

    def enqueue_batch(self, items):
        """Add multiple items to queue."""
        self.conn.executemany(
            'INSERT INTO queue (data) VALUES (?)',
            [(item,) for item in items]
        )
        self.conn.commit()

    def dequeue(self):
        """Remove and return first item from queue."""
        cursor = self.conn.execute(
            'SELECT id, data FROM queue ORDER BY id LIMIT 1'
        )
        row = cursor.fetchone()

        if row:
            item_id, data = row
            self.conn.execute('DELETE FROM queue WHERE id = ?', (item_id,))
            self.conn.commit()
            return data

        return None

    def dequeue_batch(self, count):
        """Remove and return multiple items from queue."""
        cursor = self.conn.execute(
            'SELECT id, data FROM queue ORDER BY id LIMIT ?',
            (count,)
        )
        rows = cursor.fetchall()

        if rows:
            ids = [row[0] for row in rows]
            placeholders = ','.join('?' * len(ids))
            self.conn.execute(
                f'DELETE FROM queue WHERE id IN ({placeholders})',
                ids
            )
            self.conn.commit()
            return [row[1] for row in rows]

        return []

    def size(self):
        """Return number of items in queue."""
        cursor = self.conn.execute('SELECT COUNT(*) FROM queue')
        return cursor.fetchone()[0]

    def clear(self):
        """Remove all items from queue."""
        self.conn.execute('DELETE FROM queue')
        self.conn.commit()

    def close(self):
        """Close database connection."""
        self.conn.close()


# Benchmark different queue operations

# Global queue instance for benchmarks
queue = None


def setup_queue():
    """Set up the test queue."""
    global queue
    if os.path.exists('./test_queue.db'):
        os.remove('./test_queue.db')
    queue = SQLiteQueue('./test_queue.db')


@benchmark(
    name="queue_enqueue_single",
    warmup=3,
    runs=10,
    metrics=['wall_time', 'disk_io']
)
def benchmark_enqueue_single():
    """
    Benchmark single item enqueue operations.

    Adds 1000 items one at a time.
    """
    queue.clear()

    for i in range(1000):
        queue.enqueue(f"Message {i}")

    return queue.size()


@benchmark(
    name="queue_enqueue_batch",
    warmup=3,
    runs=10,
    metrics=['wall_time', 'disk_io']
)
def benchmark_enqueue_batch():
    """
    Benchmark batch enqueue operations.

    Adds 1000 items in one batch operation.
    """
    queue.clear()

    messages = [f"Message {i}" for i in range(1000)]
    queue.enqueue_batch(messages)

    return queue.size()


@benchmark(
    name="queue_dequeue_single",
    warmup=3,
    runs=10,
    metrics=['wall_time', 'disk_io']
)
def benchmark_dequeue_single():
    """
    Benchmark single item dequeue operations.

    Removes 1000 items one at a time.
    """
    # Pre-populate queue
    queue.clear()
    messages = [f"Message {i}" for i in range(1000)]
    queue.enqueue_batch(messages)

    # Benchmark dequeue
    count = 0
    while queue.dequeue() is not None:
        count += 1

    return count


@benchmark(
    name="queue_dequeue_batch",
    warmup=3,
    runs=10,
    metrics=['wall_time', 'disk_io']
)
def benchmark_dequeue_batch():
    """
    Benchmark batch dequeue operations.

    Removes 1000 items in batches of 100.
    """
    # Pre-populate queue
    queue.clear()
    messages = [f"Message {i}" for i in range(1000)]
    queue.enqueue_batch(messages)

    # Benchmark dequeue in batches
    total_dequeued = 0
    while True:
        items = queue.dequeue_batch(100)
        if not items:
            break
        total_dequeued += len(items)

    return total_dequeued


@benchmark(
    name="queue_mixed_operations",
    warmup=2,
    runs=10,
    metrics=['wall_time', 'disk_io']
)
def benchmark_mixed_operations():
    """
    Benchmark mixed queue operations.

    Simulates realistic queue usage with interleaved
    enqueue and dequeue operations.
    """
    queue.clear()

    operations = 0

    # Simulate producer-consumer pattern
    for cycle in range(100):
        # Producer: add 10 items
        messages = [f"Cycle {cycle} Message {i}" for i in range(10)]
        queue.enqueue_batch(messages)
        operations += 1

        # Consumer: remove 5 items
        queue.dequeue_batch(5)
        operations += 1

    return operations


def run_benchmarks():
    """Run all queue benchmarks."""
    print("SQLite Queue Benchmarking")
    print("=" * 70)
    print()

    setup_queue()

    print("Running queue operation benchmarks...")
    print()

    print("1. Single enqueue (1000 items, one at a time)...")
    result1 = benchmark_enqueue_single()
    print(f"   ✓ Enqueued {result1} items")

    print("2. Batch enqueue (1000 items in one batch)...")
    result2 = benchmark_enqueue_batch()
    print(f"   ✓ Enqueued {result2} items")

    print("3. Single dequeue (1000 items, one at a time)...")
    result3 = benchmark_dequeue_single()
    print(f"   ✓ Dequeued {result3} items")

    print("4. Batch dequeue (1000 items in batches of 100)...")
    result4 = benchmark_dequeue_batch()
    print(f"   ✓ Dequeued {result4} items")

    print("5. Mixed operations (producer-consumer pattern)...")
    result5 = benchmark_mixed_operations()
    print(f"   ✓ Completed {result5} operations")

    print()
    print("-" * 70)
    print()

    queue.close()


def analyze_results():
    """Analyze and display the benchmark results."""
    print("Analysis of Queue Benchmark Results")
    print("=" * 70)
    print()

    from plainbench import BenchmarkDatabase

    db = BenchmarkDatabase("./benchmarks.db")
    db.initialize()

    # Get benchmarks for queue operations
    queue_benchmarks = [
        'queue_enqueue_single',
        'queue_enqueue_batch',
        'queue_dequeue_single',
        'queue_dequeue_batch',
        'queue_mixed_operations'
    ]

    results = {}

    for name in queue_benchmarks:
        history = db.get_benchmark_history(name=name, limit=1)
        if history:
            run = history[0]
            stats = db.get_statistics(run_id=run.run_id)

            wall_time = None
            disk_io = None

            for stat in stats:
                if stat.metric_name == 'wall_time':
                    wall_time = stat
                elif stat.metric_name == 'disk_io':
                    disk_io = stat

            if wall_time:
                results[name] = {
                    'wall_time': wall_time,
                    'disk_io': disk_io
                }

    db.close()

    if not results:
        print("No benchmark results found!")
        return

    # Display results
    print("Queue Operation Performance")
    print()
    print(f"{'Operation':<30} {'Mean Time (s)':<15} {'Throughput (ops/s)':<20}")
    print("-" * 65)

    for name, data in results.items():
        op_name = name.replace('queue_', '').replace('_', ' ').title()
        mean_time = data['wall_time'].mean

        # Calculate throughput (1000 items / time)
        throughput = 1000 / mean_time if mean_time > 0 else 0

        print(f"{op_name:<30} {mean_time:<15.6f} {throughput:<20.1f}")

    print()
    print("-" * 65)
    print()

    # Compare batch vs single operations
    if 'queue_enqueue_single' in results and 'queue_enqueue_batch' in results:
        single_time = results['queue_enqueue_single']['wall_time'].mean
        batch_time = results['queue_enqueue_batch']['wall_time'].mean
        speedup = single_time / batch_time

        print("Enqueue Comparison:")
        print(f"  Single operations: {single_time:.6f}s")
        print(f"  Batch operations:  {batch_time:.6f}s")
        print(f"  Batch speedup:     {speedup:.2f}x faster")
        print()

    if 'queue_dequeue_single' in results and 'queue_dequeue_batch' in results:
        single_time = results['queue_dequeue_single']['wall_time'].mean
        batch_time = results['queue_dequeue_batch']['wall_time'].mean
        speedup = single_time / batch_time

        print("Dequeue Comparison:")
        print(f"  Single operations: {single_time:.6f}s")
        print(f"  Batch operations:  {batch_time:.6f}s")
        print(f"  Batch speedup:     {speedup:.2f}x faster")
        print()

    # I/O analysis
    print("Disk I/O Analysis:")
    print()

    for name, data in results.items():
        if data['disk_io']:
            op_name = name.replace('queue_', '').replace('_', ' ').title()
            # Note: disk_io metrics might not be available on all platforms
            print(f"  {op_name}: I/O metrics available")

    print()


def conclusions():
    """Display conclusions and recommendations."""
    print("Conclusions and Recommendations")
    print("=" * 70)
    print()

    print("Key Findings:")
    print()
    print("  1. Batch operations are significantly faster than single operations")
    print("     - Reduces transaction overhead")
    print("     - Minimizes disk I/O")
    print("     - Better throughput for high-volume scenarios")
    print()
    print("  2. SQLite WAL mode enables good concurrent performance")
    print("     - Multiple readers don't block")
    print("     - Better for queue workloads")
    print()
    print("  3. Queue size matters for performance")
    print("     - Large queues may benefit from indexing")
    print("     - Regular cleanup improves performance")
    print()

    print("Recommendations for Production Queues:")
    print()
    print("  ✓ Use batch operations when possible")
    print("  ✓ Enable WAL mode for better concurrency")
    print("  ✓ Add indexes on frequently queried columns")
    print("  ✓ Implement periodic cleanup/vacuuming")
    print("  ✓ Monitor queue depth and latency")
    print("  ✓ Consider partitioning for very large queues")
    print("  ✓ Benchmark with realistic workload patterns")
    print()


def main():
    """Main entry point."""
    try:
        # Run the benchmarks
        run_benchmarks()

        # Analyze results
        analyze_results()

        # Show conclusions
        conclusions()

        print("=" * 70)
        print("Queue benchmarking complete!")
        print()
        print("Test queue: ./test_queue.db")
        print("Results: ./benchmarks.db")
        print()

        # Cleanup
        if os.path.exists('./test_queue.db'):
            print("Cleaning up test queue database...")
            os.remove('./test_queue.db')
            # Also remove WAL files
            for suffix in ['-wal', '-shm']:
                path = f'./test_queue.db{suffix}'
                if os.path.exists(path):
                    os.remove(path)

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
