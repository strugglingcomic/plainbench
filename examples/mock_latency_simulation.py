"""
Demonstrate latency simulation in mock data stores.

This example shows how to benchmark application logic with realistic production-like
latencies, even though using SQLite-backed mocks. This is useful for:
- Understanding the impact of network/database latency on your application
- Benchmarking under different latency scenarios (same datacenter vs cross-region)
- Testing performance with realistic timing without needing actual infrastructure
"""

import time

from plainbench import benchmark
from plainbench.mocks import use_mock_postgres, use_mock_kafka, use_mock_redis
from plainbench.mocks.base import LatencyConfig


# ============================================================================
# Example 1: PostgreSQL with default realistic latencies
# ============================================================================


@use_mock_postgres(simulate_latency=False)
@benchmark(runs=5)
def postgres_without_latency(db_conn):
    """Baseline: No latency simulation (instant SQLite operations)."""
    cursor = db_conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO users VALUES (1, 'Alice')")
    cursor.execute("SELECT * FROM users WHERE id = 1")
    result = cursor.fetchone()
    db_conn.commit()
    return result


@use_mock_postgres(simulate_latency=True)
@benchmark(runs=5)
def postgres_with_default_latency(db_conn):
    """With realistic same-datacenter PostgreSQL latencies."""
    cursor = db_conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO users VALUES (1, 'Alice')")
    cursor.execute("SELECT * FROM users WHERE id = 1")
    result = cursor.fetchone()
    db_conn.commit()
    return result


# ============================================================================
# Example 2: PostgreSQL with custom latencies (high latency network)
# ============================================================================


@use_mock_postgres(
    simulate_latency=True,
    custom_latencies={
        "execute_simple": 0.050,  # 50ms - simulate slow network
        "execute_complex": 0.100,  # 100ms - complex queries even slower
        "commit": 0.020,  # 20ms - commit latency
    },
)
@benchmark(runs=5)
def postgres_with_high_latency(db_conn):
    """Simulate high-latency environment (cross-region or overloaded DB)."""
    cursor = db_conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO users VALUES (1, 'Alice')")
    cursor.execute("SELECT * FROM users WHERE id = 1")
    result = cursor.fetchone()
    db_conn.commit()
    return result


# ============================================================================
# Example 3: Kafka with latency simulation
# ============================================================================


@use_mock_kafka(simulate_latency=False)
@benchmark(runs=10)
def kafka_without_latency(producer):
    """Kafka producer without latency simulation."""
    for i in range(10):
        producer.send("events", value=f"event-{i}".encode())
    producer.flush()
    return 10


@use_mock_kafka(simulate_latency=True)
@benchmark(runs=10)
def kafka_with_latency(producer):
    """Kafka producer with realistic latency (5ms per send, 10ms flush)."""
    for i in range(10):
        producer.send("events", value=f"event-{i}".encode())
    producer.flush()
    return 10


# ============================================================================
# Example 4: Redis with latency simulation
# ============================================================================


@use_mock_redis(simulate_latency=False)
@benchmark(runs=20)
def redis_without_latency(redis):
    """Redis operations without latency simulation."""
    for i in range(50):
        redis.set(f"key:{i}", f"value:{i}")
    for i in range(50):
        redis.get(f"key:{i}")
    return 50


@use_mock_redis(simulate_latency=True)
@benchmark(runs=20)
def redis_with_latency(redis):
    """Redis with realistic same-datacenter latency (0.5ms per operation)."""
    for i in range(50):
        redis.set(f"key:{i}", f"value:{i}")
    for i in range(50):
        redis.get(f"key:{i}")
    return 50


# ============================================================================
# Example 5: Advanced - Custom LatencyConfig object
# ============================================================================


# Create a custom latency configuration for testing worst-case scenarios
worst_case_latency = LatencyConfig(
    enabled=True,
    variance=0.5,  # 50% variance (high jitter)
    operation_latencies={
        "execute_simple": 0.100,  # 100ms
        "execute_complex": 0.500,  # 500ms
        "commit": 0.050,  # 50ms
    },
)


@use_mock_postgres(latency_config=worst_case_latency)
@benchmark(runs=3)
def postgres_worst_case_latency(db_conn):
    """Test with worst-case latency scenario."""
    cursor = db_conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO users VALUES (1, 'Alice')")
    cursor.execute("SELECT * FROM users WHERE id = 1")
    result = cursor.fetchone()
    db_conn.commit()
    return result


# ============================================================================
# Example 6: Comparing simple vs complex queries
# ============================================================================


