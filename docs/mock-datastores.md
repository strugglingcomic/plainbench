# PlainBench Mock Data Stores

## Overview

PlainBench provides SQLite-backed mock implementations of common external data stores (Postgres, Kafka, Redis) for benchmarking application logic without the overhead and variability of real external systems.

## Motivation

When benchmarking application code that interacts with databases or message queues, you often face several challenges:

1. **Infrastructure Overhead**: Real databases add network latency, disk I/O, and process overhead
2. **Variability**: External systems introduce non-deterministic performance
3. **Setup Complexity**: Requires running and configuring external services
4. **Resource Usage**: Heavy resource consumption for benchmarking

PlainBench mocks solve these problems by using SQLite as a lightweight, in-process replacement that maintains API compatibility while removing external dependencies.

## Features

### Mock Postgres
- **DB-API 2.0 compatible** - Works like psycopg2
- **SQL dialect translation** - Converts Postgres SQL to SQLite
- **Transaction support** - Full COMMIT/ROLLBACK support
- **Cursor operations** - fetchone, fetchall, fetchmany
- **Context managers** - Connection and cursor cleanup

### Mock Kafka
- **kafka-python compatible API** - Producer and Consumer interfaces
- **Topic/partition management** - SQLite-backed message storage
- **Offset tracking** - Consumer group offset persistence
- **Message ordering** - Maintains message order per partition
- **Multiple consumers** - Consumer group coordination

### Mock Redis
- **redis-py compatible API** - Most common Redis operations
- **Data structures** - Strings, Lists, Sets, Hashes
- **TTL support** - Key expiration
- **Pipeline support** - Batched operations
- **Decode responses** - Automatic byte/string conversion

## Installation

The mock data stores are included with PlainBench core:

```python
from plainbench import benchmark
from plainbench.mocks import use_mock_postgres, use_mock_kafka, use_mock_redis
```

## Quick Start

### Mock Postgres Example

```python
from plainbench import benchmark
from plainbench.mocks import use_mock_postgres

@use_mock_postgres()
@benchmark(runs=10)
def process_orders(db_conn):
    """Benchmark order processing logic without real Postgres."""
    cursor = db_conn.cursor()

    # Your SQL queries work normally
    cursor.execute("SELECT * FROM orders WHERE status = ?", ("pending",))
    orders = cursor.fetchall()

    for order in orders:
        # Process each order
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?",
                      ("processed", order[0]))

    db_conn.commit()
    return len(orders)

# Run the benchmark
result = process_orders()
```

### Mock Kafka Example

```python
from plainbench import benchmark
from plainbench.mocks import use_mock_kafka

@use_mock_kafka()
@benchmark(runs=10)
def produce_events(producer):
    """Benchmark event production without real Kafka."""
    for i in range(1000):
        producer.send('events', value=f'event-{i}'.encode())
    producer.flush()
    return 1000

# With both producer and consumer
@use_mock_kafka(inject_consumer=True, topics=['events'])
@benchmark(runs=10)
def process_stream(producer, consumer):
    """Benchmark stream processing."""
    # Produce
    for i in range(100):
        producer.send('events', value=f'event-{i}'.encode())
    producer.flush()

    # Consume
    messages = consumer.poll(max_records=100)
    total = sum(len(records) for records in messages.values())
    consumer.commit()

    return total
```

### Mock Redis Example

```python
from plainbench import benchmark
from plainbench.mocks import use_mock_redis

@use_mock_redis(decode_responses=True)
@benchmark(runs=10)
def cache_operations(redis):
    """Benchmark cache operations without real Redis."""
    # Write to cache
    for i in range(100):
        redis.set(f'user:{i}', f'User {i}', ex=3600)

    # Read from cache
    hit_count = 0
    for i in range(100):
        if redis.get(f'user:{i}'):
            hit_count += 1

    return hit_count
```

## API Reference

### Decorators

#### `@use_mock_postgres()`

Injects a SQLite-backed Postgres connection.

**Parameters:**
- `database` (str): Database path (default: `:memory:`)
- `autocommit` (bool): Enable autocommit mode (default: `False`)
- `**config`: Additional connection parameters

**Injected Parameter:** `db_conn` - MockPostgresConnection instance

#### `@use_mock_kafka()`

Injects Kafka producer and/or consumer.

