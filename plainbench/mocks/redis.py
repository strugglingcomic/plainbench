"""Mock Redis implementation using SQLite."""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from plainbench.mocks.base import LatencyConfig, MockDataStore

# Default latencies for Redis operations (in seconds)
# Based on research of typical Redis deployments in same-datacenter environments.
#
# Research sources indicate:
# - Command processing: sub-microsecond
# - Network round-trip (same datacenter): 100-300 microseconds (0.1-0.3ms)
# - Typical production latency: 0.2-0.5ms for GET/SET with network
# - Local connection: <1ms
DEFAULT_REDIS_LATENCIES = {
    "get": 0.0005,  # 0.5ms - GET single key with network
    "set": 0.0005,  # 0.5ms - SET single key with network
    "mget": 0.001,  # 1ms - MGET multiple keys
    "mset": 0.001,  # 1ms - MSET multiple keys
    "delete": 0.0005,  # 0.5ms - DEL
    "exists": 0.0003,  # 0.3ms - EXISTS check
    "ttl": 0.0003,  # 0.3ms - TTL check
    "lpush": 0.0006,  # 0.6ms - LPUSH
    "rpush": 0.0006,  # 0.6ms - RPUSH
    "lrange": 0.001,  # 1ms - LRANGE
    "sadd": 0.0006,  # 0.6ms - SADD
    "smembers": 0.001,  # 1ms - SMEMBERS
    "hset": 0.0006,  # 0.6ms - HSET
    "hget": 0.0005,  # 0.5ms - HGET
    "hgetall": 0.001,  # 1ms - HGETALL
    "pipeline_execute": 0.002,  # 2ms - pipeline execution
}