@use_mock_postgres(simulate_latency=True)
@benchmark(runs=10)
def postgres_simple_query(db_conn):
    """Simple indexed query - should be ~1ms."""
    cursor = db_conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("SELECT * FROM users WHERE id = 1")
    return cursor.fetchone()


@use_mock_postgres(simulate_latency=True)
@benchmark(runs=10)
def postgres_complex_query(db_conn):
    """Complex query with JOIN - should be ~10ms."""
    cursor = db_conn.cursor()
    # Simulate complex query
    cursor.execute(
        """
        SELECT users.*, orders.total
        FROM users
        JOIN orders ON users.id = orders.user_id
        WHERE users.id = 1
        """
    )
    return cursor.fetchone()


# ============================================================================
# Main demonstration
# ============================================================================


def main():
    print("=" * 80)
    print("PlainBench - Mock Latency Simulation Examples")
    print("=" * 80)
    print()

    # Example 1: PostgreSQL baseline vs with latency
    print("--- PostgreSQL: No Latency vs Default Latency ---")
    print()
    print("Without latency simulation (instant SQLite):")
    result1 = postgres_without_latency()
    print(f"  Mean: {result1.mean*1000:.2f}ms | Median: {result1.median*1000:.2f}ms")
    print()

    print("With default latency simulation (~1ms simple query, ~3ms commit):")
    result2 = postgres_with_default_latency()
    print(f"  Mean: {result2.mean*1000:.2f}ms | Median: {result2.median*1000:.2f}ms")
    print(f"  Overhead from latency: ~{(result2.mean - result1.mean)*1000:.2f}ms")
    print()

    # Example 2: High latency scenario
    print("--- PostgreSQL: High Latency Network ---")
    print()
    result3 = postgres_with_high_latency()
    print(f"  Mean: {result3.mean*1000:.2f}ms | Median: {result3.median*1000:.2f}ms")
    print(f"  This simulates a slow network or overloaded database")
    print()

    # Example 3: Kafka
    print("--- Kafka: Latency Impact ---")
    print()
    print("Without latency:")
    result4 = kafka_without_latency()
    print(f"  Mean: {result4.mean*1000:.2f}ms | Median: {result4.median*1000:.2f}ms")
    print()

    print("With latency (5ms/send + 10ms flush):")
    result5 = kafka_with_latency()
    print(f"  Mean: {result5.mean*1000:.2f}ms | Median: {result5.median*1000:.2f}ms")
    print(f"  Expected latency: ~{10*5 + 10}ms (10 sends * 5ms + 10ms flush)")
    print()

    # Example 4: Redis
    print("--- Redis: Cache Operations ---")
    print()
    print("Without latency:")
    result6 = redis_without_latency()
    print(f"  Mean: {result6.mean*1000:.2f}ms | Median: {result6.median*1000:.2f}ms")
    print()

    print("With latency (0.5ms per operation):")
    result7 = redis_with_latency()
    print(f"  Mean: {result7.mean*1000:.2f}ms | Median: {result7.median*1000:.2f}ms")
    print(f"  Expected latency: ~{100*0.5}ms (100 operations * 0.5ms)")
    print()

    # Example 5: Worst case
    print("--- PostgreSQL: Worst Case Scenario ---")
    print()
    result8 = postgres_worst_case_latency()
    print(f"  Mean: {result8.mean*1000:.2f}ms | Median: {result8.median*1000:.2f}ms")
    print(f"  High variance simulates network jitter")
    print()

    # Example 6: Query complexity
    print("--- PostgreSQL: Simple vs Complex Queries ---")
    print()
    print("Simple indexed query (~1ms):")
    result9 = postgres_simple_query()
    print(f"  Mean: {result9.mean*1000:.2f}ms | Median: {result9.median*1000:.2f}ms")
    print()

    print("Complex query with JOIN (~10ms):")
    result10 = postgres_complex_query()
    print(f"  Mean: {result10.mean*1000:.2f}ms | Median: {result10.median*1000:.2f}ms")
    print(
        f"  Complex queries are ~{result10.mean/result9.mean:.1f}x slower (as expected)"
    )
    print()

    print("=" * 80)
    print("Summary:")
    print("=" * 80)
    print()
    print("Latency simulation allows you to:")
    print("  1. Benchmark with realistic production-like timing")
    print("  2. Test different network/infrastructure scenarios")
    print("  3. Understand latency impact on your application")
    print("  4. Compare optimization strategies under realistic conditions")
    print()
    print("All while using fast SQLite-backed mocks!")
    print()


if __name__ == "__main__":
    main()
