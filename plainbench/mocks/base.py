"""Base classes for mock data stores."""

import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Dict, Optional


class MockDataStore(ABC):
    """
    Abstract base class for mock data stores.

    All mock implementations should inherit from this class and implement
    the required methods.
    """

    def __init__(self, database: str = ":memory:", **config):
        """
        Initialize the mock data store.

        Args:
            database: SQLite database path (default: in-memory)
            **config: Additional configuration options
        """
        self.database = database
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
