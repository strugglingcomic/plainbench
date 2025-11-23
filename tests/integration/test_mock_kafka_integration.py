"""
Integration tests for MockKafka with realistic event streaming operations.

These tests verify that MockKafka works correctly in realistic scenarios
and can be used for benchmarking event-driven applications.
"""

import json
import time

import pytest

from plainbench import benchmark
from plainbench.mocks import LatencyConfig, MockKafka, use_mock_kafka


class TestMockKafkaIntegration:
    """Integration tests for MockKafka."""

    def test_basic_producer_consumer(self):
        """Test basic producer and consumer operations."""
        kafka = MockKafka(database=":memory:")

        # Create producer
        producer = kafka.get_producer()

        # Send messages
        for i in range(10):
            message = f"message-{i}".encode()
            future = producer.send("test-topic", value=message)
            # Future should complete immediately in mock
            metadata = future.get(timeout=1)
            assert metadata is not None

        producer.flush()

        # Create consumer
        consumer = kafka.get_consumer("test-topic", group_id="test-group")

        # Consume messages
        messages = []
        for msg in consumer:
            messages.append(msg.value.decode())
            if len(messages) >= 10:
                break

        assert len(messages) == 10
        assert messages[0] == "message-0"
        assert messages[9] == "message-9"

    def test_multiple_topics(self):
        """Test producing and consuming from multiple topics."""
        kafka = MockKafka(database=":memory:")

        producer = kafka.get_producer()

        # Produce to different topics
        for topic in ["events", "logs", "metrics"]:
            for i in range(5):
                producer.send(topic, value=f"{topic}-{i}".encode())

        producer.flush()

        # Consume from each topic
        for topic in ["events", "logs", "metrics"]:
            consumer = kafka.get_consumer(topic, group_id=f"{topic}-group")

            messages = []
            for msg in consumer:
                messages.append(msg.value.decode())
                if len(messages) >= 5:
                    break

            assert len(messages) == 5
            assert all(topic in m for m in messages)

    def test_consumer_groups(self):
        """Test consumer groups and offset management."""
        kafka = MockKafka(database=":memory:")

        producer = kafka.get_producer()

        # Produce 20 messages
        for i in range(20):
            producer.send("group-topic", value=f"msg-{i}".encode())
        producer.flush()

        # Consumer 1 reads first 10
        consumer1 = kafka.get_consumer("group-topic", group_id="shared-group")
        messages1 = []
        for msg in consumer1:
            messages1.append(msg.value.decode())
            if len(messages1) >= 10:
                break

        assert len(messages1) == 10

        # Consumer 2 in different group should read all from beginning
        consumer2 = kafka.get_consumer("group-topic", group_id="different-group")
        messages2 = []
        for msg in consumer2:
            messages2.append(msg.value.decode())
            if len(messages2) >= 20:
                break

        assert len(messages2) == 20

    def test_message_keys(self):
        """Test producing and consuming messages with keys."""
        kafka = MockKafka(database=":memory:")

        producer = kafka.get_producer()

        # Produce messages with keys
        for i in range(10):
            key = f"key-{i % 3}".encode()  # 3 different keys
            value = f"value-{i}".encode()
            producer.send("keyed-topic", key=key, value=value)

        producer.flush()

        # Consume and verify keys
        consumer = kafka.get_consumer("keyed-topic", group_id="key-test")
        key_counts = {}

        for msg in consumer:
            key = msg.key.decode()
            key_counts[key] = key_counts.get(key, 0) + 1

            if sum(key_counts.values()) >= 10:
                break

        assert len(key_counts) == 3
        assert key_counts["key-0"] == 4  # Messages 0, 3, 6, 9
        assert key_counts["key-1"] == 3  # Messages 1, 4, 7
        assert key_counts["key-2"] == 3  # Messages 2, 5, 8

    def test_latency_simulation(self):
        """Test that latency simulation adds realistic delays."""
        latency_config = LatencyConfig(
            read_latency_ms=5.0,
            write_latency_ms=10.0,
            variance_factor=0.0,  # No variance for deterministic testing
        )

        kafka = MockKafka(
            database=":memory:", simulate_latency=True, latency_config=latency_config
        )

        producer = kafka.get_producer()

        # Measure write latency
        start = time.perf_counter()
        producer.send("latency-topic", value=b"test")
        producer.flush()
        write_duration = (time.perf_counter() - start) * 1000

        # Should be at least 10ms (write latency)
        assert write_duration >= 9.0  # Allow small margin

        # Measure read latency
        consumer = kafka.get_consumer("latency-topic", group_id="latency-test")

        start = time.perf_counter()
        for msg in consumer:
            read_duration = (time.perf_counter() - start) * 1000
            break

        # Should be at least 5ms (read latency)
        assert read_duration >= 4.0  # Allow small margin

    def test_decorator_integration(self):
        """Test that use_mock_kafka decorator works correctly."""

        @use_mock_kafka(database=":memory:")
        def produce_and_consume_events(kafka_producer, kafka_consumer):
            # Produce events
            events = []
            for i in range(5):
                event = {"type": "user_action", "user_id": i, "timestamp": time.time()}
                kafka_producer.send("events", value=json.dumps(event).encode())
                events.append(event)

            kafka_producer.flush()

            # Consume events
            consumed = []
            for msg in kafka_consumer:
                consumed.append(json.loads(msg.value.decode()))
                if len(consumed) >= 5:
                    break

            return consumed

        result = produce_and_consume_events()
        assert len(result) == 5
        assert all(e["type"] == "user_action" for e in result)


