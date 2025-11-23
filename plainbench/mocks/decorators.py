"""Decorators for injecting mock data stores into benchmarked functions."""

import functools
import sys
from typing import Any, Callable, Dict, Optional

from plainbench.mocks.kafka import MockKafkaConsumer, MockKafkaProducer
from plainbench.mocks.postgres import MockPostgresConnection
from plainbench.mocks.redis import MockRedis


def use_mock_postgres(
    database: str = ":memory:",
    autocommit: bool = False,
    inject_as: str = "db_conn",
    **config,
) -> Callable:
    """
    Decorator that injects a MockPostgresConnection into the benchmarked function.

    This decorator creates a SQLite-backed mock Postgres connection and injects it
    as the first parameter of the decorated function, allowing you to benchmark
    database logic without a real Postgres instance.

    Args:
        database: SQLite database path (default: in-memory)
        autocommit: Enable autocommit mode
        inject_as: Parameter name for injection (default: 'db_conn')
        **config: Additional connection configuration

    Example:
        @use_mock_postgres()
        @benchmark()
        def process_orders(db_conn):
            cursor = db_conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE status = 'pending'")
            orders = cursor.fetchall()
            # Process orders...
            return len(orders)

        # The function receives a MockPostgresConnection as db_conn
        result = process_orders()

    Example with shared database:
        # Share database across multiple runs for realistic benchmarking
        @use_mock_postgres(database='./test.db')
        @benchmark(runs=10)
        def query_users(db_conn):
            cursor = db_conn.cursor()
            cursor.execute("SELECT * FROM users LIMIT 100")
            return cursor.fetchall()

    Note:
        The mock connection is automatically closed after the function executes.
        Use shared database files if you need data persistence across runs.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create mock connection
            mock_conn = MockPostgresConnection(
                database=database, autocommit=autocommit, **config
            )

            try:
                # Inject connection as first parameter
                result = func(mock_conn, *args, **kwargs)
                return result
            finally:
                # Clean up connection
                mock_conn.close()

        # Preserve metadata for introspection
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
    **config,
) -> Callable:
    """
    Decorator that injects MockKafkaProducer and/or MockKafkaConsumer.

    This decorator creates SQLite-backed mock Kafka clients and injects them
    into the decorated function, allowing you to benchmark message processing
    logic without a real Kafka cluster.

    Args:
        database: SQLite database path (default: in-memory)
        inject_producer: Inject a producer (default: True)
        inject_consumer: Inject a consumer (default: False)
        topics: Topics to subscribe to (for consumer)
        group_id: Consumer group ID
        **config: Additional Kafka configuration

    Example:
        # Producer only
        @use_mock_kafka()
        @benchmark()
        def produce_events(producer):
            for i in range(1000):
                producer.send('events', value=f'event-{i}'.encode())
            producer.flush()

        # Producer and consumer
        @use_mock_kafka(inject_consumer=True, topics=['events'])
        @benchmark()
        def process_events(producer, consumer):
            # Produce some events
            for i in range(100):
                producer.send('events', value=f'event-{i}'.encode())
            producer.flush()

            # Consume and process
            messages = consumer.poll(timeout_ms=1000, max_records=100)
            return sum(len(records) for records in messages.values())

    Example with shared database:
        # Share database to test realistic producer/consumer scenarios
        @use_mock_kafka(database='./kafka.db', inject_consumer=True, topics=['orders'])
        @benchmark()
        def process_order_queue(producer, consumer):
            # Consumer reads from previous runs
            messages = consumer.poll(max_records=10)
            # Process and produce results
            for records in messages.values():
                for record in records:
                    # Process order
                    producer.send('processed', value=record.value)
            producer.flush()
            consumer.commit()

    Note:
        Both producer and consumer are automatically closed after execution.
        When inject_consumer=True, both producer and consumer are injected.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            producer = None
            consumer = None

            try:
                # Create producer if requested
                if inject_producer:
                    producer = MockKafkaProducer(database=database, **config)

                # Create consumer if requested
                if inject_consumer:
                    consumer_topics = topics or []
                    consumer = MockKafkaConsumer(
                        *consumer_topics, database=database, group_id=group_id, **config
                    )

                # Inject based on configuration
                if inject_producer and inject_consumer:
                    result = func(producer, consumer, *args, **kwargs)
                elif inject_producer:
                    result = func(producer, *args, **kwargs)
                elif inject_consumer:
                    result = func(consumer, *args, **kwargs)
                else:
                    raise ValueError(
                        "Must inject at least producer or consumer "
                        "(inject_producer=True or inject_consumer=True)"
                    )

                return result

            finally:
                # Clean up resources
                if producer:
                    producer.close()
                if consumer:
                    consumer.close()

        # Preserve metadata for introspection
        wrapper._mock_kafka = True
        wrapper._mock_database = database
        wrapper._mock_config = config

        return wrapper

    return decorator


