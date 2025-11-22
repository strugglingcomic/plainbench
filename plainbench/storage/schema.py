"""SQLite database schema for PlainBench."""

# Schema version for migrations
SCHEMA_VERSION = 1

CREATE_TABLES = """
-- Environments: system metadata
CREATE TABLE IF NOT EXISTS environments (
    environment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    python_version TEXT NOT NULL,
    platform TEXT NOT NULL,
    processor TEXT,
    cpu_count INTEGER,
    memory_total INTEGER,
    hostname TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT
);

-- Benchmark runs: execution metadata
CREATE TABLE IF NOT EXISTS benchmark_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    git_commit_hash TEXT,
    git_branch TEXT,
    git_is_dirty BOOLEAN,
    environment_id INTEGER NOT NULL,
    FOREIGN KEY (environment_id) REFERENCES environments(environment_id)
);

-- Benchmarks: benchmark definitions
CREATE TABLE IF NOT EXISTS benchmarks (
    benchmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    benchmark_type TEXT NOT NULL,
    category TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Measurements: raw measurement data
CREATE TABLE IF NOT EXISTS measurements (
    measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    benchmark_id INTEGER NOT NULL,
    iteration INTEGER NOT NULL,
    wall_time REAL,
    cpu_time REAL,
    peak_memory INTEGER,
    current_memory INTEGER,
    read_bytes INTEGER,
    write_bytes INTEGER,
    exit_code INTEGER,
    metadata_json TEXT,
    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(benchmark_id)
);

-- Benchmark statistics: pre-computed aggregates
CREATE TABLE IF NOT EXISTS benchmark_statistics (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    benchmark_id INTEGER NOT NULL,
    sample_count INTEGER NOT NULL,
    mean_wall_time REAL,
    median_wall_time REAL,
    stddev_wall_time REAL,
    min_wall_time REAL,
    max_wall_time REAL,
    p95_wall_time REAL,
    p99_wall_time REAL,
    mean_cpu_time REAL,
    mean_memory INTEGER,
    peak_memory INTEGER,
    total_read_bytes INTEGER,
    total_write_bytes INTEGER,
    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(benchmark_id),
    UNIQUE(run_id, benchmark_id)
);

-- Configurations: benchmark configuration
CREATE TABLE IF NOT EXISTS configurations (
    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id)
);

-- Benchmark comparisons: stored comparisons
CREATE TABLE IF NOT EXISTS benchmark_comparisons (
    comparison_id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseline_run_id INTEGER NOT NULL,
    comparison_run_id INTEGER NOT NULL,
    benchmark_id INTEGER NOT NULL,
    speedup_factor REAL,
    memory_ratio REAL,
    is_significant BOOLEAN,
    p_value REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (baseline_run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (comparison_run_id) REFERENCES benchmark_runs(run_id),
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(benchmark_id)
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES = """
-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_measurements_run
    ON measurements(run_id);

CREATE INDEX IF NOT EXISTS idx_measurements_benchmark
    ON measurements(benchmark_id);

CREATE INDEX IF NOT EXISTS idx_measurements_run_benchmark
    ON measurements(run_id, benchmark_id);

CREATE INDEX IF NOT EXISTS idx_benchmark_runs_timestamp
    ON benchmark_runs(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_benchmark_runs_git_branch
    ON benchmark_runs(git_branch);

CREATE INDEX IF NOT EXISTS idx_configurations_run
    ON configurations(run_id);

CREATE INDEX IF NOT EXISTS idx_comparisons_runs
    ON benchmark_comparisons(baseline_run_id, comparison_run_id);
"""
