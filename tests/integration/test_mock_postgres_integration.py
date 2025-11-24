"""
Integration tests for MockPostgres with realistic database operations.

These tests verify that MockPostgres works correctly in realistic scenarios
and can be used for benchmarking database-heavy applications.
"""

import json
import sqlite3
import time
from typing import List

import pytest

from plainbench import benchmark
from plainbench.mocks import LatencyConfig, MockPostgres, use_mock_postgres


class TestMockPostgresIntegration:
    """Integration tests for MockPostgres."""

    def test_basic_crud_operations(self):
        """Test basic CRUD operations work correctly."""
        mock_db = MockPostgres(database=":memory:")

        with mock_db.connect() as conn:
            cursor = conn.cursor()

            # Create table
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    age INTEGER
                )
            """)

            # Insert
            cursor.execute(
                "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
                ("Alice", "alice@example.com", 30),
            )
            cursor.execute(
                "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
                ("Bob", "bob@example.com", 25),
            )
            conn.commit()

            # Read
            cursor.execute("SELECT * FROM users WHERE age >= ?", (25,))
            results = cursor.fetchall()
            assert len(results) == 2

            # Update
            cursor.execute("UPDATE users SET age = ? WHERE name = ?", (31, "Alice"))
            conn.commit()

            cursor.execute("SELECT age FROM users WHERE name = ?", ("Alice",))
            assert cursor.fetchone()[0] == 31

            # Delete
            cursor.execute("DELETE FROM users WHERE name = ?", ("Bob",))
            conn.commit()

            cursor.execute("SELECT COUNT(*) FROM users")
            assert cursor.fetchone()[0] == 1

    def test_transactions(self):
        """Test transaction support (commit and rollback)."""
        mock_db = MockPostgres(database=":memory:")

        with mock_db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance REAL)")
            cursor.execute("INSERT INTO accounts (id, balance) VALUES (1, 100.0)")
            conn.commit()

            # Test rollback
            cursor.execute("UPDATE accounts SET balance = 50.0 WHERE id = 1")
            conn.rollback()

            cursor.execute("SELECT balance FROM accounts WHERE id = 1")
            assert cursor.fetchone()[0] == 100.0

            # Test commit
            cursor.execute("UPDATE accounts SET balance = 150.0 WHERE id = 1")
            conn.commit()

            cursor.execute("SELECT balance FROM accounts WHERE id = 1")
            assert cursor.fetchone()[0] == 150.0

    def test_joins_and_aggregations(self):
        """Test complex queries with joins and aggregations."""
        mock_db = MockPostgres(database=":memory:")

        with mock_db.connect() as conn:
            cursor = conn.cursor()

            # Create schema
            cursor.execute("""
                CREATE TABLE customers (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY,
                    customer_id INTEGER,
                    amount REAL,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            """)

            # Insert test data
            cursor.execute("INSERT INTO customers (id, name) VALUES (1, 'Alice')")
            cursor.execute("INSERT INTO customers (id, name) VALUES (2, 'Bob')")

            cursor.execute("INSERT INTO orders (customer_id, amount) VALUES (1, 100.0)")
            cursor.execute("INSERT INTO orders (customer_id, amount) VALUES (1, 200.0)")
            cursor.execute("INSERT INTO orders (customer_id, amount) VALUES (2, 150.0)")
            conn.commit()

            # Test JOIN
            cursor.execute("""
                SELECT c.name, COUNT(o.id) as order_count, SUM(o.amount) as total
                FROM customers c
                LEFT JOIN orders o ON c.id = o.customer_id
                GROUP BY c.id, c.name
                ORDER BY c.name
            """)

            results = cursor.fetchall()
            assert len(results) == 2
            assert results[0] == ("Alice", 2, 300.0)
            assert results[1] == ("Bob", 1, 150.0)

    def test_latency_simulation(self):
        """Test that latency simulation adds realistic delays."""
        latency_config = LatencyConfig(
            read_latency_ms=10.0,
            write_latency_ms=20.0,
            variance_factor=0.0,  # No variance for deterministic testing
        )

        mock_db = MockPostgres(
            database=":memory:", simulate_latency=True, latency_config=latency_config
        )

        with mock_db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER, value TEXT)")
            conn.commit()

            # Measure write latency
            start = time.perf_counter()
            cursor.execute("INSERT INTO test (id, value) VALUES (1, 'test')")
            conn.commit()
            write_duration = (time.perf_counter() - start) * 1000

            # Should be at least 20ms (write latency)
            assert write_duration >= 18.0  # Allow small margin

            # Measure read latency
            start = time.perf_counter()
            cursor.execute("SELECT * FROM test")
            cursor.fetchall()
            read_duration = (time.perf_counter() - start) * 1000

            # Should be at least 10ms (read latency)
            assert read_duration >= 9.0  # Allow small margin

    def test_decorator_integration(self):
        """Test that use_mock_postgres decorator works correctly."""

        @use_mock_postgres(database=":memory:")
        def create_and_query_users(db_conn):
            cursor = db_conn.cursor()
            cursor.execute("CREATE TABLE users (id INTEGER, name TEXT)")
            cursor.execute("INSERT INTO users VALUES (1, 'Alice')")
            cursor.execute("INSERT INTO users VALUES (2, 'Bob')")
            db_conn.commit()

            cursor.execute("SELECT name FROM users ORDER BY id")
            return [row[0] for row in cursor.fetchall()]

        result = create_and_query_users()
        assert result == ["Alice", "Bob"]


class TestBenchmarkingWithMockPostgres:
    """Test benchmarking real applications with MockPostgres."""

    def test_benchmark_database_operations(self):
        """Benchmark typical database operations."""

        @use_mock_postgres(database=":memory:", simulate_latency=False)
        @benchmark(warmup=2, runs=5, store=False)
        def bench_db_operations(db_conn):
            cursor = db_conn.cursor()

            # Create table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    price REAL,
                    quantity INTEGER
                )
            """)
            db_conn.commit()

            # Bulk insert
            for i in range(100):
                cursor.execute(
                    "INSERT INTO products (name, price, quantity) VALUES (?, ?, ?)",
                    (f"Product {i}", 10.0 + i, 100),
                )
            db_conn.commit()

            # Query with aggregation
            cursor.execute("""
                SELECT COUNT(*), AVG(price), SUM(quantity)
                FROM products
                WHERE price > 50.0
            """)
            stats = cursor.fetchone()

            return {"count": stats[0], "avg_price": stats[1], "total_qty": stats[2]}

        result = bench_db_operations()
        assert result["count"] > 0
        assert result["avg_price"] > 50.0

    def test_benchmark_query_patterns(self):
        """Benchmark different query patterns."""

        @use_mock_postgres(database=":memory:", simulate_latency=False)
        @benchmark(warmup=2, runs=5, store=False)
        def bench_index_vs_no_index(db_conn):
            cursor = db_conn.cursor()

            # Create table with index
            cursor.execute("""
                CREATE TABLE indexed_users (
                    id INTEGER PRIMARY KEY,
                    email TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX idx_email ON indexed_users(email)")

            # Insert data
            for i in range(1000):
                cursor.execute(
                    "INSERT INTO indexed_users (email) VALUES (?)",
                    (f"user{i}@example.com",),
                )
            db_conn.commit()

            # Query by index
            for i in range(100):
                cursor.execute(
                    "SELECT * FROM indexed_users WHERE email = ?",
                    (f"user{i}@example.com",),
                )
                cursor.fetchone()

            return "1000 inserts + 100 indexed queries"

        result = bench_index_vs_no_index()
        assert result == "1000 inserts + 100 indexed queries"


class TestRealisticApplicationScenarios:
    """Test realistic application scenarios."""

    def test_ecommerce_order_processing(self):
        """Test e-commerce order processing scenario."""
        mock_db = MockPostgres(database=":memory:")

        with mock_db.connect() as conn:
            cursor = conn.cursor()

            # Schema
            cursor.execute("""
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY,
                    customer_id INTEGER,
                    product_id INTEGER,
                    quantity INTEGER,
                    total_price REAL,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE inventory (
                    product_id INTEGER PRIMARY KEY,
                    quantity INTEGER,
                    price REAL
                )
            """)

            # Seed inventory
            for i in range(1, 11):
                cursor.execute(
                    "INSERT INTO inventory VALUES (?, ?, ?)", (i, 100, 10.0 * i)
                )
            conn.commit()

            # Process orders
            orders_created = 0
            for customer_id in range(1, 21):
                product_id = (customer_id % 10) + 1

                # Check inventory
                cursor.execute(
                    "SELECT quantity, price FROM inventory WHERE product_id = ?",
                    (product_id,),
                )
                row = cursor.fetchone()

                if row and row[0] >= 1:
                    quantity, price = row

                    # Create order
                    cursor.execute(
                        """
                        INSERT INTO orders (customer_id, product_id, quantity, total_price, status)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (customer_id, product_id, 1, price, "pending"),
                    )

                    # Update inventory
                    cursor.execute(
                        "UPDATE inventory SET quantity = quantity - 1 WHERE product_id = ?",
                        (product_id,),
                    )

                    orders_created += 1

            conn.commit()

            # Verify
            cursor.execute("SELECT COUNT(*) FROM orders")
            assert cursor.fetchone()[0] == orders_created

            cursor.execute("SELECT SUM(quantity) FROM inventory")
            remaining = cursor.fetchone()[0]
            assert remaining == (10 * 100) - orders_created

    def test_analytics_queries(self):
        """Test analytics-style queries on large dataset."""
        mock_db = MockPostgres(database=":memory:")

        with mock_db.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    event_type TEXT,
                    timestamp INTEGER,
                    value REAL
                )
            """)

            # Generate events
            import random

            random.seed(42)
            for i in range(1000):
                cursor.execute(
                    "INSERT INTO events (user_id, event_type, timestamp, value) VALUES (?, ?, ?, ?)",
                    (
                        random.randint(1, 100),
                        random.choice(["click", "view", "purchase"]),
                        int(time.time()) - random.randint(0, 86400),
                        random.uniform(0, 100),
                    ),
                )
            conn.commit()

            # Analytics queries
            cursor.execute("""
                SELECT event_type, COUNT(*) as count, AVG(value) as avg_value
                FROM events
                GROUP BY event_type
                ORDER BY count DESC
            """)

            results = cursor.fetchall()
            assert len(results) == 3
            assert sum(r[1] for r in results) == 1000

            # User activity
            cursor.execute("""
                SELECT user_id, COUNT(*) as event_count
                FROM events
                GROUP BY user_id
                HAVING event_count > 5
                ORDER BY event_count DESC
                LIMIT 10
            """)

            top_users = cursor.fetchall()
            assert len(top_users) <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
