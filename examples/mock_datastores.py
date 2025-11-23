"""
Comprehensive examples of using PlainBench mock data stores.

This file demonstrates how to benchmark application logic using
SQLite-backed mocks for Postgres, Kafka, and Redis, removing the
overhead and variability of real external systems.
"""

from plainbench import benchmark
from plainbench.mocks import use_mock_kafka, use_mock_postgres, use_mock_redis


# ==============================================================================
# Mock Postgres Examples
# ==============================================================================


@use_mock_postgres()
@benchmark(name="postgres_order_processing", warmup=2, runs=5)
def process_orders_postgres(db_conn):
    """
    Benchmark order processing logic using mock Postgres.

    This benchmarks your SQL queries and business logic without
    the overhead of a real Postgres server.
    """
    cursor = db_conn.cursor()

    # Create orders table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            total REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Insert test data
    test_orders = [
        (1, 101, "pending", 99.99),
        (2, 102, "pending", 149.50),
        (3, 103, "processed", 75.00),
        (4, 101, "pending", 200.00),
        (5, 104, "pending", 50.25),
    ]

    cursor.executemany(
        "INSERT OR REPLACE INTO orders (id, customer_id, status, total) VALUES (?, ?, ?, ?)",
        test_orders,
    )
    db_conn.commit()

    # Query pending orders (the logic being benchmarked)
    cursor.execute("SELECT * FROM orders WHERE status = ?", ("pending",))
    pending_orders = cursor.fetchall()

    # Process each pending order
    processed_count = 0
    for order in pending_orders:
        order_id = order[0]
        # Simulate processing logic
        cursor.execute(
            "UPDATE orders SET status = ? WHERE id = ?", ("processed", order_id)
        )
        processed_count += 1

    db_conn.commit()

    return processed_count