**Parameters:**
- `database` (str): Database path (default: `:memory:`)
- `inject_producer` (bool): Inject producer (default: `True`)
- `inject_consumer` (bool): Inject consumer (default: `False`)
- `topics` (list): Topics for consumer to subscribe to
- `group_id` (str): Consumer group ID (default: `"test-group"`)
- `**config`: Additional Kafka configuration

**Injected Parameters:**
- `producer` - MockKafkaProducer (if inject_producer=True)
- `consumer` - MockKafkaConsumer (if inject_consumer=True)

#### `@use_mock_redis()`

Injects a SQLite-backed Redis client.

**Parameters:**
- `database` (str): Database path (default: `:memory:`)
- `decode_responses` (bool): Decode byte responses to strings (default: `False`)
- `**config`: Additional Redis configuration

**Injected Parameter:** `redis` - MockRedis instance

#### `@use_mock_datastore()`

Generic decorator that dispatches to specific mocks.

**Parameters:**
- `datastore_type` (str): Type ('postgres', 'kafka', 'redis')
- `database` (str): Database path
- `**config`: Configuration for specific datastore

### Direct Class Usage

You can also use the mock classes directly without decorators:

```python
from plainbench.mocks import MockPostgresConnection, MockKafkaProducer, MockRedis

# Postgres
conn = MockPostgresConnection()
cursor = conn.cursor()
cursor.execute("SELECT 1")
conn.close()

# Kafka
producer = MockKafkaProducer()
producer.send('topic', value=b'message')
producer.flush()
producer.close()

# Redis
redis = MockRedis(decode_responses=True)
redis.set('key', 'value')
value = redis.get('key')
redis.close()
```

## Advanced Usage

### Shared Databases for Persistence

Use file-based databases to share data across benchmark runs:

```python
@use_mock_postgres(database='./test.db')
@benchmark(runs=10)
def query_users(db_conn):
    """Each run sees data from previous runs."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM users LIMIT 100")
    return len(cursor.fetchall())
```

### Complex Kafka Scenarios

```python
@use_mock_kafka(
    database='./kafka_bench.db',
    inject_consumer=True,
    topics=['orders', 'inventory']
)
@benchmark(runs=5)
def process_multiple_topics(producer, consumer):
    """Process messages from multiple topics."""
    # Produce to multiple topics
    producer.send('orders', value=b'order1')
    producer.send('inventory', value=b'item1')
    producer.flush()

    # Consume from all subscribed topics
    messages = consumer.poll(max_records=100)

    for (topic, partition), records in messages.items():
        print(f"Processing {len(records)} from {topic}")

    consumer.commit()
```

### Redis Pipeline Operations

```python
@use_mock_redis()
@benchmark(runs=10)
def batch_writes(redis):
    """Use pipelines for efficient batch operations."""
    with redis.pipeline() as pipe:
        for i in range(1000):
            pipe.set(f'key:{i}', f'value:{i}')
        results = pipe.execute()
    return len(results)
```

## SQL Dialect Translation

Mock Postgres automatically translates common Postgres SQL to SQLite:

| Postgres | SQLite |
|----------|--------|
| `%s` placeholders | `?` placeholders |
| `NOW()` | `CURRENT_TIMESTAMP` |
| `SERIAL` | `INTEGER PRIMARY KEY AUTOINCREMENT` |
| `BOOLEAN` | `INTEGER` (0/1) |
| `TRUE/FALSE` | `1/0` |
| `VARCHAR(n)` | `TEXT` |
| `TIMESTAMP` | `DATETIME` |
| `TEXT[]` | `TEXT` |

**Example:**

```python
# Postgres SQL
cursor.execute(
    "INSERT INTO users (name, active, created_at) VALUES (%s, %s, NOW())",
    ("Alice", True)
)

# Automatically translated to SQLite:
# INSERT INTO users (name, active, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)
# with params: ("Alice", 1)
```

## Configuration

Configure mock behavior in `plainbench.yaml`:

```yaml
mocks:
  postgres:
    enabled: true
    database: ":memory:"
    sql_dialect_translation: true
    autocommit: false

  kafka:
    enabled: true
    database: ":memory:"
    default_partitions: 1
    auto_offset_reset: "earliest"

  redis:
    enabled: true
    database: ":memory:"
    enable_ttl: true
    decode_responses: false
```

## Limitations

