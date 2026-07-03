"""Base classes for mock data stores."""

import random
import sqlite3
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Optional

# Named infrastructure profiles: the network round-trip time (in seconds) your
# application would pay per operation, depending on where the datastore lives
# relative to the application. Every mock operation models one client round trip,
# so the RTT is added on top of the store's base processing latency.
#
# Values are typical figures for cloud deployments (loopback, intra-AZ,
# inter-AZ, inter-region, and intercontinental links respectively).
NETWORK_PROFILES: Dict[str, float] = {
    "in_process": 0.0,  # no network at all: raw SQLite-backed mock speed
    "same_host": 0.00005,  # loopback / unix socket: ~0.05ms
    "same_zone": 0.0005,  # same availability zone: ~0.5ms
    "same_region": 0.002,  # cross-AZ within a region: ~2ms
    "cross_region": 0.060,  # e.g. us-east <-> us-west: ~60ms
    "cross_continent": 0.150,  # e.g. us <-> eu/apac: ~150ms
}


@dataclass
class LatencyConfig:
    """
    Configuration for simulating realistic latencies in mock data stores.

    This allows benchmarking application logic with production-like latencies
    while still using fast SQLite-backed mocks. Latencies are based on research
    of typical production systems in same-datacenter environments.

    Research sources:
    - PostgreSQL: Typical query latencies range from 0.5-5ms for simple indexed
      queries, 5-20ms for complex queries with joins, and a few milliseconds
      for write operations in same-datacenter deployments.
    - Kafka: Well-tuned clusters achieve <1-2ms for low-latency configs,
      2-50ms for balanced throughput/latency, with p99 latencies of 50-200ms.
    - Redis: Command processing is sub-microsecond, but network round-trips
      in same datacenter add 100-300 microseconds (0.1-0.3ms) typically.

    Attributes:
        enabled: Whether latency simulation is active
        default_latency: Default latency in seconds if operation not configured
        variance: Variance factor (0.0 = no variance, 1.0 = high variance)
                  Actual latency = base * (1 + random.uniform(-variance, +variance))
        operation_latencies: Dict mapping operation names to base latencies (seconds)
    """

    enabled: bool = False
    default_latency: float = 0.001  # 1ms default
    variance: float = 0.2  # ±20% variance
    operation_latencies: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def for_profile(
        cls,
        profile: str,
        base_latencies: Optional[Dict[str, float]] = None,
    ) -> "LatencyConfig":
        """
        Build a LatencyConfig for a named infrastructure profile.

        The profile's network round-trip time is added to every operation's
        base processing latency, so the same application code can be
        benchmarked under different infrastructure assumptions.

        Args:
            profile: One of NETWORK_PROFILES (e.g. 'same_zone', 'cross_region')
            base_latencies: Per-operation processing latencies to layer the
                network RTT onto (e.g. DEFAULT_POSTGRES_LATENCIES). Defaults
                to no processing latency.

        Returns:
            LatencyConfig with the profile applied. The 'in_process' profile
            returns a disabled config (zero simulated latency).
        """
        if profile not in NETWORK_PROFILES:
            raise ValueError(
                f"Unknown profile: {profile!r}. "
                f"Available profiles: {', '.join(NETWORK_PROFILES)}"
            )

        rtt = NETWORK_PROFILES[profile]
        if profile == "in_process":
            return cls(enabled=False)

        base = base_latencies or {}
        return cls(
            enabled=True,
            default_latency=0.001 + rtt,
            operation_latencies={op: latency + rtt for op, latency in base.items()},
        )

    def get_latency(self, operation: str) -> float:
        """
        Get latency for specific operation with variance applied.

        Args:
            operation: Name of the operation (e.g., 'execute_simple', 'get')

        Returns:
            Actual latency in seconds (with variance applied)
        """
        if not self.enabled:
            return 0.0

        # Get base latency
        base_latency = self.operation_latencies.get(operation, self.default_latency)

        # Apply variance
        variance_factor = random.uniform(-self.variance, self.variance)
        actual_latency = base_latency * (1 + variance_factor)

        return max(0.0, actual_latency)

    def simulate(self, operation: str) -> None:
        """
        Sleep to simulate latency for the given operation.

        Args:
            operation: Name of the operation
        """
        latency = self.get_latency(operation)
        if latency > 0:
            time.sleep(latency)


class MockDataStore(ABC):
    """
    Abstract base class for mock data stores.

    All mock implementations should inherit from this class and implement
    the required methods. Subclasses may set DEFAULT_LATENCIES to their
    typical per-operation processing latencies, which are used when a
    named infrastructure profile is requested.
    """

    DEFAULT_LATENCIES: Dict[str, float] = {}

    def __init__(
        self,
        database: str = ":memory:",
        latency_config: Optional[LatencyConfig] = None,
        profile: Optional[str] = None,
        **config,
    ):
        """
        Initialize the mock data store.

        Args:
            database: SQLite database path (default: in-memory)
            latency_config: Configuration for latency simulation
            profile: Named infrastructure profile (see NETWORK_PROFILES),
                e.g. 'same_zone' or 'cross_region'. Ignored if
                latency_config is given.
            **config: Additional configuration options
        """
        self.database = database
        if latency_config is None and profile is not None:
            latency_config = LatencyConfig.for_profile(profile, type(self).DEFAULT_LATENCIES)
        self.latency_config = latency_config or LatencyConfig()
        self.config = config
        self._connection: Optional[sqlite3.Connection] = None

    @abstractmethod
    def _init_schema(self) -> None:
        """Initialize the database schema."""
        pass

    def connect(self) -> sqlite3.Connection:
        """
        Get or create the SQLite connection.

        Returns:
            SQLite connection object
        """
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.database,
                check_same_thread=False,  # Allow multi-threaded access
                isolation_level="DEFERRED",  # Use standard transaction mode
            )
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency
            self._connection.execute("PRAGMA journal_mode = WAL")
            # Initialize schema
            self._init_schema()

        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.

        Example:
            with mock_store.transaction():
                # Do work
                pass
        """
        conn = self.connect()
        try:
            conn.execute("BEGIN")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


class ConnectionPool:
    """
    Simple connection pool for mock data stores.

    This simulates connection pooling without the overhead of real
    connection pool implementations.
    """

    def __init__(self, database: str = ":memory:", max_connections: int = 10):
        """
        Initialize the connection pool.

        Args:
            database: SQLite database path
            max_connections: Maximum number of connections (for API compatibility)
        """
        self.database = database
        self.max_connections = max_connections
        self._connections: Dict[int, sqlite3.Connection] = {}

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a connection from the pool.

        In SQLite, we reuse a single connection per thread.

        Returns:
            SQLite connection
        """
        import threading

        thread_id = threading.get_ident()

        if thread_id not in self._connections:
            conn = sqlite3.connect(
                self.database, check_same_thread=False, isolation_level=None
            )
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            self._connections[thread_id] = conn

        return self._connections[thread_id]

    def close_all(self) -> None:
        """Close all connections in the pool."""
        for conn in self._connections.values():
            conn.close()
        self._connections.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_all()
        return False