@use_mock_postgres()
@benchmark(name="postgres_user_analytics", warmup=2, runs=5)
def user_analytics_postgres(db_conn):
    """
    Benchmark complex SQL analytics queries.

    This example shows how to benchmark aggregation and JOIN queries
    without a real database.
    """
    cursor = db_conn.cursor()

    # Create tables
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_events (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Insert test data
    for i in range(100):
        cursor.execute(
            "INSERT OR REPLACE INTO users (id, name, email) VALUES (?, ?, ?)",
            (i, f"User {i}", f"user{i}@example.com"),
        )

    for i in range(500):
        cursor.execute(
            "INSERT OR REPLACE INTO user_events (id, user_id, event_type) VALUES (?, ?, ?)",
            (i, i % 100, ["login", "purchase", "logout"][i % 3]),
        )

    db_conn.commit()

    # Analytics query (the logic being benchmarked)
    cursor.execute(
        """
        SELECT users.id, users.name, COUNT(user_events.id) as event_count
        FROM users
        LEFT JOIN user_events ON users.id = user_events.user_id
        WHERE user_events.event_type = ?
        GROUP BY users.id
        HAVING event_count > ?
        ORDER BY event_count DESC
        LIMIT 10
        """,
        ("purchase", 0),
    )

    top_users = cursor.fetchall()
    return len(top_users)


# ==============================================================================
# Mock Kafka Examples
# ==============================================================================


@use_mock_kafka()
@benchmark(name="kafka_event_production", warmup=2, runs=5)
def produce_events_kafka(producer):
    """
    Benchmark Kafka event production.

    This benchmarks your event serialization and production logic
    without a real Kafka cluster.
    """
    topic = "user-events"
    event_count = 1000

    # Produce events
    for i in range(event_count):
        key = f"user-{i % 100}".encode("utf-8")
        value = f'{{"event_id": {i}, "type": "click", "timestamp": "2024-01-01"}}'.encode(
            "utf-8"
        )

        future = producer.send(topic, value=value, key=key)
        # In real benchmarks, you might want to measure throughput
        # without waiting for each send

    # Ensure all messages are sent
    producer.flush()

    return event_count


@use_mock_kafka(inject_consumer=True, topics=["order-events"])
@benchmark(name="kafka_stream_processing", warmup=2, runs=5)
def process_event_stream_kafka(producer, consumer):
    """
    Benchmark Kafka stream processing (produce + consume).

    This benchmarks a complete event processing pipeline without
    a real Kafka cluster.
    """
    input_topic = "order-events"
    output_topic = "processed-orders"

    # Produce some input events
    for i in range(100):
        order_data = f'{{"order_id": {i}, "amount": {100 + i}}}'.encode("utf-8")
        producer.send(input_topic, value=order_data)

    producer.flush()

    # Consume and process events
    messages = consumer.poll(timeout_ms=1000, max_records=100)

    processed_count = 0
    for topic_partition, records in messages.items():
        for record in records:
            # Simulate processing logic
            order_data = record.value.decode("utf-8")

            # Produce processed result
            result = f'{{"processed": true, "data": {order_data}}}'.encode("utf-8")
            producer.send(output_topic, value=result)

            processed_count += 1

    producer.flush()
    consumer.commit()

    return processed_count


@use_mock_kafka(database="./kafka_benchmark.db", inject_consumer=True, topics=["queue"])
@benchmark(name="kafka_persistent_queue", warmup=1, runs=3)
def persistent_queue_benchmark(producer, consumer):
    """
    Benchmark with persistent SQLite database.

    This uses a shared database file, so messages persist across runs.
    Useful for realistic queue benchmarking scenarios.
    """
    # Add messages to queue
    for i in range(50):
        producer.send("queue", value=f"task-{i}".encode("utf-8"))
    producer.flush()

    # Process messages from queue (including from previous runs)
    messages = consumer.poll(max_records=10)

    processed = 0
    for records in messages.values():
        processed += len(records)

    consumer.commit()

    return processed


# ==============================================================================
# Mock Redis Examples
# ==============================================================================


@use_mock_redis(decode_responses=True)
@benchmark(name="redis_cache_operations", warmup=2, runs=5)
def cache_operations_redis(redis):
    """
    Benchmark Redis cache operations.

    This benchmarks cache lookups and writes without a real Redis server.
    """
    # Populate cache
    for i in range(100):
        redis.set(f"user:{i}", f"User {i}", ex=3600)

    # Benchmark cache reads
    hit_count = 0
    for i in range(100):
        value = redis.get(f"user:{i}")
        if value:
            hit_count += 1

    return hit_count


@use_mock_redis()
@benchmark(name="redis_queue_operations", warmup=2, runs=5)
def queue_operations_redis(redis):
    """
    Benchmark Redis list operations (queue).

    This benchmarks using Redis as a queue without a real server.
    """
    queue_name = "job-queue"

    # Add jobs to queue
    for i in range(100):
        redis.lpush(queue_name, f"job-{i}".encode("utf-8"))

    # Process jobs from queue
    processed = 0
    while True:
        job = redis.lrange(queue_name, -1, -1)
        if not job:
            break
        # In real Redis, you'd use RPOP
        # For simplicity, we just count
        processed += 1
        if processed >= 100:
            break

    return processed


@use_mock_redis(decode_responses=True)
@benchmark(name="redis_session_storage", warmup=2, runs=5)
def session_storage_redis(redis):
    """
    Benchmark Redis hash operations (session storage).

    This benchmarks using Redis hashes for session storage.
    """
    session_count = 50

    # Create sessions
    for i in range(session_count):
        session_id = f"session:{i}"
        redis.hset(session_id, "user_id", str(100 + i))
        redis.hset(session_id, "username", f"user{i}")
        redis.hset(session_id, "login_time", "2024-01-01T00:00:00")

    # Read sessions
    read_count = 0
    for i in range(session_count):
        session_id = f"session:{i}"
        session_data = redis.hgetall(session_id)
        if session_data:
            read_count += 1

    return read_count


@use_mock_redis()
@benchmark(name="redis_set_operations", warmup=2, runs=5)
def set_operations_redis(redis):
    """
    Benchmark Redis set operations.

    This benchmarks using Redis sets for tag/category management.
    """
    # Add items to sets
    for i in range(100):
        # Each item has multiple tags
        tags = [b"python", b"benchmark", b"redis"][: (i % 3) + 1]
        for tag in tags:
            redis.sadd(f"item:{i}:tags".encode("utf-8"), tag)

    # Query sets
    python_items = 0
    for i in range(100):
        tags = redis.smembers(f"item:{i}:tags".encode("utf-8"))
        if b"python" in tags:
            python_items += 1

    return python_items


@use_mock_redis()
@benchmark(name="redis_pipeline_operations", warmup=2, runs=5)
def pipeline_operations_redis(redis):
    """
    Benchmark Redis pipeline for batched operations.

    This benchmarks using Redis pipelines for efficient batch operations.
    """
    # Use pipeline for batch writes
    with redis.pipeline() as pipe:
        for i in range(1000):
            pipe.set(f"key:{i}".encode("utf-8"), f"value:{i}".encode("utf-8"))
        results = pipe.execute()

    # Batch reads (without pipeline for comparison)
    read_count = 0
    for i in range(1000):
        value = redis.get(f"key:{i}".encode("utf-8"))
        if value:
            read_count += 1

    return read_count


# ==============================================================================
# Comparison: With vs Without Mocks
# ==============================================================================


@benchmark(name="without_mock_computation", warmup=2, runs=5)
def pure_computation_without_mock():
    """
    Baseline: Pure computation without any data store.

    This is what you're actually benchmarking - the business logic,
    not the database overhead.
    """
    # Simulate the same computation as the Postgres example
    orders = [
        {"id": 1, "status": "pending", "total": 99.99},
        {"id": 2, "status": "pending", "total": 149.50},
        {"id": 3, "status": "processed", "total": 75.00},
        {"id": 4, "status": "pending", "total": 200.00},
        {"id": 5, "status": "pending", "total": 50.25},
    ]

    # Process pending orders
    processed_count = 0
    for order in orders:
        if order["status"] == "pending":
            order["status"] = "processed"
            processed_count += 1

    return processed_count


def main():
    """
    Run all mock datastore examples.

    This demonstrates the power of PlainBench mocks - you can benchmark
    your application logic without the overhead of real external systems.
    """
    print("=" * 80)
    print("PlainBench Mock Data Stores - Comprehensive Examples")
    print("=" * 80)

    print("\n🐘 Running Mock Postgres examples...")
    result1 = process_orders_postgres()
    print(f"   ✓ Processed {result1} orders")

    result2 = user_analytics_postgres()
    print(f"   ✓ Found {result2} top users")

    print("\n📨 Running Mock Kafka examples...")
    result3 = produce_events_kafka()
    print(f"   ✓ Produced {result3} events")

    result4 = process_event_stream_kafka()
    print(f"   ✓ Processed {result4} events from stream")

    result5 = persistent_queue_benchmark()
    print(f"   ✓ Processed {result5} messages from persistent queue")

    print("\n🔴 Running Mock Redis examples...")
    result6 = cache_operations_redis()
    print(f"   ✓ Cache hit count: {result6}")

    result7 = queue_operations_redis()
    print(f"   ✓ Processed {result7} jobs from queue")

    result8 = session_storage_redis()
    print(f"   ✓ Read {result8} sessions")

    result9 = set_operations_redis()
    print(f"   ✓ Found {result9} items with Python tag")

    result10 = pipeline_operations_redis()
    print(f"   ✓ Read {result10} keys after pipeline write")

    print("\n⚡ Running baseline (no mock)...")
    result11 = pure_computation_without_mock()
    print(f"   ✓ Processed {result11} orders (pure computation)")

    print("\n" + "=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)
    print("\nBenchmark results stored in: ./benchmarks.db")
    print("View results with: plainbench show")
    print("\nKey Benefits of Mock Data Stores:")
    print("  • No external dependencies required")
    print("  • Fast and deterministic benchmarks")
    print("  • Focus on business logic, not infrastructure")
    print("  • Easy to set up and tear down")
    print("  • Reproducible results")


if __name__ == "__main__":
    main()
