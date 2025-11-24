"""
Realistic E-Commerce Order Processing Application

This example demonstrates benchmarking a realistic application that uses:
- PostgreSQL for order database
- Redis for caching
- Kafka for event streaming

The benchmarks use mock implementations to isolate application logic performance.
"""

import json
import time
from typing import Dict, List, Optional

from plainbench import benchmark
from plainbench.mocks import LatencyConfig, use_mock_kafka, use_mock_postgres, use_mock_redis


# ============================================================================
# Application Code (What we're benchmarking)
# ============================================================================


class OrderProcessor:
    """
    E-commerce order processing system.

    Realistic flow:
    1. Check inventory in cache (Redis)
    2. Create order in database (Postgres)
    3. Update inventory
    4. Send order confirmation event (Kafka)
    """

    def __init__(self, db_conn, cache, event_producer):
        self.db_conn = db_conn
        self.cache = cache
        self.producer = event_producer
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema."""
        cursor = self.db_conn.cursor()

        # Create orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                total_price REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create inventory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                product_id INTEGER PRIMARY KEY,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL
            )
        """)

        # Seed some initial inventory
        for product_id in range(1, 101):
            cursor.execute(
                "INSERT OR IGNORE INTO inventory (product_id, quantity, price) VALUES (?, ?, ?)",
                (product_id, 1000, 10.0 + product_id),
            )

        self.db_conn.commit()

    def get_inventory(self, product_id: int) -> Optional[Dict]:
        """Get inventory with Redis caching."""
        # Check cache first
        cache_key = f"inventory:{product_id}"
        cached = self.cache.get(cache_key)

        if cached:
            return json.loads(cached)

        # Cache miss - query database
        cursor = self.db_conn.cursor()
        cursor.execute(
            "SELECT product_id, quantity, price FROM inventory WHERE product_id = ?",
            (product_id,),
        )
        row = cursor.fetchone()

        if row:
            inventory = {"product_id": row[0], "quantity": row[1], "price": row[2]}
            # Cache for 60 seconds
            self.cache.setex(cache_key, 60, json.dumps(inventory))
            return inventory

        return None

    def create_order(
        self, customer_id: int, product_id: int, quantity: int
    ) -> Optional[Dict]:
        """
        Create a new order with inventory check.

        Returns:
            Order dict if successful, None if insufficient inventory
        """
        # Get inventory (with caching)
        inventory = self.get_inventory(product_id)

        if not inventory or inventory["quantity"] < quantity:
            return None  # Insufficient inventory

        # Calculate total price
        total_price = inventory["price"] * quantity

        # Create order in database
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            INSERT INTO orders (customer_id, product_id, quantity, total_price, status)
            VALUES (?, ?, ?, ?, ?)
        """,
            (customer_id, product_id, quantity, total_price, "pending"),
        )
        order_id = cursor.lastrowid

        # Update inventory
        cursor.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE product_id = ?",
            (quantity, product_id),
        )

        self.db_conn.commit()

        # Invalidate cache
        self.cache.delete(f"inventory:{product_id}")

        # Publish order created event
        order_event = {
            "event_type": "order_created",
            "order_id": order_id,
            "customer_id": customer_id,
            "product_id": product_id,
            "quantity": quantity,
            "total_price": total_price,
            "timestamp": time.time(),
        }

        self.producer.send("orders", value=json.dumps(order_event).encode())
        self.producer.flush()

        return {
            "id": order_id,
            "customer_id": customer_id,
            "product_id": product_id,
            "quantity": quantity,
            "total_price": total_price,
            "status": "pending",
        }

    def get_customer_orders(self, customer_id: int) -> List[Dict]:
        """Get all orders for a customer."""
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            SELECT id, customer_id, product_id, quantity, total_price, status
            FROM orders
            WHERE customer_id = ?
            ORDER BY id DESC
        """,
            (customer_id,),
        )

        orders = []
        for row in cursor.fetchall():
            orders.append(
                {
                    "id": row[0],
                    "customer_id": row[1],
                    "product_id": row[2],
                    "quantity": row[3],
                    "total_price": row[4],
                    "status": row[5],
                }
            )

        return orders

    def get_order_stats(self) -> Dict:
        """Get order statistics (cached)."""
        cache_key = "stats:orders"
        cached = self.cache.get(cache_key)

        if cached:
            return json.loads(cached)

        # Calculate stats from database
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_orders,
                SUM(total_price) as total_revenue,
                AVG(total_price) as avg_order_value
            FROM orders
        """
        )
        row = cursor.fetchone()

        stats = {
            "total_orders": row[0] or 0,
            "total_revenue": row[1] or 0.0,
            "avg_order_value": row[2] or 0.0,
        }

        # Cache for 30 seconds
        self.cache.setex(cache_key, 30, json.dumps(stats))

        return stats


# ============================================================================
# Benchmark Tests
# ============================================================================

# Use realistic latency simulation
realistic_latency = LatencyConfig(
    read_latency_ms=0.5,  # 0.5ms read latency
    write_latency_ms=1.0,  # 1ms write latency
    variance_factor=0.2,  # ±20% variance
)


@use_mock_postgres(database=":memory:", simulate_latency=True, latency_config=realistic_latency)
@use_mock_redis(database=":memory:", simulate_latency=True, latency_config=realistic_latency)
@use_mock_kafka(simulate_latency=True, latency_config=realistic_latency)
@benchmark(warmup=5, runs=20, metrics=["wall_time", "cpu_time", "python_memory"])
def bench_create_order(db_conn, redis, kafka_producer):
    """Benchmark order creation (realistic e-commerce flow)."""
    processor = OrderProcessor(db_conn, redis, kafka_producer)

    # Create 10 orders
    for i in range(10):
        processor.create_order(
            customer_id=1000 + (i % 10), product_id=1 + (i % 100), quantity=1 + (i % 5)
        )

    return processor.get_order_stats()


@use_mock_postgres(database=":memory:", simulate_latency=True, latency_config=realistic_latency)
@use_mock_redis(database=":memory:", simulate_latency=True, latency_config=realistic_latency)
@use_mock_kafka(simulate_latency=True, latency_config=realistic_latency)
@benchmark(warmup=5, runs=20, metrics=["wall_time", "cpu_time", "python_memory"])
def bench_inventory_lookup_with_cache(db_conn, redis, kafka_producer):
    """Benchmark inventory lookup with cache hits/misses."""
    processor = OrderProcessor(db_conn, redis, kafka_producer)

    # First pass: all cache misses
    for product_id in range(1, 51):
        processor.get_inventory(product_id)

    # Second pass: all cache hits
    for product_id in range(1, 51):
        processor.get_inventory(product_id)

    return "50 cache misses + 50 cache hits"


@use_mock_postgres(database=":memory:", simulate_latency=True, latency_config=realistic_latency)
@use_mock_redis(database=":memory:", simulate_latency=True, latency_config=realistic_latency)
@use_mock_kafka(simulate_latency=True, latency_config=realistic_latency)
@benchmark(warmup=5, runs=20, metrics=["wall_time", "cpu_time", "python_memory"])
def bench_customer_order_history(db_conn, redis, kafka_producer):
    """Benchmark fetching customer order history."""
    processor = OrderProcessor(db_conn, redis, kafka_producer)

    # Create orders for multiple customers
    for i in range(50):
        processor.create_order(customer_id=1000 + (i % 10), product_id=1 + i, quantity=1)

    # Fetch order history for each customer
    results = []
    for customer_id in range(1000, 1010):
        orders = processor.get_customer_orders(customer_id)
        results.append(len(orders))

    return sum(results)


@use_mock_postgres(database=":memory:", simulate_latency=False)  # No latency for pure logic test
@use_mock_redis(database=":memory:", simulate_latency=False)
@use_mock_kafka(simulate_latency=False)
@benchmark(warmup=5, runs=20, metrics=["wall_time", "cpu_time", "python_memory"])
def bench_order_processing_logic_only(db_conn, redis, kafka_producer):
    """Benchmark pure application logic without simulated latency."""
    processor = OrderProcessor(db_conn, redis, kafka_producer)

    # Process 100 orders
    for i in range(100):
        processor.create_order(customer_id=1000 + i, product_id=1 + (i % 100), quantity=1)

    return processor.get_order_stats()


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("PlainBench: Realistic E-Commerce Application Benchmark")
    print("=" * 80)
    print()

    print("Running benchmarks with realistic latency simulation...")
    print()

    print("1. Order Creation (10 orders per run)")
    stats1 = bench_create_order()
    print(f"   Final stats: {stats1}")
    print()

    print("2. Inventory Lookup with Caching (50 misses + 50 hits)")
    result2 = bench_inventory_lookup_with_cache()
    print(f"   Result: {result2}")
    print()

    print("3. Customer Order History (50 orders, 10 customers)")
    total_orders = bench_customer_order_history()
    print(f"   Total orders retrieved: {total_orders}")
    print()

    print("4. Pure Application Logic (no latency simulation)")
    stats4 = bench_order_processing_logic_only()
    print(f"   Final stats: {stats4}")
    print()

    print("=" * 80)
    print("Benchmarks complete! Results saved to ./benchmarks.db")
    print("=" * 80)