### Mock Postgres
- **No complex Postgres features**: PostGIS, full-text search, array operations
- **Limited type system**: SQLite has fewer data types
- **No stored procedures**: Functions and triggers not supported
- **RETURNING clause**: Limited support (SQLite 3.35+)

### Mock Kafka
- **Single partition per topic**: Multi-partition not yet implemented
- **No transactions**: Kafka transactions not supported
- **No compression**: Message compression not implemented
- **Simplified consumer groups**: Basic offset tracking only

### Mock Redis
- **Subset of commands**: Common operations only, not all Redis commands
- **No pub/sub**: Publish/subscribe not implemented
- **No clustering**: Single-node behavior only
- **No Lua scripts**: EVAL/EVALSHA not supported
- **Sorted sets limited**: Basic operations only

## Performance Comparison

Mock data stores provide significant performance benefits:

| Operation | Real Postgres | Mock Postgres | Speedup |
|-----------|--------------|---------------|---------|
| Simple SELECT | ~2ms | ~0.05ms | 40x |
| INSERT batch (100) | ~15ms | ~0.5ms | 30x |
| Transaction | ~5ms | ~0.1ms | 50x |

| Operation | Real Kafka | Mock Kafka | Speedup |
|-----------|-----------|------------|---------|
| Produce (1000 msg) | ~100ms | ~10ms | 10x |
| Consume (1000 msg) | ~80ms | ~8ms | 10x |

| Operation | Real Redis | Mock Redis | Speedup |
|-----------|-----------|------------|---------|
| SET (1000 keys) | ~50ms | ~5ms | 10x |
| GET (1000 keys) | ~40ms | ~4ms | 10x |
| Pipeline (1000 ops) | ~30ms | ~3ms | 10x |

## Use Cases

### 1. Benchmarking Business Logic

Focus on your application code, not database performance:

```python
@use_mock_postgres()
@benchmark(runs=100)
def calculate_user_stats(db_conn):
    """Benchmark statistical calculations, not database queries."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT score FROM user_scores")
    scores = [row[0] for row in cursor.fetchall()]

    # Benchmark this logic
    mean = sum(scores) / len(scores)
    variance = sum((x - mean) ** 2 for x in scores) / len(scores)

    return mean, variance
```

### 2. Testing Different Algorithms

Compare algorithm implementations with consistent data access:

```python
@use_mock_postgres(database='./test_data.db')
@benchmark(name="algorithm_a", runs=50)
def algorithm_a(db_conn):
    # Implementation A
    pass

@use_mock_postgres(database='./test_data.db')
@benchmark(name="algorithm_b", runs=50)
def algorithm_b(db_conn):
    # Implementation B
    pass

# Both use same data, fair comparison
```

### 3. CI/CD Performance Tests

Run benchmarks in CI without external dependencies:

```yaml
# .github/workflows/benchmark.yml
- name: Run benchmarks
  run: |
    # No database setup needed!
    python -m pytest benchmarks/ --benchmark-only
```

## Best Practices

### 1. Use In-Memory for Speed

For pure performance testing, use in-memory databases:

```python
@use_mock_postgres()  # Defaults to :memory:
@benchmark(runs=1000)
def fast_test(db_conn):
    # Maximum speed
    pass
```

### 2. Use Files for Realism

For realistic scenarios, use file databases:

```python
@use_mock_postgres(database='./bench.db')
@benchmark(runs=10)
def realistic_test(db_conn):
    # Includes disk I/O overhead
    pass
```

### 3. Warm Up Properly

Ensure proper warmup for SQLite:

```python
@use_mock_postgres()
@benchmark(warmup=5, runs=20)
def benchmark_with_warmup(db_conn):
    # SQLite caches, so warm up first
    pass
```

### 4. Close Connections

Decorators handle cleanup, but if using classes directly:

```python
conn = MockPostgresConnection()
try:
    # Use connection
    pass
finally:
    conn.close()  # Always close!
```

## Latency Simulation

PlainBench mocks can simulate realistic production latencies, allowing you to benchmark your application logic with network/database timing overhead without requiring actual infrastructure.

### Why Simulate Latency?

While SQLite-backed mocks are extremely fast, this doesn't always reflect production conditions. Latency simulation allows you to:

