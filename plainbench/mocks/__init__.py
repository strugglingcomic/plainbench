"""
Mock data store implementations for PlainBench.

This module provides SQLite-backed mock implementations of common
external data stores (Postgres, Kafka, Redis) for benchmarking
application logic without the overhead of real external systems.

Example:
    from plainbench import benchmark
    from plainbench.mocks import use_mock_postgres

    @use_mock_postgres()
    @benchmark()
    def process_orders(db_conn):
        cursor = db_conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE status = 'pending'")
        orders = cursor.fetchall()
        # Business logic here
"""

from plainbench.mocks.base import LatencyConfig, MockDataStore
from plainbench.mocks.decorators import (
    use_mock_datastore,
    use_mock_kafka,
    use_mock_postgres,
    use_mock_redis,
)
from plainbench.mocks.kafka import MockKafka, MockKafkaConsumer, MockKafkaProducer
from plainbench.mocks.postgres import MockPostgres, MockPostgresConnection, MockPostgresCursor
from plainbench.mocks.redis import MockRedis

__all__ = [
    # Base classes
    "LatencyConfig",
    "MockDataStore",
    # Decorators
    "use_mock_postgres",
    "use_mock_kafka",
    "use_mock_redis",
    "use_mock_datastore",
    # Direct classes
    "MockPostgres",
    "MockPostgresConnection",
    "MockPostgresCursor",
    "MockKafka",
    "MockKafkaProducer",
    "MockKafkaConsumer",
    "MockRedis",
]
