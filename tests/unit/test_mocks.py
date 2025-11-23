"""Unit tests for mock data store implementations."""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from plainbench.mocks.base import ConnectionPool, MockDataStore
from plainbench.mocks.decorators import (
    use_mock_datastore,
    use_mock_kafka,
    use_mock_postgres,
    use_mock_redis,
)
from plainbench.mocks.kafka import MockKafkaConsumer, MockKafkaProducer
from plainbench.mocks.postgres import MockPostgresConnection, MockPostgresCursor
from plainbench.mocks.redis import MockRedis


# ==============================================================================
# Base Mock Tests
# ==============================================================================


class ConcreteMockDataStore(MockDataStore):
    """Concrete implementation for testing."""

    def _init_schema(self):
        conn = self.connect()
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")


class TestMockDataStore:
    """Tests for base MockDataStore class."""

    def test_in_memory_database(self):
        """Test creating an in-memory database."""
        mock = ConcreteMockDataStore()
        conn = mock.connect()
        assert conn is not None
        mock.close()

    def test_file_database(self):
        """Test creating a file-based database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        try:
            mock = ConcreteMockDataStore(database=db_path)
            mock.connect()
            assert Path(db_path).exists()
            mock.close()
        finally:
            if Path(db_path).exists():
                os.unlink(db_path)

    def test_context_manager(self):
        """Test using mock as context manager."""
        with ConcreteMockDataStore() as mock:
            conn = mock.connect()
            assert conn is not None

    def test_transaction(self):
        """Test transaction context manager."""
        mock = ConcreteMockDataStore()
        with mock.transaction() as conn:
            conn.execute("INSERT INTO test (id) VALUES (1)")

        # Verify data was committed
        result = mock.connect().execute("SELECT * FROM test").fetchall()
        assert len(result) == 1
        mock.close()


class TestConnectionPool:
    """Tests for ConnectionPool class."""

    def test_get_connection(self):
        """Test getting a connection from the pool."""
        pool = ConnectionPool()
        conn = pool.get_connection()
        assert conn is not None
        pool.close_all()

    def test_context_manager(self):
        """Test using pool as context manager."""
        with ConnectionPool() as pool:
            conn = pool.get_connection()
            assert conn is not None


# ==============================================================================
# Mock Postgres Tests
# ==============================================================================


class TestMockPostgres:
    """Tests for MockPostgresConnection and MockPostgresCursor."""

    def test_connection_creation(self):
        """Test creating a mock Postgres connection."""
        conn = MockPostgresConnection()
        assert conn is not None
        assert not conn.closed
        conn.close()
        assert conn.closed

    def test_cursor_creation(self):
        """Test creating a cursor."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()
        assert isinstance(cursor, MockPostgresCursor)
        cursor.close()
        conn.close()

    def test_create_table(self):
        """Test creating a table."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL
            )
            """
        )

        # Verify table was created
        result = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        assert result is not None

        cursor.close()
        conn.close()

    def test_insert_and_select(self):
        """Test inserting and selecting data."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE test (id INTEGER, value TEXT)")
        cursor.execute("INSERT INTO test VALUES (?, ?)", (1, "test"))
        conn.commit()

        cursor.execute("SELECT * FROM test WHERE id = ?", (1,))
        result = cursor.fetchone()

        assert result == (1, "test")

        cursor.close()
        conn.close()

    def test_executemany(self):
        """Test executing with multiple parameter sets."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE test (id INTEGER, value TEXT)")
        cursor.executemany(
            "INSERT INTO test VALUES (?, ?)", [(1, "a"), (2, "b"), (3, "c")]
        )
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]

        assert count == 3

        cursor.close()
        conn.close()

    def test_fetchall(self):
        """Test fetching all rows."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE test (id INTEGER)")
        cursor.executemany("INSERT INTO test VALUES (?)", [(1,), (2,), (3,)])
        conn.commit()

        cursor.execute("SELECT * FROM test ORDER BY id")
        results = cursor.fetchall()

        assert len(results) == 3
        assert results == [(1,), (2,), (3,)]

        cursor.close()
        conn.close()

    def test_fetchmany(self):
        """Test fetching a limited number of rows."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE test (id INTEGER)")
        cursor.executemany("INSERT INTO test VALUES (?)", [(i,) for i in range(10)])
        conn.commit()

        cursor.execute("SELECT * FROM test")
        results = cursor.fetchmany(3)

        assert len(results) == 3

        cursor.close()
        conn.close()

    def test_sql_translation_placeholders(self):
        """Test SQL translation of placeholders."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()

        # Use %s placeholders (Postgres style)
        sql = "SELECT %s, %s"
        translated = cursor._translate_sql(sql)

        assert translated == "SELECT ?, ?"

        conn.close()

    def test_sql_translation_now(self):
        """Test SQL translation of NOW()."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()

        sql = "SELECT NOW()"
        translated = cursor._translate_sql(sql)

        assert "CURRENT_TIMESTAMP" in translated

        conn.close()

    def test_sql_translation_boolean(self):
        """Test SQL translation of BOOLEAN type."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()

        sql = "CREATE TABLE test (active BOOLEAN)"
        translated = cursor._translate_sql(sql)

        assert "INTEGER" in translated
        assert "BOOLEAN" not in translated

        conn.close()

    def test_commit_rollback(self):
        """Test commit and rollback."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()

        # Create table and commit (DDL should be committed)
        cursor.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()

        # Insert and rollback
        cursor.execute("INSERT INTO test VALUES (1)")
        conn.rollback()

        # Verify data was not committed
        cursor.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        assert count == 0

        # Insert and commit
        cursor.execute("INSERT INTO test VALUES (2)")
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        assert count == 1

        cursor.close()
        conn.close()

    def test_cursor_description(self):
        """Test cursor description attribute."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        cursor.execute("INSERT INTO test VALUES (1, 'Alice')")
        cursor.execute("SELECT * FROM test")

        assert cursor.description is not None
        assert len(cursor.description) == 2

        cursor.close()
        conn.close()

    def test_cursor_rowcount(self):
        """Test cursor rowcount attribute."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE test (id INTEGER)")
        cursor.executemany("INSERT INTO test VALUES (?)", [(i,) for i in range(5)])

        assert cursor.rowcount == 5

        cursor.close()
        conn.close()

    def test_cursor_iterator(self):
        """Test using cursor as iterator."""
        conn = MockPostgresConnection()
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE test (id INTEGER)")
        cursor.executemany("INSERT INTO test VALUES (?)", [(1,), (2,), (3,)])
        conn.commit()

        cursor.execute("SELECT * FROM test ORDER BY id")

        rows = list(cursor)
        assert len(rows) == 3

        cursor.close()
        conn.close()