class MockRedis(MockDataStore):
    """
    Mock Redis client that uses SQLite as the backend.

    This class provides an API compatible with redis-py's Redis client,
    allowing you to benchmark Redis operations without a real Redis server.

    Example:
        redis = MockRedis()
        redis.set('key', 'value', ex=60)
        value = redis.get('key')
        redis.close()
    """

    def __init__(
        self,
        database: str = ":memory:",
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        decode_responses: bool = False,
        latency_config: Optional[LatencyConfig] = None,
        **config,
    ):
        """
        Initialize mock Redis client.

        Args:
            database: SQLite database path (default: in-memory)
            host: Redis host (for API compatibility)
            port: Redis port (for API compatibility)
            db: Redis database number (for API compatibility)
            decode_responses: Decode byte responses to strings
            latency_config: Configuration for latency simulation
            **config: Additional configuration
        """
        super().__init__(database, latency_config=latency_config, **config)
        self.host = host
        self.port = port
        self.db = db
        self.decode_responses = decode_responses
        self._closed = False
        self._pipeline_commands: List[Tuple] = []
        self._in_pipeline = False
        # Connect and initialize schema immediately
        self.connect()

    def _init_schema(self) -> None:
        """Initialize the Redis storage schema."""
        conn = self.connect()

        # Main keys table for strings and metadata
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS redis_keys (
                key TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                value BLOB,
                expires_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Lists table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS redis_lists (
                key TEXT NOT NULL,
                idx INTEGER NOT NULL,
                value BLOB NOT NULL,
                PRIMARY KEY (key, idx)
            )
            """
        )

        # Sets table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS redis_sets (
                key TEXT NOT NULL,
                member BLOB NOT NULL,
                PRIMARY KEY (key, member)
            )
            """
        )

        # Hashes table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS redis_hashes (
                key TEXT NOT NULL,
                field TEXT NOT NULL,
                value BLOB NOT NULL,
                PRIMARY KEY (key, field)
            )
            """
        )

        # Sorted sets table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS redis_sorted_sets (
                key TEXT NOT NULL,
                member BLOB NOT NULL,
                score REAL NOT NULL,
                PRIMARY KEY (key, member)
            )
            """
        )

        # Create indexes
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_expires_at
            ON redis_keys(expires_at)
            """
        )

    def _cleanup_expired_keys(self) -> None:
        """Remove expired keys from the database."""
        conn = self.connect()
        now = datetime.utcnow().isoformat()

        # Get expired keys
        expired = conn.execute(
            """
            SELECT key, type FROM redis_keys
            WHERE expires_at IS NOT NULL AND expires_at <= ?
            """,
            (now,),
        ).fetchall()

        for key, key_type in expired:
            # Delete from main table
            conn.execute("DELETE FROM redis_keys WHERE key = ?", (key,))

            # Delete from type-specific tables
            if key_type == "list":
                conn.execute("DELETE FROM redis_lists WHERE key = ?", (key,))
            elif key_type == "set":
                conn.execute("DELETE FROM redis_sets WHERE key = ?", (key,))
            elif key_type == "hash":
                conn.execute("DELETE FROM redis_hashes WHERE key = ?", (key,))
            elif key_type == "zset":
                conn.execute("DELETE FROM redis_sorted_sets WHERE key = ?", (key,))

    def _encode_value(self, value: Any) -> bytes:
        """Encode a value to bytes."""
        if isinstance(value, bytes):
            return value
        elif isinstance(value, str):
            return value.encode("utf-8")
        elif isinstance(value, (int, float)):
            return str(value).encode("utf-8")
        else:
            return json.dumps(value).encode("utf-8")

    def _decode_value(self, value: Optional[bytes]) -> Union[bytes, str, None]:
        """Decode a value from bytes."""
        if value is None:
            return None
        if self.decode_responses:
            return value.decode("utf-8")
        return value

    # String operations

    def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set a key-value pair.

        Args:
            key: Key name
            value: Value to set
            ex: Expiration in seconds
            px: Expiration in milliseconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            True if set, False otherwise
        """
        # Simulate SET latency
        self.latency_config.simulate("set")

        self._cleanup_expired_keys()
        conn = self.connect()

        # Calculate expiration
        expires_at = None
        if ex is not None:
            expires_at = (datetime.utcnow() + timedelta(seconds=ex)).isoformat()
        elif px is not None:
            expires_at = (
                datetime.utcnow() + timedelta(milliseconds=px)
            ).isoformat()

        # Check nx/xx conditions
        existing = conn.execute(
            "SELECT 1 FROM redis_keys WHERE key = ?", (key,)
        ).fetchone()

        if nx and existing:
            return False
        if xx and not existing:
            return False

        # Encode value
        encoded_value = self._encode_value(value)

        # Set the value
        conn.execute(
            """
            INSERT OR REPLACE INTO redis_keys (key, type, value, expires_at)
            VALUES (?, 'string', ?, ?)
            """,
            (key, encoded_value, expires_at),
        )

        return True

    def get(self, key: str) -> Union[bytes, str, None]:
        """
        Get a value by key.

        Args:
            key: Key name

        Returns:
            Value or None if not found
        """
        # Simulate GET latency
        self.latency_config.simulate("get")

        self._cleanup_expired_keys()
        conn = self.connect()

        result = conn.execute(
            """
            SELECT value FROM redis_keys
            WHERE key = ? AND type = 'string'
            """,
            (key,),
        ).fetchone()

        if result:
            return self._decode_value(result[0])
        return None

    def delete(self, *keys: str) -> int:
        """
        Delete one or more keys.

        Args:
            *keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        # Simulate DELETE latency
        self.latency_config.simulate("delete")

        conn = self.connect()
        count = 0

        for key in keys:
            # Get key type
            result = conn.execute(
                "SELECT type FROM redis_keys WHERE key = ?", (key,)
            ).fetchone()

            if result:
                key_type = result[0]
                conn.execute("DELETE FROM redis_keys WHERE key = ?", (key,))

                # Delete from type-specific tables
                if key_type == "list":
                    conn.execute("DELETE FROM redis_lists WHERE key = ?", (key,))
                elif key_type == "set":
                    conn.execute("DELETE FROM redis_sets WHERE key = ?", (key,))
                elif key_type == "hash":
                    conn.execute("DELETE FROM redis_hashes WHERE key = ?", (key,))
                elif key_type == "zset":
                    conn.execute("DELETE FROM redis_sorted_sets WHERE key = ?", (key,))

                count += 1

        return count

    def exists(self, *keys: str) -> int:
        """
        Check if keys exist.

        Args:
            *keys: Keys to check

        Returns:
            Number of existing keys
        """
        # Simulate EXISTS latency
        self.latency_config.simulate("exists")

        self._cleanup_expired_keys()
        conn = self.connect()

        placeholders = ",".join("?" * len(keys))
        result = conn.execute(
            f"SELECT COUNT(*) FROM redis_keys WHERE key IN ({placeholders})", keys
        ).fetchone()

        return result[0] if result else 0

    def ttl(self, key: str) -> int:
        """
        Get time-to-live for a key.

        Args:
            key: Key name

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        # Simulate TTL latency
        self.latency_config.simulate("ttl")

        self._cleanup_expired_keys()
        conn = self.connect()

        result = conn.execute(
            "SELECT expires_at FROM redis_keys WHERE key = ?", (key,)
        ).fetchone()

        if not result:
            return -2

        if result[0] is None:
            return -1

        expires_at = datetime.fromisoformat(result[0])
        ttl_seconds = (expires_at - datetime.utcnow()).total_seconds()
        return max(0, int(ttl_seconds))

    # List operations

    def lpush(self, key: str, *values: Any) -> int:
        """
        Push values to the left of a list.

        Args:
            key: List key
            *values: Values to push

        Returns:
            New length of list
        """
        # Simulate LPUSH latency
        self.latency_config.simulate("lpush")

        conn = self.connect()

        # Ensure key exists as list
        conn.execute(
            """
            INSERT OR IGNORE INTO redis_keys (key, type)
            VALUES (?, 'list')
            """,
            (key,),
        )

        # Get current max index
        result = conn.execute(
            "SELECT MIN(idx) FROM redis_lists WHERE key = ?", (key,)
        ).fetchone()
        min_idx = result[0] if result[0] is not None else 0

        # Insert values at the left (negative indices)
        for i, value in enumerate(values):
            encoded = self._encode_value(value)
            idx = min_idx - i - 1
            conn.execute(
                "INSERT INTO redis_lists (key, idx, value) VALUES (?, ?, ?)",
                (key, idx, encoded),
            )

        # Get new length
        result = conn.execute(
            "SELECT COUNT(*) FROM redis_lists WHERE key = ?", (key,)
        ).fetchone()
        return result[0] if result else 0

    def rpush(self, key: str, *values: Any) -> int:
        """
        Push values to the right of a list.

        Args:
            key: List key
            *values: Values to push

        Returns:
            New length of list
        """
        # Simulate RPUSH latency
        self.latency_config.simulate("rpush")

        conn = self.connect()

        # Ensure key exists as list
        conn.execute(
            """
            INSERT OR IGNORE INTO redis_keys (key, type)
            VALUES (?, 'list')
            """,
            (key,),
        )

        # Get current max index
        result = conn.execute(
            "SELECT MAX(idx) FROM redis_lists WHERE key = ?", (key,)
        ).fetchone()
        max_idx = result[0] if result[0] is not None else -1

        # Insert values at the right
        for i, value in enumerate(values):
            encoded = self._encode_value(value)
            idx = max_idx + i + 1
            conn.execute(
                "INSERT INTO redis_lists (key, idx, value) VALUES (?, ?, ?)",
                (key, idx, encoded),
            )

        # Get new length
        result = conn.execute(
            "SELECT COUNT(*) FROM redis_lists WHERE key = ?", (key,)
        ).fetchone()
        return result[0] if result else 0

    def lrange(self, key: str, start: int, stop: int) -> List[Union[bytes, str]]:
        """
        Get a range of elements from a list.

        Args:
            key: List key
            start: Start index
            stop: Stop index

        Returns:
            List of elements
        """
        # Simulate LRANGE latency
        self.latency_config.simulate("lrange")

        conn = self.connect()

        # Get all indices for this key (sorted)
        rows = conn.execute(
            """
            SELECT value FROM redis_lists
            WHERE key = ?
            ORDER BY idx
            """,
            (key,),
        ).fetchall()

        if not rows:
            return []

        # Convert to list
        items = [row[0] for row in rows]

        # Handle negative indices
        if start < 0:
            start = len(items) + start
        if stop < 0:
            stop = len(items) + stop

        # Slice the list
        result = items[start : stop + 1]
        return [self._decode_value(v) for v in result]

    # Set operations

    def sadd(self, key: str, *members: Any) -> int:
        """
        Add members to a set.

        Args:
            key: Set key
            *members: Members to add

        Returns:
            Number of members added
        """
        # Simulate SADD latency
        self.latency_config.simulate("sadd")

        conn = self.connect()

        # Ensure key exists as set
        conn.execute(
            """
            INSERT OR IGNORE INTO redis_keys (key, type)
            VALUES (?, 'set')
            """,
            (key,),
        )

        count = 0
        for member in members:
            encoded = self._encode_value(member)
            try:
                conn.execute(
                    "INSERT INTO redis_sets (key, member) VALUES (?, ?)",
                    (key, encoded),
                )
                count += 1
            except sqlite3.IntegrityError:
                # Member already exists
                pass

        return count

    def smembers(self, key: str) -> Set[Union[bytes, str]]:
        """
        Get all members of a set.

        Args:
            key: Set key

        Returns:
            Set of members
        """
        # Simulate SMEMBERS latency
        self.latency_config.simulate("smembers")

        conn = self.connect()

        rows = conn.execute(
            "SELECT member FROM redis_sets WHERE key = ?", (key,)
        ).fetchall()

        return {self._decode_value(row[0]) for row in rows}

    # Hash operations

    def hset(self, key: str, field: str, value: Any) -> int:
        """
        Set a hash field.

        Args:
            key: Hash key
            field: Field name
            value: Field value

        Returns:
            1 if new field, 0 if updated
        """
        # Simulate HSET latency
        self.latency_config.simulate("hset")

        conn = self.connect()

        # Ensure key exists as hash
        conn.execute(
            """
            INSERT OR IGNORE INTO redis_keys (key, type)
            VALUES (?, 'hash')
            """,
            (key,),
        )

        # Check if field exists
        existing = conn.execute(
            "SELECT 1 FROM redis_hashes WHERE key = ? AND field = ?", (key, field)
        ).fetchone()

        encoded = self._encode_value(value)
        conn.execute(
            """
            INSERT OR REPLACE INTO redis_hashes (key, field, value)
            VALUES (?, ?, ?)
            """,
            (key, field, encoded),
        )

        return 0 if existing else 1

    def hget(self, key: str, field: str) -> Union[bytes, str, None]:
        """
        Get a hash field value.

        Args:
            key: Hash key
            field: Field name

        Returns:
            Field value or None
        """
        # Simulate HGET latency
        self.latency_config.simulate("hget")

        conn = self.connect()

        result = conn.execute(
            "SELECT value FROM redis_hashes WHERE key = ? AND field = ?", (key, field)
        ).fetchone()

        if result:
            return self._decode_value(result[0])
        return None

    def hgetall(self, key: str) -> Dict[str, Union[bytes, str]]:
        """
        Get all fields and values of a hash.

        Args:
            key: Hash key

        Returns:
            Dictionary of field-value pairs
        """
        # Simulate HGETALL latency
        self.latency_config.simulate("hgetall")

        conn = self.connect()

        rows = conn.execute(
            "SELECT field, value FROM redis_hashes WHERE key = ?", (key,)
        ).fetchall()

        return {row[0]: self._decode_value(row[1]) for row in rows}

    # Pipeline support

    def pipeline(self, transaction: bool = True) -> "MockRedisPipeline":
        """
        Create a pipeline for batched commands.

        Args:
            transaction: Use transaction (MULTI/EXEC)

        Returns:
            Pipeline object
        """
        return MockRedisPipeline(self, transaction)

    def close(self) -> None:
        """Close the Redis connection."""
        if not self._closed:
            super().close()
            self._closed = True


