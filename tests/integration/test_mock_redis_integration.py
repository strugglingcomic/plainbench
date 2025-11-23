"""
Integration tests for MockRedis with realistic caching operations.

These tests verify that MockRedis works correctly in realistic scenarios
and can be used for benchmarking cache-heavy applications.
"""

import json
import time

import pytest

from plainbench import benchmark
from plainbench.mocks import LatencyConfig, MockRedis, use_mock_redis


class TestMockRedisIntegration:
    """Integration tests for MockRedis."""

    def test_basic_string_operations(self):
        """Test basic string operations."""
        redis = MockRedis(database=":memory:")

        # Set and get
        redis.set("key1", "value1")
        assert redis.get("key1") == b"value1"

        # Set with expiration
        redis.setex("temp_key", 60, "temp_value")
        assert redis.get("temp_key") == b"temp_value"
        assert redis.ttl("temp_key") <= 60

        # Multiple set/get
        redis.mset({"key2": "value2", "key3": "value3"})
        assert redis.mget(["key2", "key3"]) == [b"value2", b"value3"]

        # Delete
        redis.delete("key1")
        assert redis.get("key1") is None

    def test_list_operations(self):
        """Test list operations."""
        redis = MockRedis(database=":memory:")

        # Push operations
        redis.rpush("mylist", "item1", "item2", "item3")
        redis.lpush("mylist", "item0")

        # Get range
        items = redis.lrange("mylist", 0, -1)
        assert items == [b"item0", b"item1", b"item2", b"item3"]

        # Pop operations
        assert redis.lpop("mylist") == b"item0"
        assert redis.rpop("mylist") == b"item3"

        # Length
        assert redis.llen("mylist") == 2

    def test_set_operations(self):
        """Test set operations."""
        redis = MockRedis(database=":memory:")

        # Add members
        redis.sadd("set1", "member1", "member2", "member3")
        redis.sadd("set2", "member2", "member3", "member4")

        # Members
        members = redis.smembers("set1")
        assert members == {b"member1", b"member2", b"member3"}

        # Cardinality
        assert redis.scard("set1") == 3

        # Is member
        assert redis.sismember("set1", "member1") == 1
        assert redis.sismember("set1", "member99") == 0

        # Set operations
        intersection = redis.sinter("set1", "set2")
        assert intersection == {b"member2", b"member3"}

        union = redis.sunion("set1", "set2")
        assert union == {b"member1", b"member2", b"member3", b"member4"}

    def test_hash_operations(self):
        """Test hash operations."""
        redis = MockRedis(database=":memory:")

        # Set hash fields
        redis.hset("user:1", "name", "Alice")
        redis.hset("user:1", "email", "alice@example.com")
        redis.hset("user:1", "age", "30")

        # Get field
        assert redis.hget("user:1", "name") == b"Alice"

        # Get all
        user_data = redis.hgetall("user:1")
        assert user_data == {
            b"name": b"Alice",
            b"email": b"alice@example.com",
            b"age": b"30",
        }

        # Multiple set
        redis.hmset("user:2", {"name": "Bob", "email": "bob@example.com"})
        assert redis.hget("user:2", "name") == b"Bob"

        # Field exists
        assert redis.hexists("user:1", "name") == 1
        assert redis.hexists("user:1", "invalid") == 0

    def test_key_expiration(self):
        """Test key expiration functionality."""
        redis = MockRedis(database=":memory:")

        # Set with expiration
        redis.setex("temp", 2, "temporary")
        assert redis.exists("temp") == 1

        # Check TTL
        ttl = redis.ttl("temp")
        assert 0 < ttl <= 2

        # Wait for expiration (simulate with manual expiration for testing)
        time.sleep(0.1)  # Small sleep to ensure time passes

        # Key should still exist (2 seconds not passed yet)
        assert redis.exists("temp") == 1

        # Set expiration on existing key
        redis.set("persist_key", "value")
        redis.expire("persist_key", 60)
        assert redis.ttl("persist_key") <= 60

    def test_pipeline_operations(self):
        """Test pipeline for batch operations."""
        redis = MockRedis(database=":memory:")

        # Use pipeline
        pipe = redis.pipeline()
        pipe.set("key1", "value1")
        pipe.set("key2", "value2")
        pipe.get("key1")
        pipe.get("key2")
        results = pipe.execute()

        assert results == [True, True, b"value1", b"value2"]

    def test_latency_simulation(self):
        """Test that latency simulation adds realistic delays."""
        latency_config = LatencyConfig(
            read_latency_ms=5.0,
            write_latency_ms=10.0,
            variance_factor=0.0,  # No variance for deterministic testing
        )

        redis = MockRedis(
            database=":memory:", simulate_latency=True, latency_config=latency_config
        )

        # Measure write latency
        start = time.perf_counter()
        redis.set("test_key", "test_value")
        write_duration = (time.perf_counter() - start) * 1000

        # Should be at least 10ms (write latency)
        assert write_duration >= 9.0  # Allow small margin

        # Measure read latency
        start = time.perf_counter()
        redis.get("test_key")
        read_duration = (time.perf_counter() - start) * 1000

        # Should be at least 5ms (read latency)
        assert read_duration >= 4.0  # Allow small margin

    def test_decorator_integration(self):
        """Test that use_mock_redis decorator works correctly."""

        @use_mock_redis(database=":memory:")
        def cache_user_data(redis):
            # Store user data
            redis.hmset(
                "user:1000", {"name": "Charlie", "email": "charlie@example.com", "points": "150"}
            )

            # Store user's recent items in a list
            redis.rpush("user:1000:items", "item1", "item2", "item3")

            # Store user's tags in a set
            redis.sadd("user:1000:tags", "premium", "active", "verified")

            # Retrieve data
            user_info = redis.hgetall("user:1000")
            items = redis.lrange("user:1000:items", 0, -1)
            tags = redis.smembers("user:1000:tags")

            return {
                "user": user_info,
                "items": items,
                "tags": tags,
            }

        result = cache_user_data()
        assert result["user"][b"name"] == b"Charlie"
        assert len(result["items"]) == 3
        assert len(result["tags"]) == 3