# ==============================================================================
# Mock Kafka Tests
# ==============================================================================


class TestMockKafka:
    """Tests for MockKafkaProducer and MockKafkaConsumer."""

    def test_producer_creation(self):
        """Test creating a mock Kafka producer."""
        producer = MockKafkaProducer()
        assert producer is not None
        producer.close()

    def test_producer_send(self):
        """Test sending messages."""
        producer = MockKafkaProducer()

        future = producer.send("test-topic", value=b"test-message", key=b"test-key")
        result = future.result()

        assert result.topic == "test-topic"
        assert result.partition == 0
        assert result.offset == 0

        producer.close()

    def test_producer_multiple_messages(self):
        """Test sending multiple messages."""
        producer = MockKafkaProducer()

        for i in range(10):
            future = producer.send("test-topic", value=f"message-{i}".encode())
            result = future.result()
            assert result.offset == i

        producer.close()

    def test_consumer_creation(self):
        """Test creating a mock Kafka consumer."""
        consumer = MockKafkaConsumer("test-topic", group_id="test-group")
        assert consumer is not None
        assert "test-topic" in consumer.topics
        consumer.close()

    def test_producer_consumer_integration(self):
        """Test producing and consuming messages."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        try:
            # Produce messages
            producer = MockKafkaProducer(database=db_path)
            for i in range(5):
                producer.send("test-topic", value=f"message-{i}".encode())
            producer.flush()
            producer.close()

            # Consume messages
            consumer = MockKafkaConsumer("test-topic", database=db_path, group_id="test-group")
            messages = consumer.poll(max_records=10)

            total_messages = sum(len(records) for records in messages.values())
            assert total_messages == 5

            consumer.close()
        finally:
            if Path(db_path).exists():
                os.unlink(db_path)

    def test_consumer_offset_tracking(self):
        """Test consumer offset tracking."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        try:
            # Produce messages
            producer = MockKafkaProducer(database=db_path)
            for i in range(10):
                producer.send("test-topic", value=f"message-{i}".encode())
            producer.close()

            # Consume first batch
            consumer = MockKafkaConsumer("test-topic", database=db_path, group_id="test-group")
            messages1 = consumer.poll(max_records=5)
            consumer.commit()
            consumer.close()

            # Consume second batch (should get different messages)
            consumer2 = MockKafkaConsumer("test-topic", database=db_path, group_id="test-group")
            messages2 = consumer2.poll(max_records=5)

            total1 = sum(len(records) for records in messages1.values())
            total2 = sum(len(records) for records in messages2.values())

            assert total1 == 5
            assert total2 == 5

            consumer2.close()
        finally:
            if Path(db_path).exists():
                os.unlink(db_path)

    def test_consumer_auto_offset_reset(self):
        """Test consumer auto_offset_reset behavior."""
        consumer_earliest = MockKafkaConsumer(
            "test-topic", auto_offset_reset="earliest"
        )
        consumer_latest = MockKafkaConsumer("test-topic", auto_offset_reset="latest")

        assert consumer_earliest.auto_offset_reset == "earliest"
        assert consumer_latest.auto_offset_reset == "latest"

        consumer_earliest.close()
        consumer_latest.close()