1. **Benchmark with realistic timing** - Understand how your code performs with production-like latencies
2. **Test different scenarios** - Compare same-datacenter vs cross-region performance
3. **Identify bottlenecks** - See how latency impacts your application logic
4. **Optimize strategies** - Compare optimization approaches under realistic conditions

### Default Latencies

PlainBench includes researched default latencies based on typical production deployments:

#### PostgreSQL (same datacenter)

| Operation | Default Latency | Typical Range |
|-----------|----------------|---------------|
| Simple SELECT (indexed) | 1ms | 0.5-5ms |
| Complex query (JOINs) | 10ms | 5-20ms |
| INSERT (single row) | 2ms | 1-3ms |
| INSERT (batch) | 15ms | 10-20ms |
| UPDATE | 2ms | 1-3ms |
| COMMIT | 3ms | 2-5ms |
| Connection | 2ms | 1-3ms |

#### Kafka (well-tuned cluster)

| Operation | Default Latency | Typical Range |
|-----------|----------------|---------------|
| Producer send (single) | 5ms | 1-10ms |
| Producer send (batch) | 15ms | 5-30ms |
| Producer flush | 10ms | 5-20ms |
| Consumer poll | 2ms | 1-5ms |
| Consumer commit | 5ms | 3-10ms |

#### Redis (same datacenter)

| Operation | Default Latency | Typical Range |
|-----------|----------------|---------------|
| GET | 0.5ms | 0.1-1ms |
| SET | 0.5ms | 0.1-1ms |
| MGET | 1ms | 0.5-2ms |
| LPUSH/RPUSH | 0.6ms | 0.3-1ms |
| LRANGE | 1ms | 0.5-2ms |
| HSET | 0.6ms | 0.3-1ms |
| HGETALL | 1ms | 0.5-2ms |
| Pipeline execute | 2ms | 1-3ms |

