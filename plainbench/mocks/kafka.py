"""Mock Kafka implementation using SQLite."""

import json
import time
from concurrent.futures import Future
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from plainbench.mocks.base import LatencyConfig, MockDataStore

# Default latencies for Kafka operations (in seconds)
# Based on research of well-tuned Kafka clusters in same-datacenter environments.
#
# Research sources indicate:
# - Low-latency configs: <1-2ms for producer send
# - Balanced throughput/latency: 2-50ms end-to-end
# - P99 latencies: 50-200ms in cloud environments
# - Consumer lag typically a few milliseconds in healthy clusters
DEFAULT_KAFKA_LATENCIES = {
    "producer_send_single": 0.005,  # 5ms - single message send
    "producer_send_batch": 0.015,  # 15ms - batch of messages
    "producer_flush": 0.010,  # 10ms - flush pending messages
    "consumer_poll": 0.002,  # 2ms - poll for messages
    "consumer_commit": 0.005,  # 5ms - commit offsets
}


class MockKafkaProducer(MockDataStore):
    """
    Mock Kafka producer that uses SQLite as the backend.

    This class provides an API compatible with kafka-python's KafkaProducer,
    allowing you to benchmark message production without a real Kafka cluster.

    Example:
        producer = MockKafkaProducer()
        future = producer.send('my-topic', value=b'my-message', key=b'my-key')
        result = future.get(timeout=10)
        producer.close()
    """

    def __init__(
        self,
        database: str = ":memory:",
        bootstrap_servers: Optional[List[str]] = None,
        latency_config: Optional[LatencyConfig] = None,
        **config,
    ):
        """
        Initialize mock Kafka producer.

        Args:
            database: SQLite database path (default: in-memory)
            bootstrap_servers: Bootstrap servers (for API compatibility)
            latency_config: Configuration for latency simulation
            **config: Additional configuration (for API compatibility)
        """
        super().__init__(database, latency_config=latency_config, **config)
        self.bootstrap_servers = bootstrap_servers or ["localhost:9092"]
        self._closed = False
        # Connect and initialize schema immediately
        self.connect()

    def _init_schema(self) -> None:
        """Initialize the Kafka storage schema."""
        conn = self.connect()

        # Topics table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kafka_topics (
                topic_name TEXT PRIMARY KEY,
                partition_count INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Messages table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kafka_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                partition INTEGER NOT NULL,
                offset INTEGER NOT NULL,
                key BLOB,
                value BLOB,
                headers TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(topic, partition, offset)
            )
            """
        )

        # Consumer offsets table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kafka_consumer_offsets (
                consumer_group TEXT NOT NULL,
                topic TEXT NOT NULL,
                partition INTEGER NOT NULL,
                offset INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (consumer_group, topic, partition)
            )
            """
        )

        # Create indexes for performance
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_topic_partition
            ON kafka_messages(topic, partition, offset)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_consumer_offsets
            ON kafka_consumer_offsets(consumer_group, topic, partition)
            """
        )

    def _ensure_topic_exists(self, topic: str, partitions: int = 1) -> None:
        """
        Ensure topic exists in the database.

        Args:
            topic: Topic name
            partitions: Number of partitions
        """
        conn = self.connect()
        conn.execute(
            """
            INSERT OR IGNORE INTO kafka_topics (topic_name, partition_count)
            VALUES (?, ?)
            """,
            (topic, partitions),
        )

    def _get_next_offset(self, topic: str, partition: int) -> int:
        """
        Get the next offset for a topic/partition.

        Args:
            topic: Topic name
            partition: Partition number

        Returns:
            Next offset value
        """
        conn = self.connect()
        result = conn.execute(
            """
            SELECT MAX(offset) FROM kafka_messages
            WHERE topic = ? AND partition = ?
            """,
            (topic, partition),
        ).fetchone()

        current_max = result[0] if result[0] is not None else -1
        return current_max + 1

    def send(
        self,
        topic: str,
        value: Optional[bytes] = None,
        key: Optional[bytes] = None,
        headers: Optional[List[Tuple[str, bytes]]] = None,
        partition: Optional[int] = None,
        timestamp_ms: Optional[int] = None,
    ) -> Future:
        """
        Send a message to a topic.

        Args:
            topic: Topic name
            value: Message value (bytes)
            key: Message key (bytes)
            headers: Message headers
            partition: Target partition (default: 0)
            timestamp_ms: Message timestamp in milliseconds

        Returns:
            Future that resolves to RecordMetadata
        """
        if self._closed:
            raise ValueError("Producer is closed")

        # Simulate producer send latency
        self.latency_config.simulate("producer_send_single")

        # Default partition
        if partition is None:
            partition = 0

        # Ensure topic exists
        self._ensure_topic_exists(topic)

        # Get next offset
        offset = self._get_next_offset(topic, partition)

        # Serialize headers
        headers_json = json.dumps(headers) if headers else None

        # Insert message
        conn = self.connect()
        conn.execute(
            """
            INSERT INTO kafka_messages
            (topic, partition, offset, key, value, headers, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic,
                partition,
                offset,
                key,
                value,
                headers_json,
                datetime.utcnow().isoformat(),
            ),
        )

        # Create successful future
        future = Future()
        metadata = RecordMetadata(
            topic=topic,
            partition=partition,
            offset=offset,
            timestamp=timestamp_ms or int(time.time() * 1000),
        )
        future.set_result(metadata)

        return future

    def flush(self, timeout: Optional[float] = None) -> None:
        """
        Flush all pending messages.

        Args:
            timeout: Timeout in seconds (not used in mock)
        """
        # Simulate flush latency
        self.latency_config.simulate("producer_flush")

        # Commit any pending transactions
        conn = self.connect()
        conn.commit()

    def close(self, timeout: Optional[float] = None) -> None:
        """
        Close the producer.

        Args:
            timeout: Timeout in seconds (not used in mock)
        """
        if not self._closed:
            self.flush(timeout)
            super().close()
            self._closed = True