# ==============================================================================
# Mock Redis Tests
# ==============================================================================


class TestMockRedis:
    """Tests for MockRedis."""

    def test_redis_creation(self):
        """Test creating a mock Redis client."""
        redis = MockRedis()
        assert redis is not None
        redis.close()

    def test_string_operations(self):
        """Test string SET and GET operations."""
        redis = MockRedis(decode_responses=True)

        redis.set("key1", "value1")
        result = redis.get("key1")

        assert result == "value1"

        redis.close()

    def test_string_with_expiration(self):
        """Test string operations with expiration."""
        redis = MockRedis(decode_responses=True)

        redis.set("key1", "value1", ex=3600)
        ttl = redis.ttl("key1")

        assert ttl > 0
        assert ttl <= 3600

        redis.close()

    def test_delete_operations(self):
        """Test deleting keys."""
        redis = MockRedis()

        redis.set("key1", "value1")
        redis.set("key2", "value2")

        count = redis.delete("key1", "key2")
        assert count == 2

        assert redis.get("key1") is None
        assert redis.get("key2") is None

        redis.close()

    def test_exists_operations(self):
        """Test checking key existence."""
        redis = MockRedis()

        redis.set("key1", "value1")
        redis.set("key2", "value2")

        assert redis.exists("key1", "key2") == 2
        assert redis.exists("key1", "nonexistent") == 1

        redis.close()

    def test_list_operations(self):
        """Test list LPUSH and LRANGE operations."""
        redis = MockRedis(decode_responses=True)

        redis.lpush("mylist", "a", "b", "c")
        result = redis.lrange("mylist", 0, -1)

        assert len(result) == 3
        assert "a" in result

        redis.close()

    def test_list_rpush(self):
        """Test list RPUSH operation."""
        redis = MockRedis(decode_responses=True)

        length = redis.rpush("mylist", "a", "b", "c")
        assert length == 3

        result = redis.lrange("mylist", 0, -1)
        assert result == ["a", "b", "c"]

        redis.close()

    def test_set_operations(self):
        """Test set SADD and SMEMBERS operations."""
        redis = MockRedis(decode_responses=True)

        redis.sadd("myset", "a", "b", "c")
        members = redis.smembers("myset")

        assert len(members) == 3
        assert "a" in members
        assert "b" in members

        redis.close()

    def test_hash_operations(self):
        """Test hash HSET and HGET operations."""
        redis = MockRedis(decode_responses=True)

        redis.hset("myhash", "field1", "value1")
        redis.hset("myhash", "field2", "value2")

        assert redis.hget("myhash", "field1") == "value1"
        assert redis.hget("myhash", "field2") == "value2"

        redis.close()

    def test_hash_getall(self):
        """Test HGETALL operation."""
        redis = MockRedis(decode_responses=True)

        redis.hset("myhash", "field1", "value1")
        redis.hset("myhash", "field2", "value2")

        all_fields = redis.hgetall("myhash")

        assert len(all_fields) == 2
        assert all_fields["field1"] == "value1"
        assert all_fields["field2"] == "value2"

        redis.close()

    def test_pipeline(self):
        """Test pipeline operations."""
        redis = MockRedis(decode_responses=True)

        with redis.pipeline() as pipe:
            pipe.set("key1", "value1")
            pipe.set("key2", "value2")
            pipe.get("key1")
            results = pipe.execute()

        assert len(results) == 3
        assert results[2] == "value1"

        redis.close()

    def test_decode_responses(self):
        """Test decode_responses option."""
        redis_bytes = MockRedis(decode_responses=False)
        redis_str = MockRedis(decode_responses=True)

        redis_bytes.set("key", "value")
        redis_str.set("key", "value")

        assert isinstance(redis_bytes.get("key"), bytes)
        assert isinstance(redis_str.get("key"), str)

        redis_bytes.close()
        redis_str.close()