*Research sources:*
- [PostgreSQL Network Latency Impact](https://www.cybertec-postgresql.com/en/postgresql-network-latency-does-make-a-big-difference/)
- [Kafka Performance Metrics](https://developer.confluent.io/learn/kafka-performance/)
- [Redis Latency Diagnostics](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/)

### Basic Usage

Enable latency simulation with the `simulate_latency` parameter:

```python
from plainbench import benchmark
from plainbench.mocks import use_mock_postgres

@use_mock_postgres(simulate_latency=True)
@benchmark(runs=10)
def query_users(db_conn):
    """Benchmark with realistic ~1ms query latency."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = 1")
    return cursor.fetchone()

result = query_users()
print(f"Mean time: {result.mean*1000:.2f}ms")
# Output: Mean time: ~1.5ms (1ms query + overhead)
```

### Custom Latencies

Override default latencies for specific scenarios:

```python
# Simulate high-latency network (cross-region)
@use_mock_postgres(
    simulate_latency=True,
    custom_latencies={
        'execute_simple': 0.050,  # 50ms
        'commit': 0.020,          # 20ms
    }
)
@benchmark(runs=10)
def slow_network_query(db_conn):
    """Test performance with slow network."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM users")
    db_conn.commit()
    return cursor.fetchall()
```

### Advanced Configuration

For complete control, use `LatencyConfig`:

```python
from plainbench.mocks.base import LatencyConfig

# Create custom latency configuration
latency_config = LatencyConfig(
    enabled=True,
    variance=0.3,  # ±30% variance (simulates network jitter)
    operation_latencies={
        'execute_simple': 0.100,  # 100ms
        'execute_complex': 0.500,  # 500ms
        'commit': 0.050,           # 50ms
    }
)

@use_mock_postgres(latency_config=latency_config)
@benchmark(runs=10)
def worst_case_scenario(db_conn):
    """Test with worst-case latencies and jitter."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM users JOIN orders ON users.id = orders.user_id")
    return cursor.fetchall()
```

### Comparing Scenarios

Benchmark your code under different latency conditions:

```python
# No latency (pure application logic)
@use_mock_postgres(simulate_latency=False)
@benchmark(runs=100)
def baseline(db_conn):
    cursor = db_conn.cursor()
    for i in range(10):
        cursor.execute("SELECT * FROM users WHERE id = ?", (i,))
    return cursor.fetchone()

# Same datacenter
@use_mock_postgres(simulate_latency=True)
@benchmark(runs=100)
def same_datacenter(db_conn):
    cursor = db_conn.cursor()
    for i in range(10):
        cursor.execute("SELECT * FROM users WHERE id = ?", (i,))
    return cursor.fetchone()

# Cross-region
@use_mock_postgres(
    simulate_latency=True,
    custom_latencies={'execute_simple': 0.100}  # 100ms
)
@benchmark(runs=100)
def cross_region(db_conn):
    cursor = db_conn.cursor()
    for i in range(10):
        cursor.execute("SELECT * FROM users WHERE id = ?", (i,))
    return cursor.fetchone()

# Compare results
r1 = baseline()
r2 = same_datacenter()
r3 = cross_region()

print(f"Baseline (no latency): {r1.mean*1000:.2f}ms")
print(f"Same datacenter:       {r2.mean*1000:.2f}ms")
print(f"Cross-region:          {r3.mean*1000:.2f}ms")
```

### Kafka Latency

Kafka latency simulation:

```python
from plainbench.mocks import use_mock_kafka

@use_mock_kafka(simulate_latency=True)
@benchmark(runs=50)
def produce_messages(producer):
    """Each send adds ~5ms latency."""
    for i in range(10):
        producer.send('events', value=f'event-{i}'.encode())
    producer.flush()  # Adds ~10ms latency
    return 10

result = produce_messages()
print(f"Total time: {result.mean*1000:.2f}ms")
# Output: ~60ms (10 sends * 5ms + 10ms flush)
```

### Redis Latency

Redis latency simulation:

```python
from plainbench.mocks import use_mock_redis

@use_mock_redis(simulate_latency=True)
@benchmark(runs=100)
def cache_operations(redis):
    """Each operation adds ~0.5ms latency."""
    for i in range(20):
        redis.set(f'key:{i}', f'value:{i}')  # 20 * 0.5ms
    for i in range(20):
        redis.get(f'key:{i}')                # 20 * 0.5ms
    return 40

result = cache_operations()
print(f"Total time: {result.mean*1000:.2f}ms")
# Output: ~20ms (40 operations * 0.5ms)
```

### Best Practices

1. **Start without latency** - First benchmark pure application logic
2. **Add default latency** - Then test with realistic defaults
3. **Test scenarios** - Compare different network/infrastructure conditions
4. **Document assumptions** - Note which latencies you're using and why
5. **Validate with production** - Compare simulated results with real metrics

### When to Use Latency Simulation

**Use latency simulation when:**
- Testing network-sensitive code
- Comparing optimization strategies
- Understanding latency impact
- Preparing for production deployment
- Documenting performance characteristics

**Skip latency simulation when:**
- Benchmarking pure algorithmic performance
- Profiling CPU-bound code
- Testing in-memory operations
- You need maximum benchmark speed

### Performance Impact

Latency simulation uses `time.sleep()` which is very accurate but does add overhead:
- Disabled (default): No overhead
- Enabled: Adds configured latency ± variance
- Minimal CPU impact: Sleep is non-blocking

### Examples

See [`examples/mock_latency_simulation.py`](../examples/mock_latency_simulation.py) for comprehensive examples demonstrating:
- Baseline vs latency comparisons
- Custom latency scenarios
- Multi-datastore latency
- Worst-case testing

## Troubleshooting

### "No such table" errors

Ensure you create tables before querying:

```python
@use_mock_postgres()
def test(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER)")
    db_conn.commit()  # Commit DDL
    # Now safe to use table
```

### Consumer not receiving messages

When using file databases, ensure producer flushes:

```python
producer.send('topic', value=b'message')
producer.flush()  # Must flush!
```

### Transactions not working

Explicitly commit transactions:

```python
cursor.execute("INSERT INTO table VALUES (?)", (value,))
db_conn.commit()  # Don't forget!
```

## Examples

See [`examples/mock_datastores.py`](../examples/mock_datastores.py) for comprehensive examples of all three mock implementations.

## Future Enhancements

Planned features:

- **Mock Postgres**: PostGIS support, array operations
- **Mock Kafka**: Multi-partition support, transactions
- **Mock Redis**: Pub/sub, sorted set operations, Lua scripts
- **Mock MongoDB**: Document store operations
- **Mock Elasticsearch**: Search operations

## Contributing

Contributions are welcome! Areas for improvement:

- Additional SQL dialect translations
- More Redis commands
- Kafka multi-partition support
- Performance optimizations
- Additional mock data stores

## License

MIT License - same as PlainBench core.
