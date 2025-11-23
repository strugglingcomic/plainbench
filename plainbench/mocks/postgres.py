"""Mock Postgres implementation using SQLite."""

import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from plainbench.mocks.base import MockDataStore


class MockPostgresConnection(MockDataStore):
    """
    Mock Postgres connection that uses SQLite as the backend.

    This class provides a DB-API 2.0 compatible interface that mimics
    psycopg2 connections, allowing you to benchmark your application
    logic without the overhead of a real Postgres database.

    Example:
        conn = MockPostgresConnection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO users VALUES (?, ?)", (1, "Alice"))
        conn.commit()
    """

    def __init__(
        self,
        database: str = ":memory:",
        autocommit: bool = False,
        **kwargs,
    ):
        """
        Initialize mock Postgres connection.

        Args:
            database: SQLite database path (default: in-memory)
            autocommit: Enable autocommit mode
            **kwargs: Additional connection parameters (for API compatibility)
        """
        super().__init__(database, **kwargs)
        self.autocommit = autocommit
        self._in_transaction = False
        self._closed = False

    def _init_schema(self) -> None:
        """Initialize the database schema (no-op for Postgres mock)."""
        # Schema is created by user queries
        pass

    def cursor(self) -> "MockPostgresCursor":
        """
        Create a new cursor.

        Returns:
            MockPostgresCursor instance
        """
        if self._closed:
            raise ValueError("Connection is closed")
        return MockPostgresCursor(self)

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._closed:
            raise ValueError("Connection is closed")
        if not self.autocommit and self._in_transaction:
            conn = self.connect()
            conn.execute("COMMIT")
            self._in_transaction = False

    def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._closed:
            raise ValueError("Connection is closed")
        if not self.autocommit and self._in_transaction:
            conn = self.connect()
            conn.execute("ROLLBACK")
            self._in_transaction = False

    def close(self) -> None:
        """Close the connection."""
        if not self._closed:
            super().close()
            self._closed = True

    @property
    def closed(self) -> bool:
        """Check if connection is closed."""
        return self._closed

    def __del__(self):
        """Cleanup on deletion."""
        if not self._closed:
            self.close()