class TestBenchmarkingWithMockKafka:
    """Test benchmarking real applications with MockKafka."""

    def test_benchmark_event_production(self):
        """Benchmark event production throughput."""

        @use_mock_kafka(database=":memory:", simulate_latency=False)
        @benchmark(warmup=2, runs=5, store=False)
        def bench_produce_events(kafka_producer, kafka_consumer):
            # Produce 100 events
            for i in range(100):
                event = {
                    "event_id": i,
                    "event_type": "page_view",
                    "user_id": 1000 + (i % 10),
                    "timestamp": time.time(),
                }
                kafka_producer.send("analytics", value=json.dumps(event).encode())

            kafka_producer.flush()
            return "100 events produced"

        result = bench_produce_events()
        assert result == "100 events produced"

    def test_benchmark_event_consumption(self):
        """Benchmark event consumption throughput."""

        @use_mock_kafka(database=":memory:", simulate_latency=False)
        @benchmark(warmup=2, runs=5, store=False)
        def bench_consume_events(kafka_producer, kafka_consumer):
            # Produce events first
            for i in range(100):
                kafka_producer.send("processing", value=f"event-{i}".encode())
            kafka_producer.flush()

            # Consume and process
            processed = 0
            for msg in kafka_consumer:
                # Simulate processing
                event_id = msg.value.decode()
                processed += 1

                if processed >= 100:
                    break

            return processed

        result = bench_consume_events()
        assert result == 100


