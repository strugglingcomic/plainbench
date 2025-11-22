"""SQLite database interface for PlainBench."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import (
    Benchmark,
    BenchmarkComparison,
    BenchmarkRun,
    BenchmarkStatistics,
    Environment,
    Measurement,
)
from .schema import CREATE_INDEXES, CREATE_TABLES, SCHEMA_VERSION


class BenchmarkDatabase:
    """SQLite database for storing benchmark results."""

    def __init__(self, db_path: str = ":memory:"):
        """
        Initialize database connection.

        Args:
            db_path: Path to database file or ':memory:' for in-memory database
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def initialize(self) -> None:
        """Initialize database connection and create schema."""
        # Create parent directory if needed
        if self.db_path != ":memory:":
            db_file = Path(self.db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")

        # Set WAL mode for concurrent access
        if self.db_path != ":memory:":
            self.conn.execute("PRAGMA journal_mode = WAL")

        # Set cache size (64MB)
        self.conn.execute("PRAGMA cache_size = -64000")

        # Set synchronous mode
        self.conn.execute("PRAGMA synchronous = NORMAL")

        # Create schema
        self.conn.executescript(CREATE_TABLES)
        self.conn.executescript(CREATE_INDEXES)

        # Record schema version
        self.conn.execute(
            "INSERT OR IGNORE INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
        )
        self.conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry."""
        if not self.conn:
            self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    # ============================================================================
    # Environment Operations
    # ============================================================================

    def insert_environment(self, env: Environment) -> int:
        """Insert environment record and return ID."""
        cursor = self.conn.execute(
            """
            INSERT INTO environments
            (python_version, platform, processor, cpu_count, memory_total, hostname, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                env.python_version,
                env.platform,
                env.processor,
                env.cpu_count,
                env.memory_total,
                env.hostname,
                json.dumps(env.metadata) if env.metadata else None,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_environment(self, environment_id: int) -> Optional[Environment]:
        """Get environment by ID."""
        row = self.conn.execute(
            "SELECT * FROM environments WHERE environment_id = ?", (environment_id,)
        ).fetchone()

        if row:
            return Environment(
                environment_id=row["environment_id"],
                python_version=row["python_version"],
                platform=row["platform"],
                processor=row["processor"],
                cpu_count=row["cpu_count"],
                memory_total=row["memory_total"],
                hostname=row["hostname"],
                created_at=datetime.fromisoformat(row["created_at"]),
                metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            )
        return None

    # ============================================================================
    # Benchmark Run Operations
    # ============================================================================

    def insert_run(self, run: BenchmarkRun) -> int:
        """Insert benchmark run and return ID."""
        cursor = self.conn.execute(
            """
            INSERT INTO benchmark_runs
            (timestamp, git_commit_hash, git_branch, git_is_dirty, environment_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run.timestamp,
                run.git_commit_hash,
                run.git_branch,
                run.git_is_dirty,
                run.environment_id,
            ),
        )
        run_id = cursor.lastrowid

        # Insert configurations
        for key, value in run.configurations.items():
            self.conn.execute(
                "INSERT INTO configurations (run_id, key, value) VALUES (?, ?, ?)",
                (run_id, key, value),
            )

        self.conn.commit()
        return run_id

    def get_run(self, run_id: int) -> Optional[BenchmarkRun]:
        """Get benchmark run by ID."""
        row = self.conn.execute(
            "SELECT * FROM benchmark_runs WHERE run_id = ?", (run_id,)
        ).fetchone()

        if row:
            # Get configurations
            configs = {}
            for config_row in self.conn.execute(
                "SELECT key, value FROM configurations WHERE run_id = ?", (run_id,)
            ):
                configs[config_row["key"]] = config_row["value"]

            return BenchmarkRun(
                run_id=row["run_id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                git_commit_hash=row["git_commit_hash"],
                git_branch=row["git_branch"],
                git_is_dirty=bool(row["git_is_dirty"]),
                environment_id=row["environment_id"],
                configurations=configs,
            )
        return None

    def get_latest_run(self) -> Optional[BenchmarkRun]:
        """Get most recent benchmark run."""
        row = self.conn.execute(
            "SELECT run_id FROM benchmark_runs ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()

        if row:
            return self.get_run(row["run_id"])
        return None

    def get_all_runs(self) -> List[BenchmarkRun]:
        """Get all benchmark runs."""
        rows = self.conn.execute(
            "SELECT run_id FROM benchmark_runs ORDER BY timestamp DESC"
        ).fetchall()

        return [self.get_run(row["run_id"]) for row in rows]

    # ============================================================================
    # Benchmark Operations
    # ============================================================================

    def insert_benchmark(self, benchmark: Benchmark) -> int:
        """Insert benchmark definition and return ID."""
        cursor = self.conn.execute(
            """
            INSERT INTO benchmarks (name, description, benchmark_type, category)
            VALUES (?, ?, ?, ?)
            """,
            (
                benchmark.name,
                benchmark.description,
                benchmark.benchmark_type,
                benchmark.category,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_benchmark_by_name(self, name: str) -> Optional[Benchmark]:
        """Get benchmark by name."""
        row = self.conn.execute(
            "SELECT * FROM benchmarks WHERE name = ?", (name,)
        ).fetchone()

        if row:
            return Benchmark(
                benchmark_id=row["benchmark_id"],
                name=row["name"],
                description=row["description"],
                benchmark_type=row["benchmark_type"],
                category=row["category"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
        return None

    def get_or_create_benchmark(self, name: str, benchmark_type: str) -> int:
        """Get existing benchmark ID or create new one."""
        benchmark = self.get_benchmark_by_name(name)
        if benchmark:
            return benchmark.benchmark_id

        new_benchmark = Benchmark(
            benchmark_id=None,
            name=name,
            description=None,
            benchmark_type=benchmark_type,
            category=None,
            created_at=datetime.now(),
        )
        return self.insert_benchmark(new_benchmark)

    # ============================================================================
    # Measurement Operations
    # ============================================================================

    def insert_measurement(self, measurement: Measurement) -> int:
        """Insert single measurement and return ID."""
        cursor = self.conn.execute(
            """
            INSERT INTO measurements
            (run_id, benchmark_id, iteration, wall_time, cpu_time,
             peak_memory, current_memory, read_bytes, write_bytes,
             exit_code, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                measurement.run_id,
                measurement.benchmark_id,
                measurement.iteration,
                measurement.wall_time,
                measurement.cpu_time,
                measurement.peak_memory,
                measurement.current_memory,
                measurement.read_bytes,
                measurement.write_bytes,
                measurement.exit_code,
                json.dumps(measurement.metadata) if measurement.metadata else None,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def insert_measurements(self, measurements: List[Measurement]) -> None:
        """Insert multiple measurements in a transaction."""
        self.conn.execute("BEGIN TRANSACTION")
        try:
            for measurement in measurements:
                self.insert_measurement(measurement)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def get_measurements(
        self, run_id: Optional[int] = None, benchmark_id: Optional[int] = None
    ) -> List[Measurement]:
        """Get measurements filtered by run_id and/or benchmark_id."""
        query = "SELECT * FROM measurements WHERE 1=1"
        params = []

        if run_id is not None:
            query += " AND run_id = ?"
            params.append(run_id)

        if benchmark_id is not None:
            query += " AND benchmark_id = ?"
            params.append(benchmark_id)

        query += " ORDER BY iteration"

        rows = self.conn.execute(query, params).fetchall()

        measurements = []
        for row in rows:
            measurements.append(
                Measurement(
                    measurement_id=row["measurement_id"],
                    run_id=row["run_id"],
                    benchmark_id=row["benchmark_id"],
                    iteration=row["iteration"],
                    wall_time=row["wall_time"],
                    cpu_time=row["cpu_time"],
                    peak_memory=row["peak_memory"],
                    current_memory=row["current_memory"],
                    read_bytes=row["read_bytes"],
                    write_bytes=row["write_bytes"],
                    exit_code=row["exit_code"],
                    metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
                )
            )

        return measurements

    # ============================================================================
    # Statistics Operations
    # ============================================================================

    def insert_statistics(self, stats: BenchmarkStatistics) -> int:
        """Insert benchmark statistics and return ID."""
        cursor = self.conn.execute(
            """
            INSERT INTO benchmark_statistics
            (run_id, benchmark_id, sample_count, mean_wall_time, median_wall_time,
             stddev_wall_time, min_wall_time, max_wall_time, p95_wall_time, p99_wall_time,
             mean_cpu_time, mean_memory, peak_memory, total_read_bytes, total_write_bytes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stats.run_id,
                stats.benchmark_id,
                stats.sample_count,
                stats.mean_wall_time,
                stats.median_wall_time,
                stats.stddev_wall_time,
                stats.min_wall_time,
                stats.max_wall_time,
                stats.p95_wall_time,
                stats.p99_wall_time,
                stats.mean_cpu_time,
                stats.mean_memory,
                stats.peak_memory,
                stats.total_read_bytes,
                stats.total_write_bytes,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    # ============================================================================
    # Helper Methods
    # ============================================================================

    def store_benchmark_results(
        self, benchmark_name: str, measurements: List[Dict], metadata: Dict
    ) -> int:
        """
        Store complete benchmark results (run, benchmark, measurements).

        Args:
            benchmark_name: Name of the benchmark
            measurements: List of measurement dictionaries
            metadata: Run metadata

        Returns:
            run_id: ID of created benchmark run
        """
        # Get or create environment
        # For now, create a simple environment record
        # In real usage, this would detect system info
        import platform
        import sys

        env = Environment(
            environment_id=None,
            python_version=sys.version,
            platform=platform.platform(),
            processor=platform.processor(),
            cpu_count=platform.os.cpu_count() or 0,
            memory_total=0,  # Would use psutil in real implementation
            hostname=platform.node(),
            created_at=datetime.now(),
        )
        env_id = self.insert_environment(env)

        # Create benchmark run
        run = BenchmarkRun(
            run_id=None,
            timestamp=datetime.now(),
            git_commit_hash=None,
            git_branch=None,
            git_is_dirty=False,
            environment_id=env_id,
            configurations=metadata,
        )
        run_id = self.insert_run(run)

        # Get or create benchmark
        benchmark_id = self.get_or_create_benchmark(benchmark_name, "function")

        # Store measurements
        for i, metric_results in enumerate(measurements):
            measurement = Measurement(
                measurement_id=None,
                run_id=run_id,
                benchmark_id=benchmark_id,
                iteration=i,
                wall_time=metric_results.get("wall_time", {}).value
                if "wall_time" in metric_results
                else None,
                cpu_time=metric_results.get("cpu_time", {}).value
                if "cpu_time" in metric_results
                else None,
                peak_memory=metric_results.get("python_memory", {}).value
                if "python_memory" in metric_results
                else None,
                current_memory=None,
                read_bytes=None,
                write_bytes=None,
                exit_code=None,
                metadata={},
            )
            self.insert_measurement(measurement)

        return run_id