class TestBenchmarkingWithMockRedis:
    """Test benchmarking real applications with MockRedis."""

    def test_benchmark_cache_operations(self):
        """Benchmark typical cache operations."""

        @use_mock_redis(database=":memory:", simulate_latency=False)
        @benchmark(warmup=2, runs=5, store=False)
        def bench_cache_ops(redis):
            # Write phase: store 100 items
            for i in range(100):
                redis.set(f"item:{i}", f"value_{i}")
                redis.setex(f"temp:{i}", 60, f"temp_value_{i}")

            # Read phase: retrieve all items
            for i in range(100):
                redis.get(f"item:{i}")
                redis.get(f"temp:{i}")

            # Batch operations
            keys = [f"item:{i}" for i in range(50)]
            values = redis.mget(keys)

            return len(values)

        result = bench_cache_ops()
        assert result == 50

    def test_benchmark_cache_hit_miss_ratio(self):
        """Benchmark cache hit/miss patterns."""

        @use_mock_redis(database=":memory:", simulate_latency=False)
        @benchmark(warmup=2, runs=5, store=False)
        def bench_cache_patterns(redis):
            # Populate cache with 50 items
            for i in range(50):
                redis.set(f"cached:{i}", f"data_{i}")

            hits = 0
            misses = 0

            # Mixed hit/miss pattern
            for i in range(100):
                value = redis.get(f"cached:{i}")
                if value:
                    hits += 1
                else:
                    misses += 1

            return {"hits": hits, "misses": misses, "ratio": hits / (hits + misses)}

        result = bench_cache_patterns()
        assert result["hits"] == 50
        assert result["misses"] == 50
        assert result["ratio"] == 0.5


class TestRealisticCachingScenarios:
    """Test realistic caching scenarios."""

    def test_session_management(self):
        """Test session management scenario."""
        redis = MockRedis(database=":memory:")

        # Create sessions
        sessions = {}
        for user_id in range(1, 11):
            session_id = f"session:{user_id}:abc123"
            session_data = json.dumps(
                {
                    "user_id": user_id,
                    "logged_in_at": int(time.time()),
                    "permissions": ["read", "write"],
                }
            )

            # Store session with 1 hour expiration
            redis.setex(session_id, 3600, session_data)
            sessions[user_id] = session_id

        # Verify sessions exist
        for user_id, session_id in sessions.items():
            session_json = redis.get(session_id)
            assert session_json is not None

            session = json.loads(session_json)
            assert session["user_id"] == user_id

        # Invalidate a session
        redis.delete(sessions[5])
        assert redis.get(sessions[5]) is None

    def test_leaderboard(self):
        """Test leaderboard/ranking scenario using sorted sets."""
        redis = MockRedis(database=":memory:")

        # Note: MockRedis doesn't implement sorted sets yet,
        # so we'll use a workaround with hashes

        leaderboard = "game:leaderboard"

        # Store player scores
        for player_id in range(1, 21):
            import random

            random.seed(player_id)
            score = random.randint(0, 1000)
            redis.hset(leaderboard, f"player:{player_id}", str(score))

        # Get all scores
        scores = redis.hgetall(leaderboard)
        assert len(scores) == 20

        # Verify scores are stored
        player_1_score = int(redis.hget(leaderboard, "player:1"))
        assert player_1_score >= 0

    def test_rate_limiting(self):
        """Test rate limiting scenario."""
        redis = MockRedis(database=":memory:")

        def check_rate_limit(user_id: str, limit: int = 10, window: int = 60) -> bool:
            """
            Check if user is within rate limit.

            Returns:
                True if request is allowed, False if rate limited
            """
            key = f"rate_limit:{user_id}"
            current = redis.get(key)

            if current is None:
                # First request in window
                redis.setex(key, window, "1")
                return True

            count = int(current)
            if count >= limit:
                return False

            # Increment counter
            redis.incr(key)
            return True

        # Make requests
        user = "user:123"
        allowed_requests = 0
        blocked_requests = 0

        for i in range(15):
            if check_rate_limit(user, limit=10):
                allowed_requests += 1
            else:
                blocked_requests += 1

        assert allowed_requests == 10
        assert blocked_requests == 5

    def test_distributed_cache(self):
        """Test distributed cache scenario with cache-aside pattern."""
        redis = MockRedis(database=":memory:")

        def get_user_profile(user_id: int) -> dict:
            """Get user profile with cache-aside pattern."""
            cache_key = f"user:profile:{user_id}"

            # Check cache
            cached = redis.get(cache_key)
            if cached:
                return json.loads(cached)

            # Cache miss - simulate database fetch
            profile = {
                "id": user_id,
                "name": f"User {user_id}",
                "email": f"user{user_id}@example.com",
                "created_at": int(time.time()),
            }

            # Store in cache with 5 minute TTL
            redis.setex(cache_key, 300, json.dumps(profile))

            return profile

        # First access - cache miss
        profile1 = get_user_profile(100)
        assert profile1["id"] == 100

        # Second access - cache hit
        profile2 = get_user_profile(100)
        assert profile2 == profile1

        # Verify cache was used
        cached = redis.get("user:profile:100")
        assert cached is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
