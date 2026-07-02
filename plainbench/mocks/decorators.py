"""Decorators for injecting mock data stores into benchmarked functions."""

import functools
from typing import Callable, Dict, Optional

from plainbench.mocks.base import LatencyConfig
from plainbench.mocks.kafka import (
    DEFAULT_KAFKA_LATENCIES,
    MockKafkaConsumer,
    MockKafkaProducer,
)
from plainbench.mocks.postgres import (
    DEFAULT_POSTGRES_LATENCIES,
    MockPostgresConnection,
)
from plainbench.mocks.redis import DEFAULT_REDIS_LATENCIES, MockRedis


def _resolve_latency_config(
    defaults: Dict[str, float],
    profile: Optional[str],
    simulate_latency: bool,
    latency_config: Optional[LatencyConfig],
    custom_latencies: Optional[Dict[str, float]],
) -> LatencyConfig:
    """
    Resolve the latency configuration for a mock decorator.

    Precedence: explicit latency_config > named profile > simulate_latency
    with defaults > disabled. custom_latencies overrides individual
    operations in the profile/default cases.
    """
    if latency_config is not None:
        return latency_config

    if profile is not None:
        config = LatencyConfig.for_profile(profile, defaults)
    elif simulate_latency:
        config = LatencyConfig(enabled=True, operation_latencies=defaults.copy())
    else:
        return LatencyConfig(enabled=False)

    if custom_latencies:
        config.operation_latencies.update(custom_latencies)
    return config


def use_mock_postgres(
    database: str = ":memory:",
    autocommit: bool = False,
    profile: Optional[str] = None,
    simulate_latency: bool = False,
    latency_config: Optional[LatencyConfig] = None,
    custom_latencies: Optional[Dict[str, float]] = None,
    **config,
) -> Callable:
    """
    Decorator that injects a MockPostgresConnection into the decorated function.

    Creates a SQLite-backed mock Postgres connection and injects it as the
    first parameter, allowing you to benchmark database logic without a
    real Postgres instance.

    Args:
        database: SQLite database path (default: in-memory)
        autocommit: Enable autocommit mode
        profile: Named infrastructure profile (e.g. 'same_zone',
            'cross_region') simulating where the database lives
        simulate_latency: Enable default same-datacenter latency simulation
        latency_config: Custom LatencyConfig (overrides profile/simulate_latency)
        custom_latencies: Dict of operation->latency overrides in seconds
        **config: Additional connection configuration

    Example:
        @use_mock_postgres(profile='same_region')
        def process_orders(db_conn):
            cursor = db_conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE status = 'pending'")
            return len(cursor.fetchall())
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            latency_cfg = _resolve_latency_config(
                DEFAULT_POSTGRES_LATENCIES,
                profile,
                simulate_latency,
                latency_config,
                custom_latencies,
            )
            mock_conn = MockPostgresConnection(
                database=database,
                autocommit=autocommit,
                latency_config=latency_cfg,
                **config,
            )
            try:
                return func(mock_conn, *args, **kwargs)
            finally:
                mock_conn.close()

        wrapper._mock_postgres = True
        wrapper._mock_database = database
        wrapper._mock_config = config
        return wrapper

    return decorator


def use_mock_kafka(
    database: str = ":memory:",
    inject_producer: bool = True,
    inject_consumer: bool = False,
    topics: Optional[list] = None,
    group_id: str = "test-group",
    profile: Optional[str] = None,
    simulate_latency: bool = False,
    latency_config: Optional[LatencyConfig] = None,
    custom_latencies: Optional[Dict[str, float]] = None,
    **config,
) -> Callable:
    """
    Decorator that injects MockKafkaProducer and/or MockKafkaConsumer.

    Creates SQLite-backed mock Kafka clients and injects them into the
    decorated function, allowing you to benchmark message processing logic
    without a real Kafka cluster.

    Args:
        database: SQLite database path (default: in-memory)
        inject_producer: Inject a producer (default: True)
        inject_consumer: Inject a consumer (default: False)
        topics: Topics to subscribe to (for consumer)
        group_id: Consumer group ID
        profile: Named infrastructure profile (e.g. 'same_zone',
            'cross_region') simulating where the cluster lives
        simulate_latency: Enable default same-datacenter latency simulation
        latency_config: Custom LatencyConfig (overrides profile/simulate_latency)
        custom_latencies: Dict of operation->latency overrides in seconds
        **config: Additional Kafka configuration

    Example:
        @use_mock_kafka(inject_consumer=True, topics=['events'])
        def process_events(producer, consumer):
            for i in range(100):
                producer.send('events', value=f'event-{i}'.encode())
            producer.flush()
            messages = consumer.poll(timeout_ms=1000, max_records=100)
            return sum(len(records) for records in messages.values())
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            latency_cfg = _resolve_latency_config(
                DEFAULT_KAFKA_LATENCIES,
                profile,
                simulate_latency,
                latency_config,
                custom_latencies,
            )

            producer = None
            consumer = None
            try:
                if inject_producer:
                    producer = MockKafkaProducer(
                        database=database, latency_config=latency_cfg, **config
                    )
                if inject_consumer:
                    consumer = MockKafkaConsumer(
                        *(topics or []),
                        database=database,
                        group_id=group_id,
                        latency_config=latency_cfg,
                        **config,
                    )

                if producer and consumer:
                    return func(producer, consumer, *args, **kwargs)
                elif producer:
                    return func(producer, *args, **kwargs)
                elif consumer:
                    return func(consumer, *args, **kwargs)
                else:
                    raise ValueError(
                        "Must inject at least producer or consumer "
                        "(inject_producer=True or inject_consumer=True)"
                    )
            finally:
                if producer:
                    producer.close()
                if consumer:
                    consumer.close()

        wrapper._mock_kafka = True
        wrapper._mock_database = database
        wrapper._mock_config = config
        return wrapper

    return decorator