class MockRedisPipeline:
    """Mock Redis pipeline for batched commands."""

    def __init__(self, redis: MockRedis, transaction: bool = True):
        """
        Initialize pipeline.

        Args:
            redis: Parent MockRedis instance
            transaction: Use transaction
        """
        self.redis = redis
        self.transaction = transaction
        self.commands: List[Tuple[str, Tuple, Dict]] = []

    def set(self, key: str, value: Any, **kwargs) -> "MockRedisPipeline":
        """Queue a SET command."""
        self.commands.append(("set", (key, value), kwargs))
        return self

    def get(self, key: str) -> "MockRedisPipeline":
        """Queue a GET command."""
        self.commands.append(("get", (key,), {}))
        return self

    def delete(self, *keys: str) -> "MockRedisPipeline":
        """Queue a DELETE command."""
        self.commands.append(("delete", keys, {}))
        return self

    def execute(self) -> List[Any]:
        """
        Execute all queued commands.

        Returns:
            List of command results
        """
        # Simulate pipeline execution latency
        self.redis.latency_config.simulate("pipeline_execute")

        results = []

        if self.transaction:
            # Execute in transaction
            with self.redis.transaction():
                for cmd_name, args, kwargs in self.commands:
                    method = getattr(self.redis, cmd_name)
                    result = method(*args, **kwargs)
                    results.append(result)
        else:
            # Execute without transaction
            for cmd_name, args, kwargs in self.commands:
                method = getattr(self.redis, cmd_name)
                result = method(*args, **kwargs)
                results.append(result)

        self.commands.clear()
        return results

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is None:
            self.execute()
        return False
