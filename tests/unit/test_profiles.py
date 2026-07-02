"""Unit tests for infrastructure latency profiles."""

import time

import pytest

from plainbench.mocks import (
    DEFAULT_POSTGRES_LATENCIES,
    NETWORK_PROFILES,
    LatencyConfig,
    MockPostgresConnection,
    MockRedis,
    use_mock_redis,
)


class TestLatencyConfigForProfile:
    def test_in_process_is_disabled(self):
        config = LatencyConfig.for_profile("in_process")
        assert not config.enabled
        assert config.get_latency("anything") == 0.0

    def test_rtt_added_to_base_latencies(self):
        config = LatencyConfig.for_profile("cross_region", {"query": 0.001})
        assert config.enabled
        assert config.operation_latencies["query"] == pytest.approx(
            0.001 + NETWORK_PROFILES["cross_region"]
        )

    def test_default_latency_includes_rtt(self):
        config = LatencyConfig.for_profile("same_region")
        assert config.default_latency == pytest.approx(
            0.001 + NETWORK_PROFILES["same_region"]
        )

    def test_unknown_profile_raises(self):
        with pytest.raises(ValueError, match="Unknown profile"):
            LatencyConfig.for_profile("the_moon")

    def test_all_profiles_are_constructible(self):
        for profile in NETWORK_PROFILES:
            LatencyConfig.for_profile(profile, DEFAULT_POSTGRES_LATENCIES)


class TestMockProfileIntegration:
    def test_postgres_profile_kwarg(self):
        conn = MockPostgresConnection(profile="same_zone")
        expected = (
            DEFAULT_POSTGRES_LATENCIES["execute_simple"]
            + NETWORK_PROFILES["same_zone"]
        )
        assert conn.latency_config.operation_latencies["execute_simple"] == pytest.approx(expected)
        conn.close()

    def test_redis_profile_adds_measurable_latency(self):
        redis = MockRedis(profile="same_region")
        start = time.perf_counter()
        redis.set("key", "value")
        elapsed = time.perf_counter() - start
        redis.close()
        # base 0.5ms + 2ms RTT, ±20% variance
        assert elapsed >= 0.0015

    def test_in_process_profile_has_no_latency(self):
        redis = MockRedis(profile="in_process")
        assert not redis.latency_config.enabled
        redis.close()

    def test_pipeline_is_one_round_trip(self):
        redis = MockRedis(profile="same_region")
        try:
            start = time.perf_counter()
            with redis.pipeline() as pipe:
                for i in range(20):
                    pipe.set(f"k{i}", "v")
                pipe.execute()
            elapsed = time.perf_counter() - start
            # 20 individual SETs would cost >= 20 * 2ms RTT; one pipeline
            # round trip is ~2.5ms + variance.
            assert elapsed < 0.020
            assert redis.latency_config.enabled  # config restored afterwards
        finally:
            redis.close()

    def test_explicit_latency_config_wins_over_profile(self):
        config = LatencyConfig(enabled=False)
        conn = MockPostgresConnection(latency_config=config, profile="cross_region")
        assert conn.latency_config is config
        conn.close()


class TestDecoratorProfileIntegration:
    def test_profile_kwarg_on_decorator(self):
        @use_mock_redis(profile="same_zone")
        def check(redis):
            return redis.latency_config

        config = check()
        assert config.enabled
        assert config.operation_latencies["get"] > 0

    def test_custom_latencies_override_profile(self):
        @use_mock_redis(profile="same_zone", custom_latencies={"get": 0.5})
        def check(redis):
            return redis.latency_config

        assert check().operation_latencies["get"] == 0.5

    def test_no_latency_by_default(self):
        @use_mock_redis()
        def check(redis):
            return redis.latency_config

        assert not check().enabled