def use_mock_redis(
    database: str = ":memory:",
    decode_responses: bool = False,
    profile: Optional[str] = None,
    simulate_latency: bool = False,
    latency_config: Optional[LatencyConfig] = None,
    custom_latencies: Optional[Dict[str, float]] = None,
    **config,
) -> Callable:
    """
    Decorator that injects a MockRedis client into the decorated function.

    Creates a SQLite-backed mock Redis client and injects it as the first
    parameter, allowing you to benchmark caching logic without a real
    Redis server.

    Args:
        database: SQLite database path (default: in-memory)
        decode_responses: Decode byte responses to strings
        profile: Named infrastructure profile (e.g. 'same_zone',
            'cross_region') simulating where the cache lives
        simulate_latency: Enable default same-datacenter latency simulation
        latency_config: Custom LatencyConfig (overrides profile/simulate_latency)
        custom_latencies: Dict of operation->latency overrides in seconds
        **config: Additional Redis configuration

    Example:
        @use_mock_redis(decode_responses=True, profile='same_zone')
        def cache_lookups(redis):
            for i in range(100):
                redis.set(f'user:{i}', f'User {i}', ex=60)
            return sum(1 for i in range(100) if redis.get(f'user:{i}'))
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            latency_cfg = _resolve_latency_config(
                DEFAULT_REDIS_LATENCIES,
                profile,
                simulate_latency,
                latency_config,
                custom_latencies,
            )
            mock_redis = MockRedis(
                database=database,
                decode_responses=decode_responses,
                latency_config=latency_cfg,
                **config,
            )
            try:
                return func(mock_redis, *args, **kwargs)
            finally:
                mock_redis.close()

        wrapper._mock_redis = True
        wrapper._mock_database = database
        wrapper._mock_config = config
        return wrapper

    return decorator


def use_mock_datastore(
    datastore_type: str,
    database: str = ":memory:",
    **config,
) -> Callable:
    """
    Generic decorator for injecting any mock data store.

    Dispatches to the appropriate specific mock decorator based on
    datastore_type ('postgres', 'kafka', 'redis').

    Example:
        @use_mock_datastore('redis', decode_responses=True)
        def cache_test(redis):
            redis.set('key', 'value')
            return redis.get('key')

    Raises:
        ValueError: If datastore_type is not recognized
    """
    decorators = {
        "postgres": use_mock_postgres,
        "kafka": use_mock_kafka,
        "redis": use_mock_redis,
    }
    key = datastore_type.lower()
    if key not in decorators:
        raise ValueError(
            f"Unknown datastore type: {datastore_type}. "
            f"Supported types: {', '.join(decorators)}"
        )
    return decorators[key](database=database, **config)