class MockPostgresCursor:
    """
    Mock Postgres cursor that uses SQLite.

    Provides DB-API 2.0 compatible cursor interface with SQL translation
    from Postgres dialect to SQLite dialect.
    """

    def __init__(self, connection: MockPostgresConnection):
        """
        Initialize cursor.

        Args:
            connection: Parent MockPostgresConnection
        """
        self.connection = connection
        self._sqlite_conn = connection.connect()
        self._sqlite_cursor = self._sqlite_conn.cursor()
        self._description: Optional[Tuple] = None
        self._rowcount: int = -1
        self._arraysize: int = 1
        self._closed = False

    def _translate_sql(self, sql: str) -> str:
        """
        Translate Postgres SQL to SQLite SQL.

        Args:
            sql: Postgres SQL statement

        Returns:
            SQLite-compatible SQL statement
        """
        # Handle RETURNING clauses (SQLite supports it from 3.35+)
        # We'll assume modern SQLite

        # Convert %s placeholders to ?
        translated = sql.replace("%s", "?")

        # Convert NOW() to CURRENT_TIMESTAMP
        translated = re.sub(
            r"\bNOW\(\)", "CURRENT_TIMESTAMP", translated, flags=re.IGNORECASE
        )

        # Convert SERIAL to INTEGER PRIMARY KEY AUTOINCREMENT
        translated = re.sub(
            r"\bSERIAL\b",
            "INTEGER PRIMARY KEY AUTOINCREMENT",
            translated,
            flags=re.IGNORECASE,
        )

        # Convert BOOLEAN to INTEGER (SQLite doesn't have native boolean)
        translated = re.sub(r"\bBOOLEAN\b", "INTEGER", translated, flags=re.IGNORECASE)

        # Convert TRUE/FALSE to 1/0
        translated = re.sub(r"\bTRUE\b", "1", translated, flags=re.IGNORECASE)
        translated = re.sub(r"\bFALSE\b", "0", translated, flags=re.IGNORECASE)

        # Convert TEXT[] to TEXT (SQLite doesn't have array types)
        translated = re.sub(r"\bTEXT\[\]", "TEXT", translated, flags=re.IGNORECASE)
        translated = re.sub(
            r"\bINTEGER\[\]", "TEXT", translated, flags=re.IGNORECASE
        )

        # Convert TIMESTAMP to DATETIME
        translated = re.sub(
            r"\bTIMESTAMP\b", "DATETIME", translated, flags=re.IGNORECASE
        )

        # Convert VARCHAR to TEXT
        translated = re.sub(
            r"\bVARCHAR\(\d+\)", "TEXT", translated, flags=re.IGNORECASE
        )

        return translated

    def _translate_params(
        self, params: Optional[Union[Tuple, List, Dict]]
    ) -> Optional[Union[Tuple, List]]:
        """
        Translate parameter format.

        Args:
            params: Parameters in Postgres format

        Returns:
            Parameters in SQLite format
        """
        if params is None:
            return None

        # Handle dictionary parameters (named parameters)
        if isinstance(params, dict):
            # SQLite uses :name format for named parameters
            return params

        # Handle list/tuple parameters
        return tuple(params) if isinstance(params, list) else params

    def execute(
        self,
        sql: str,
        params: Optional[Union[Tuple, List, Dict]] = None,
    ) -> "MockPostgresCursor":
        """
        Execute a SQL statement.

        Args:
            sql: SQL statement (Postgres dialect)
            params: Parameters for the SQL statement

        Returns:
            self (for chaining)
        """
        if self._closed:
            raise ValueError("Cursor is closed")

        # Start transaction if needed
        if not self.connection.autocommit and not self.connection._in_transaction:
            self._sqlite_conn.execute("BEGIN")
            self.connection._in_transaction = True

        # Translate SQL
        translated_sql = self._translate_sql(sql)
        translated_params = self._translate_params(params)

        # Execute
        if translated_params:
            self._sqlite_cursor.execute(translated_sql, translated_params)
        else:
            self._sqlite_cursor.execute(translated_sql)

        # Update cursor state
        self._description = self._sqlite_cursor.description
        self._rowcount = self._sqlite_cursor.rowcount

        return self

    def executemany(
        self,
        sql: str,
        params_list: List[Union[Tuple, List, Dict]],
    ) -> "MockPostgresCursor":
        """
        Execute a SQL statement with multiple parameter sets.

        Args:
            sql: SQL statement
            params_list: List of parameter sets

        Returns:
            self (for chaining)
        """
        if self._closed:
            raise ValueError("Cursor is closed")

        # Start transaction if needed
        if not self.connection.autocommit and not self.connection._in_transaction:
            self._sqlite_conn.execute("BEGIN")
            self.connection._in_transaction = True

        # Translate SQL
        translated_sql = self._translate_sql(sql)

        # Translate all parameter sets
        translated_params_list = [
            self._translate_params(params) for params in params_list
        ]

        # Execute
        self._sqlite_cursor.executemany(translated_sql, translated_params_list)

        # Update cursor state
        self._description = self._sqlite_cursor.description
        self._rowcount = self._sqlite_cursor.rowcount

        return self

    def fetchone(self) -> Optional[Tuple]:
        """
        Fetch the next row.

        Returns:
            Next row as tuple, or None if no more rows
        """
        if self._closed:
            raise ValueError("Cursor is closed")
        return self._sqlite_cursor.fetchone()

    def fetchmany(self, size: Optional[int] = None) -> List[Tuple]:
        """
        Fetch the next set of rows.

        Args:
            size: Number of rows to fetch (default: arraysize)

        Returns:
            List of rows
        """
        if self._closed:
            raise ValueError("Cursor is closed")
        if size is None:
            size = self._arraysize
        return self._sqlite_cursor.fetchmany(size)

    def fetchall(self) -> List[Tuple]:
        """
        Fetch all remaining rows.

        Returns:
            List of all remaining rows
        """
        if self._closed:
            raise ValueError("Cursor is closed")
        return self._sqlite_cursor.fetchall()

    def close(self) -> None:
        """Close the cursor."""
        if not self._closed:
            self._sqlite_cursor.close()
            self._closed = True

    @property
    def description(self) -> Optional[Tuple]:
        """Get cursor description (column information)."""
        return self._description

    @property
    def rowcount(self) -> int:
        """Get number of rows affected by last operation."""
        return self._rowcount

    @property
    def arraysize(self) -> int:
        """Get default fetch size."""
        return self._arraysize

    @arraysize.setter
    def arraysize(self, value: int) -> None:
        """Set default fetch size."""
        self._arraysize = value

    def __iter__(self):
        """Make cursor iterable."""
        return self

    def __next__(self):
        """Get next row when iterating."""
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