def use_mock_redis(
    database: str = ":memory:",
    decode_responses: bool = False,
    **config,
) -> Callable:
    """
    Decorator that injects a MockRedis client into the benchmarked function.

    This decorator creates a SQLite-backed mock Redis client and injects it
    as the first parameter, allowing you to benchmark caching logic without
    a real Redis server.

    Args:
        database: SQLite database path (default: in-memory)
        decode_responses: Decode byte responses to strings
        **config: Additional Redis configuration

    Example:
        @use_mock_redis(decode_responses=True)
        @benchmark()
        def cache_lookups(redis):
            # Warm up cache
            for i in range(100):
                redis.set(f'user:{i}', f'User {i}', ex=60)

            # Benchmark cache reads
            results = []
            for i in range(100):
                value = redis.get(f'user:{i}')
                results.append(value)

            return len(results)

    Example with different data structures:
        @use_mock_redis()
        @benchmark()
        def redis_operations(redis):
            # String operations
            redis.set('counter', 0)

            # List operations
            redis.lpush('queue', 'task1', 'task2', 'task3')
            tasks = redis.lrange('queue', 0, -1)

            # Set operations
            redis.sadd('tags', 'python', 'benchmark', 'redis')
            all_tags = redis.smembers('tags')

            # Hash operations
            redis.hset('user:1', 'name', 'Alice')
            redis.hset('user:1', 'email', 'alice@example.com')
            user_data = redis.hgetall('user:1')

            return len(tasks) + len(all_tags)

    Example with pipeline:
        @use_mock_redis()
        @benchmark()
        def batch_operations(redis):
            # Use pipeline for batched commands
            with redis.pipeline() as pipe:
                for i in range(1000):
                    pipe.set(f'key:{i}', f'value:{i}')
                pipe.execute()

            # Read back
            results = [redis.get(f'key:{i}') for i in range(1000)]
            return len(results)

    Note:
        The mock Redis client is automatically closed after execution.
        Use shared database files for persistence across runs.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create mock Redis client
            mock_redis = MockRedis(
                database=database, decode_responses=decode_responses, **config
            )

            try:
                # Inject Redis client as first parameter
                result = func(mock_redis, *args, **kwargs)
                return result
            finally:
                # Clean up client
                mock_redis.close()

        # Preserve metadata for introspection
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

    This is a convenience decorator that dispatches to the appropriate
    specific mock decorator based on datastore_type.

    Args:
        datastore_type: Type of datastore ('postgres', 'kafka', 'redis')
        database: SQLite database path (default: in-memory)
        **config: Configuration passed to specific decorator

    Example:
        @use_mock_datastore('postgres')
        @benchmark()
        def query_data(db_conn):
            cursor = db_conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            return cursor.fetchone()[0]

        @use_mock_datastore('redis', decode_responses=True)
        @benchmark()
        def cache_test(redis):
            redis.set('key', 'value')
            return redis.get('key')

    Raises:
        ValueError: If datastore_type is not recognized
    """

    def decorator(func: Callable) -> Callable:
        if datastore_type.lower() == "postgres":
            return use_mock_postgres(database=database, **config)(func)
        elif datastore_type.lower() == "kafka":
            return use_mock_kafka(database=database, **config)(func)
        elif datastore_type.lower() == "redis":
            return use_mock_redis(database=database, **config)(func)
        else:
            raise ValueError(
                f"Unknown datastore type: {datastore_type}. "
                f"Supported types: postgres, kafka, redis"
            )

    return decorator


def use_mock_datastore_with_monkey_patch(
    datastore_type: str,
    database: str = ":memory:",
    module_name: Optional[str] = None,
    **config,
) -> Callable:
    """
    Decorator that monkey-patches the specified module to use mocks.

    WARNING: This is an advanced feature that modifies module imports.
    Use with caution and prefer the injection approach when possible.

    Args:
        datastore_type: Type of datastore ('postgres', 'kafka', 'redis')
        database: SQLite database path
        module_name: Module to patch (e.g., 'psycopg2', 'kafka', 'redis')
        **config: Additional configuration

    Example:
        # Patch psycopg2 to use mock
        @use_mock_datastore_with_monkey_patch('postgres', module_name='psycopg2')
        @benchmark()
        def my_existing_code():
            import psycopg2
            # This now returns MockPostgresConnection!
            conn = psycopg2.connect(host='localhost', database='test')
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            conn.close()
            return result

    Note:
        This approach is provided for compatibility with existing code
        that imports and uses the real libraries. The injection approach
        is preferred for new code.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            original_modules = {}

            try:
                # Setup monkey patches based on datastore type
                if datastore_type.lower() == "postgres":
                    patch_module = module_name or "psycopg2"
                    if patch_module in sys.modules:
                        original_modules[patch_module] = sys.modules[patch_module]

                    # Create mock module with connect function
                    class MockPsycopg2Module:
                        @staticmethod
                        def connect(**kwargs):
                            return MockPostgresConnection(database=database, **config)

                    sys.modules[patch_module] = MockPsycopg2Module()

                elif datastore_type.lower() == "redis":
                    patch_module = module_name or "redis"
                    if patch_module in sys.modules:
                        original_modules[patch_module] = sys.modules[patch_module]

                    # Create mock module with Redis class
                    class MockRedisModule:
                        @staticmethod
                        def Redis(**kwargs):
                            return MockRedis(database=database, **config)

                        # For redis.StrictRedis
                        StrictRedis = Redis

                    sys.modules[patch_module] = MockRedisModule()

                # Execute function
                result = func(*args, **kwargs)
                return result

            finally:
                # Restore original modules
                for module, original in original_modules.items():
                    sys.modules[module] = original

        return wrapper

    return decorator