class TestRealisticEventStreamingScenarios:
    """Test realistic event streaming scenarios."""

    def test_clickstream_processing(self):
        """Test clickstream event processing scenario."""
        kafka = MockKafka(database=":memory:")

        producer = kafka.get_producer()

        # Simulate clickstream events
        clicks = []
        for user_id in range(1, 11):
            for page in ["home", "products", "cart", "checkout"]:
                event = {
                    "user_id": user_id,
                    "page": page,
                    "timestamp": int(time.time()),
                    "session_id": f"session-{user_id}",
                }
                clicks.append(event)
                producer.send("clickstream", value=json.dumps(event).encode())

        producer.flush()

        # Process events
        consumer = kafka.get_consumer("clickstream", group_id="analytics")

        user_paths = {}
        events_processed = 0

        for msg in consumer:
            event = json.loads(msg.value.decode())
            user_id = event["user_id"]

            if user_id not in user_paths:
                user_paths[user_id] = []

            user_paths[user_id].append(event["page"])
            events_processed += 1

            if events_processed >= len(clicks):
                break

        # Verify all users completed the flow
        assert len(user_paths) == 10
        for user_id, path in user_paths.items():
            assert path == ["home", "products", "cart", "checkout"]

    def test_order_event_pipeline(self):
        """Test order event processing pipeline."""
        kafka = MockKafka(database=":memory:")

        producer = kafka.get_producer()

        # Produce order events
        orders = []
        for order_id in range(1, 21):
            # Order created event
            created_event = {
                "event_type": "order_created",
                "order_id": order_id,
                "customer_id": 1000 + (order_id % 5),
                "amount": 100.0 + order_id,
                "timestamp": time.time(),
            }
            producer.send("orders", value=json.dumps(created_event).encode())
            orders.append(created_event)

            # Order confirmed event
            confirmed_event = {
                "event_type": "order_confirmed",
                "order_id": order_id,
                "timestamp": time.time(),
            }
            producer.send("orders", value=json.dumps(confirmed_event).encode())

        producer.flush()

        # Process events
        consumer = kafka.get_consumer("orders", group_id="order-processor")

        created_count = 0
        confirmed_count = 0

        for msg in consumer:
            event = json.loads(msg.value.decode())

            if event["event_type"] == "order_created":
                created_count += 1
            elif event["event_type"] == "order_confirmed":
                confirmed_count += 1

            if created_count >= 20 and confirmed_count >= 20:
                break

        assert created_count == 20
        assert confirmed_count == 20

    def test_event_aggregation(self):
        """Test event aggregation scenario."""
        kafka = MockKafka(database=":memory:")

        producer = kafka.get_producer()

        # Produce metric events
        import random

        random.seed(42)

        for i in range(100):
            metric = {
                "metric_name": random.choice(["cpu", "memory", "disk", "network"]),
                "value": random.uniform(0, 100),
                "host": f"server-{random.randint(1, 5)}",
                "timestamp": time.time(),
            }
            producer.send("metrics", value=json.dumps(metric).encode())

        producer.flush()

        # Aggregate metrics
        consumer = kafka.get_consumer("metrics", group_id="aggregator")

        aggregations = {}

        for msg in consumer:
            metric = json.loads(msg.value.decode())
            key = metric["metric_name"]

            if key not in aggregations:
                aggregations[key] = {"count": 0, "sum": 0.0, "min": float("inf"), "max": 0.0}

            agg = aggregations[key]
            agg["count"] += 1
            agg["sum"] += metric["value"]
            agg["min"] = min(agg["min"], metric["value"])
            agg["max"] = max(agg["max"], metric["value"])

            if sum(a["count"] for a in aggregations.values()) >= 100:
                break

        # Verify aggregations
        assert len(aggregations) == 4
        for metric_name, agg in aggregations.items():
            assert agg["count"] > 0
            assert agg["min"] <= agg["max"]

    def test_event_replay(self):
        """Test event replay scenario (reprocessing from offset 0)."""
        kafka = MockKafka(database=":memory:")

        producer = kafka.get_producer()

        # Produce events
        for i in range(20):
            producer.send("replay-topic", value=f"event-{i}".encode())
        producer.flush()

        # First consumer processes all events
        consumer1 = kafka.get_consumer("replay-topic", group_id="group1")
        first_pass = []
        for msg in consumer1:
            first_pass.append(msg.value.decode())
            if len(first_pass) >= 20:
                break

        assert len(first_pass) == 20

        # Second consumer in different group can replay all events
        consumer2 = kafka.get_consumer("replay-topic", group_id="group2")
        second_pass = []
        for msg in consumer2:
            second_pass.append(msg.value.decode())
            if len(second_pass) >= 20:
                break

        assert len(second_pass) == 20
        assert first_pass == second_pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
