# Mock Datastores

PlainBench's core trick: benchmark application logic against Postgres, Redis,
and Kafka **without running Postgres, Redis, or Kafka**. Each mock is backed
by SQLite (in-memory or file), speaks the client API you already use, and can
simulate realistic latencies — so comparative results transfer to the real
world without deploying anything.

## The mocks

| mock | mimics | highlights |
|------|--------|-----------|
| `MockPostgresConnection` | psycopg2 / DB-API 2.0 | cursors, transactions, `%s` params, Postgres→SQLite SQL translation (`SERIAL`, `NOW()`, `BOOLEAN`, `VARCHAR(n)`, ...) |
| `MockRedis` | redis-py | strings, lists, sets, hashes, TTL/expiry, pipelines |
| `MockKafkaProducer` / `MockKafkaConsumer` | kafka-python | topics, partitions, offsets, consumer groups, commits |

```python
from plainbench.mocks import MockPostgresConnection, MockRedis, MockKafkaProducer

with MockPostgresConnection() as db:
    cursor = db.cursor()
    cursor.execute("CREATE TABLE users (id SERIAL, name TEXT)")
    cursor.execute("INSERT INTO users (name) VALUES (%s)", ("Alice",))
    db.commit()

redis = MockRedis(decode_responses=True)
redis.set("greeting", "hello", ex=60)

producer = MockKafkaProducer()
producer.send("events", value=b"payload").get()
```

Use `database=":memory:"` (default) for isolated throwaway state, or a file
path to share data across connections, processes, and runs.

## Infrastructure profiles

Every mock operation models one client round trip. A **profile** says where
the real system would live; its network round-trip time is added to each
operation's typical processing latency:

| profile           | round trip | typical situation          |
|-------------------|-----------:|----------------------------|
| `in_process`      |        0ms | no network, raw mock speed |
| `same_host`       |     0.05ms | loopback / unix socket     |
| `same_zone`       |      0.5ms | same availability zone     |
| `same_region`     |        2ms | cross-AZ within a region   |
| `cross_region`    |       60ms | e.g. us-east ↔ us-west     |
| `cross_continent` |      150ms | e.g. us ↔ eu/apac          |

```python
from plainbench.mocks import MockRedis

redis = MockRedis(profile="cross_region")
redis.get("key")   # takes ~60.5ms, like it would in production
```

Profiles are defined in `plainbench.mocks.NETWORK_PROFILES`. The
per-operation processing latencies they extend live in
`DEFAULT_POSTGRES_LATENCIES`, `DEFAULT_REDIS_LATENCIES`, and
`DEFAULT_KAFKA_LATENCIES` (e.g. a simple indexed SELECT ≈ 1ms, a JOIN-heavy
query ≈ 10ms, a Redis GET ≈ 0.5ms). Sources for these figures are collected
in [research.md](research.md). A ±20% variance is applied per operation so
results aren't suspiciously smooth.

## Decorator injection

Each decorator builds the mock, injects it as the first argument, and closes
it afterwards:

```python
from plainbench import use_mock_postgres, use_mock_redis, use_mock_kafka

@use_mock_postgres(profile="same_region")
def query_orders(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE status = 'pending'")
    return cursor.fetchall()

@use_mock_kafka(inject_consumer=True, topics=["events"], profile="same_zone")
def roundtrip(producer, consumer):
    producer.send("events", value=b"x")
    producer.flush()
    return consumer.poll(max_records=10)
```

Latency control, in precedence order:

```python
@use_mock_redis(latency_config=my_config)                 # full control
@use_mock_redis(profile="cross_region")                   # named profile
@use_mock_redis(simulate_latency=True)                    # same-DC defaults
@use_mock_redis(profile="same_zone",
                custom_latencies={"get": 0.010})          # override one op
@use_mock_redis()                                         # no latency
```

Or build a config directly:

```python
from plainbench.mocks import LatencyConfig, DEFAULT_REDIS_LATENCIES

config = LatencyConfig.for_profile("same_region", DEFAULT_REDIS_LATENCIES)
config = LatencyConfig(enabled=True, default_latency=0.005, variance=0.4)
```

## Limitations — read this

The mocks give you *realistic comparative* numbers, not production numbers:

- **No contention or load effects**: one SQLite file is not a connection
  pool under saturation, a hot Redis shard, or a rebalancing Kafka cluster.
- **No tail modeling**: latencies vary ±20% around typical values; real p99s
  are uglier.
- **Postgres**: SQLite's planner, not Postgres's. Complex-query costs are
  modeled by latency class, not by actual plan cost. No server-side
  procedures, arrays, or JSONB operators.
- **Kafka**: no replication, no rebalancing, single-node semantics.
- **Redis**: core data structures only; no cluster mode, no Lua.

Use the mocks to *choose between designs*; validate the winner against real
infrastructure.