class MockKafkaConsumer(MockDataStore):
    """
    Mock Kafka consumer that uses SQLite as the backend.

    This class provides an API compatible with kafka-python's KafkaConsumer,
    allowing you to benchmark message consumption without a real Kafka cluster.

    Example:
        consumer = MockKafkaConsumer('my-topic', group_id='my-group')
        for message in consumer:
            print(f"Received: {message.value}")
            consumer.commit()
        consumer.close()
    """

    def __init__(
        self,
        *topics,
        database: str = ":memory:",
        bootstrap_servers: Optional[List[str]] = None,
        group_id: Optional[str] = None,
        auto_offset_reset: str = "earliest",
        enable_auto_commit: bool = True,
        latency_config: Optional[LatencyConfig] = None,
        **config,
    ):
        """
        Initialize mock Kafka consumer.

        Args:
            *topics: Topics to subscribe to
            database: SQLite database path (default: in-memory)
            bootstrap_servers: Bootstrap servers (for API compatibility)
            group_id: Consumer group ID
            auto_offset_reset: Where to start consuming ('earliest' or 'latest')
            enable_auto_commit: Enable automatic offset commits
            latency_config: Configuration for latency simulation
            **config: Additional configuration
        """
        super().__init__(database, latency_config=latency_config, **config)
        self.topics = list(topics)
        self.bootstrap_servers = bootstrap_servers or ["localhost:9092"]
        self.group_id = group_id or "default-group"
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit
        self._closed = False
        self._current_offsets: Dict[Tuple[str, int], int] = {}
        # Connect and initialize schema immediately
        self.connect()

    def _init_schema(self) -> None:
        """Initialize the Kafka storage schema."""
        conn = self.connect()

        # Topics table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kafka_topics (
                topic_name TEXT PRIMARY KEY,
                partition_count INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Messages table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kafka_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                partition INTEGER NOT NULL,
                offset INTEGER NOT NULL,
                key BLOB,
                value BLOB,
                headers TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(topic, partition, offset)
            )
            """
        )

        # Consumer offsets table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kafka_consumer_offsets (
                consumer_group TEXT NOT NULL,
                topic TEXT NOT NULL,
                partition INTEGER NOT NULL,
                offset INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (consumer_group, topic, partition)
            )
            """
        )

        # Create indexes for performance
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_topic_partition
            ON kafka_messages(topic, partition, offset)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_consumer_offsets
            ON kafka_consumer_offsets(consumer_group, topic, partition)
            """
        )

        conn.commit()

    def _get_consumer_offset(self, topic: str, partition: int) -> int:
        """
        Get the current offset for a topic/partition in this consumer group.

        Args:
            topic: Topic name
            partition: Partition number

        Returns:
            Current offset
        """
        conn = self.connect()
        result = conn.execute(
            """
            SELECT offset FROM kafka_consumer_offsets
            WHERE consumer_group = ? AND topic = ? AND partition = ?
            """,
            (self.group_id, topic, partition),
        ).fetchone()

        if result:
            return result[0]

        # No offset stored, use auto_offset_reset
        if self.auto_offset_reset == "earliest":
            return 0
        else:  # latest
            max_result = conn.execute(
                """
                SELECT MAX(offset) FROM kafka_messages
                WHERE topic = ? AND partition = ?
                """,
                (topic, partition),
            ).fetchone()
            return (max_result[0] + 1) if max_result[0] is not None else 0

    def _fetch_messages(
        self, topic: str, partition: int, limit: int = 100
    ) -> List["ConsumerRecord"]:
        """
        Fetch messages from a topic/partition.

        Args:
            topic: Topic name
            partition: Partition number
            limit: Maximum number of messages to fetch

        Returns:
            List of ConsumerRecord objects
        """
        offset = self._get_consumer_offset(topic, partition)

        conn = self.connect()
        rows = conn.execute(
            """
            SELECT id, topic, partition, offset, key, value, headers, timestamp
            FROM kafka_messages
            WHERE topic = ? AND partition = ? AND offset >= ?
            ORDER BY offset
            LIMIT ?
            """,
            (topic, partition, offset, limit),
        ).fetchall()

        records = []
        for row in rows:
            headers = json.loads(row[6]) if row[6] else None
            record = ConsumerRecord(
                topic=row[1],
                partition=row[2],
                offset=row[3],
                key=row[4],
                value=row[5],
                headers=headers,
                timestamp=row[7],
            )
            records.append(record)

        return records

    def poll(
        self,
        timeout_ms: float = 1000,
        max_records: Optional[int] = None,
        update_offsets: bool = True,
    ) -> Dict[Tuple[str, int], List["ConsumerRecord"]]:
        """
        Poll for messages.

        Args:
            timeout_ms: Timeout in milliseconds (not used in mock)
            max_records: Maximum number of records to return
            update_offsets: Update internal offset tracking

        Returns:
            Dictionary mapping (topic, partition) to list of records
        """
        if self._closed:
            raise ValueError("Consumer is closed")

        # Simulate consumer poll latency
        self.latency_config.simulate("consumer_poll")

        result = {}

        for topic in self.topics:
            # For simplicity, assume single partition
            partition = 0
            records = self._fetch_messages(topic, partition, limit=max_records or 100)

            if records:
                result[(topic, partition)] = records

                # Update internal offset tracking
                if update_offsets:
                    last_offset = records[-1].offset
                    self._current_offsets[(topic, partition)] = last_offset + 1

                    # Auto-commit if enabled
                    if self.enable_auto_commit:
                        self._commit_offset(topic, partition, last_offset + 1)

        return result

    def _commit_offset(self, topic: str, partition: int, offset: int) -> None:
        """
        Commit an offset to the database.

        Args:
            topic: Topic name
            partition: Partition number
            offset: Offset to commit
        """
        conn = self.connect()
        conn.execute(
            """
            INSERT OR REPLACE INTO kafka_consumer_offsets
            (consumer_group, topic, partition, offset, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (self.group_id, topic, partition, offset, datetime.utcnow().isoformat()),
        )
        conn.commit()

    def commit(self, offsets: Optional[Dict] = None) -> None:
        """
        Commit offsets.

        Args:
            offsets: Specific offsets to commit (default: current offsets)
        """
        if self._closed:
            raise ValueError("Consumer is closed")

        # Simulate consumer commit latency
        self.latency_config.simulate("consumer_commit")

        if offsets is None:
            # Commit all current offsets
            for (topic, partition), offset in self._current_offsets.items():
                self._commit_offset(topic, partition, offset)
        else:
            # Commit specified offsets
            for (topic, partition), offset in offsets.items():
                self._commit_offset(topic, partition, offset)

    def close(self, autocommit: bool = True) -> None:
        """
        Close the consumer.

        Args:
            autocommit: Commit offsets before closing
        """
        if not self._closed:
            if autocommit:
                self.commit()
            super().close()
            self._closed = True

    def __iter__(self):
        """Make consumer iterable."""
        return self

    def __next__(self) -> "ConsumerRecord":
        """Get next message when iterating."""
        if self._closed:
            raise StopIteration

        # Poll for messages
        records = self.poll(timeout_ms=100, max_records=1)

        if not records:
            raise StopIteration

        # Return first record
        for record_list in records.values():
            if record_list:
                return record_list[0]

        raise StopIteration