# ==============================================================================
# Decorator Tests
# ==============================================================================


class TestMockDecorators:
    """Tests for mock decorators."""

    def test_use_mock_postgres_decorator(self):
        """Test @use_mock_postgres decorator."""

        @use_mock_postgres()
        def test_func(db_conn):
            cursor = db_conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER)")
            cursor.execute("INSERT INTO test VALUES (1)")
            cursor.execute("SELECT COUNT(*) FROM test")
            return cursor.fetchone()[0]

        result = test_func()
        assert result == 1

    def test_use_mock_kafka_decorator_producer(self):
        """Test @use_mock_kafka decorator with producer."""

        @use_mock_kafka()
        def test_func(producer):
            future = producer.send("test-topic", value=b"test")
            result = future.result()
            return result.offset

        offset = test_func()
        assert offset == 0

    def test_use_mock_kafka_decorator_both(self):
        """Test @use_mock_kafka decorator with producer and consumer."""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        try:

            @use_mock_kafka(database=db_path, inject_consumer=True, topics=["test-topic"])
            def test_func(producer, consumer):
                # Produce a message
                producer.send("test-topic", value=b"test")
                producer.flush()

                # Consume the message
                messages = consumer.poll(max_records=1)
                total = sum(len(records) for records in messages.values())
                return total

            count = test_func()
            assert count == 1

        finally:
            if Path(db_path).exists():
                os.unlink(db_path)

    def test_use_mock_redis_decorator(self):
        """Test @use_mock_redis decorator."""

        @use_mock_redis(decode_responses=True)
        def test_func(redis):
            redis.set("key", "value")
            return redis.get("key")

        result = test_func()
        assert result == "value"

    def test_use_mock_datastore_postgres(self):
        """Test @use_mock_datastore with postgres."""

        @use_mock_datastore("postgres")
        def test_func(db_conn):
            cursor = db_conn.cursor()
            cursor.execute("SELECT 1")
            return cursor.fetchone()[0]

        result = test_func()
        assert result == 1

    def test_use_mock_datastore_redis(self):
        """Test @use_mock_datastore with redis."""

        @use_mock_datastore("redis", decode_responses=True)
        def test_func(redis):
            redis.set("key", "value")
            return redis.get("key")

        result = test_func()
        assert result == "value"

    def test_use_mock_datastore_invalid(self):
        """Test @use_mock_datastore with invalid type."""
        with pytest.raises(ValueError, match="Unknown datastore type"):

            @use_mock_datastore("invalid")
            def test_func(conn):
                pass

            test_func()

    def test_decorator_preserves_metadata(self):
        """Test that decorators preserve function metadata."""

        @use_mock_postgres()
        def test_func(db_conn):
            """Test function docstring."""
            pass

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring."
        assert hasattr(test_func, "_mock_postgres")