class RecordMetadata:
    """Metadata for a produced record."""

    def __init__(self, topic: str, partition: int, offset: int, timestamp: int):
        """
        Initialize record metadata.

        Args:
            topic: Topic name
            partition: Partition number
            offset: Record offset
            timestamp: Timestamp in milliseconds
        """
        self.topic = topic
        self.partition = partition
        self.offset = offset
        self.timestamp = timestamp

    def __repr__(self):
        return (
            f"RecordMetadata(topic={self.topic}, partition={self.partition}, "
            f"offset={self.offset}, timestamp={self.timestamp})"
        )


class ConsumerRecord:
    """A consumed Kafka record."""

    def __init__(
        self,
        topic: str,
        partition: int,
        offset: int,
        key: Optional[bytes],
        value: Optional[bytes],
        headers: Optional[List],
        timestamp: str,
    ):
        """
        Initialize consumer record.

        Args:
            topic: Topic name
            partition: Partition number
            offset: Record offset
            key: Record key
            value: Record value
            headers: Record headers
            timestamp: Timestamp
        """
        self.topic = topic
        self.partition = partition
        self.offset = offset
        self.key = key
        self.value = value
        self.headers = headers
        self.timestamp = timestamp

    def __repr__(self):
        return (
            f"ConsumerRecord(topic={self.topic}, partition={self.partition}, "
            f"offset={self.offset}, key={self.key!r}, value={self.value!r})"
        )
