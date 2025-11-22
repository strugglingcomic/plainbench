"""
Pytest configuration and shared fixtures.

This module provides:
- Database fixtures (temp, in-memory, populated)
- Mock data fixtures
- Configuration fixtures
- Test isolation fixtures
- Helper utilities
"""

import pytest
import tempfile
import os
from pathlib import Path


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def temp_database(tmp_path):
    """
    Provide a temporary SQLite database for testing.

    The database is created in a temporary directory and automatically
    cleaned up after the test completes.

    Yields:
        str: Path to temporary database file

    Example:
        def test_something(temp_database):
            db = BenchmarkDatabase(temp_database)
            # ... test code ...
    """
    from plainbench.storage.database import BenchmarkDatabase

    db_path = tmp_path / "test_benchmark.db"
    db = BenchmarkDatabase(str(db_path))
    db.initialize()
    yield str(db_path)
    db.close()


@pytest.fixture
def memory_database():
    """
    Provide an in-memory SQLite database for testing.

    Faster than file-based database, ideal for unit tests.

    Yields:
        BenchmarkDatabase: In-memory database instance

    Example:
        def test_something(memory_database):
            memory_database.insert_benchmark(...)
    """
    from plainbench.storage.database import BenchmarkDatabase

    db = BenchmarkDatabase(":memory:")
    db.initialize()
    yield db
    db.close()


@pytest.fixture
def populated_database(temp_database):
    """
    Provide a database pre-populated with sample data.

    Includes:
    - Multiple benchmark runs
    - Various benchmarks (function and shell types)
    - Measurements with different metrics
    - Pre-computed statistics
    - Comparisons

    Yields:
        str: Path to populated database

    Example:
        def test_query(populated_database):
            db = BenchmarkDatabase(populated_database)
            runs = db.get_all_runs()
            assert len(runs) > 0
    """
    # TODO: Implement
    # from plainbench.storage.database import BenchmarkDatabase
    # from tests.fixtures.mock_data import create_sample_runs
    #
    # db = BenchmarkDatabase(temp_database)
    # create_sample_runs(db)
    # yield temp_database
    pass


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@pytest.fixture
def sample_measurements():
    """
    Provide sample measurement data.

    Returns:
        list[Measurement]: List of sample measurements

    Example:
        def test_statistics(sample_measurements):
            stats = compute_statistics(sample_measurements)
            assert stats.mean_wall_time > 0
    """
    # TODO: Implement
    # from plainbench.storage.models import Measurement
    # return [
    #     Measurement(
    #         measurement_id=None,
    #         run_id=1,
    #         benchmark_id=1,
    #         iteration=i,
    #         wall_time=1.0 + i * 0.1,
    #         cpu_time=0.9 + i * 0.1,
    #         peak_memory=1024 * 1024 * (10 + i),
    #         current_memory=1024 * 1024 * (8 + i),
    #         read_bytes=1000 * i,
    #         write_bytes=500 * i,
    #         exit_code=0,
    #     )
    #     for i in range(10)
    # ]
    pass


@pytest.fixture
def sample_benchmark_run():
    """
    Provide a sample BenchmarkRun object.

    Returns:
        BenchmarkRun: Sample run metadata

    Example:
        def test_run_storage(sample_benchmark_run, temp_database):
            db = BenchmarkDatabase(temp_database)
            db.insert_run(sample_benchmark_run)
    """
    # TODO: Implement
    # from plainbench.storage.models import BenchmarkRun
    # from datetime import datetime
    #
    # return BenchmarkRun(
    #     run_id=None,
    #     timestamp=datetime.now(),
    #     git_commit_hash='abc123',
    #     git_branch='main',
    #     git_is_dirty=False,
    #     environment_id=1,
    # )
    pass


@pytest.fixture
def sample_environment():
    """
    Provide a sample Environment object.

    Returns:
        Environment: Sample environment metadata

    Example:
        def test_env_storage(sample_environment, temp_database):
            db = BenchmarkDatabase(temp_database)
            env_id = db.insert_environment(sample_environment)
    """
    # TODO: Implement
    # from plainbench.storage.models import Environment
    # from datetime import datetime
    # import platform
    # import sys
    #
    # return Environment(
    #     environment_id=None,
    #     python_version=sys.version,
    #     platform=platform.platform(),
    #     processor=platform.processor(),
    #     cpu_count=os.cpu_count(),
    #     memory_total=1024 * 1024 * 1024 * 16,  # 16GB
    #     hostname=platform.node(),
    #     created_at=datetime.now(),
    # )
    pass


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def minimal_config():
    """
    Provide minimal benchmark configuration.

    Returns:
        BenchmarkConfig: Minimal configuration with defaults

    Example:
        def test_with_config(minimal_config):
            assert minimal_config.default_warmup == 1
    """
    # TODO: Implement
    # from plainbench.config.settings import BenchmarkConfig
    #
    # return BenchmarkConfig(
    #     default_warmup=1,
    #     default_runs=3,
    #     default_isolation='minimal',
    # )
    pass


@pytest.fixture
def full_config():
    """
    Provide full benchmark configuration with all options.

    Returns:
        BenchmarkConfig: Complete configuration

    Example:
        def test_with_full_config(full_config):
            assert full_config.cpu_affinity is not None
    """
    # TODO: Implement
    # from plainbench.config.settings import BenchmarkConfig
    #
    # return BenchmarkConfig(
    #     default_warmup=3,
    #     default_runs=10,
    #     default_isolation='moderate',
    #     default_metrics=['wall_time', 'cpu_time', 'python_memory'],
    #     database_path='./benchmarks.db',
    #     cpu_affinity=[0, 1, 2, 3],
    #     disable_gc=True,
    #     regression_threshold=0.05,
    # )
    pass


# ============================================================================
# File and Directory Fixtures
# ============================================================================

@pytest.fixture
def sample_benchmark_file(tmp_path):
    """
    Create a sample benchmark Python file.

    Args:
        tmp_path: pytest's tmp_path fixture

    Returns:
        Path: Path to created benchmark file

    Example:
        def test_discovery(sample_benchmark_file):
            benchmarks = discover_benchmarks(sample_benchmark_file.parent)
            assert len(benchmarks) > 0
    """
    # TODO: Implement
    # benchmark_file = tmp_path / 'test_bench.py'
    # benchmark_file.write_text('''
    # from plainbench import benchmark
    #
    # @benchmark()
    # def sample_function():
    #     return sum(range(100))
    # ''')
    # return benchmark_file
    pass


@pytest.fixture
def sample_config_file(tmp_path):
    """
    Create a sample configuration YAML file.

    Args:
        tmp_path: pytest's tmp_path fixture

    Returns:
        Path: Path to created config file

    Example:
        def test_config_loading(sample_config_file):
            config = load_config(sample_config_file)
            assert config.default_warmup == 5
    """
    # TODO: Implement
    # config_file = tmp_path / 'plainbench.yaml'
    # config_file.write_text('''
    # default_warmup: 5
    # default_runs: 20
    # default_isolation: moderate
    # ''')
    # return config_file
    pass


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_metric_collector():
    """
    Provide a mock MetricCollector for testing.

    Returns:
        Mock: Mock MetricCollector with standard behavior

    Example:
        def test_decorator(mock_metric_collector):
            # Use mock instead of real collector
            pass
    """
    # TODO: Implement
    # from unittest.mock import Mock
    # from plainbench.metrics.base import MetricResult
    #
    # mock = Mock()
    # mock.name = 'mock_metric'
    # mock.is_available.return_value = True
    # mock.setup.return_value = None
    # mock.start.return_value = None
    # mock.stop.return_value = MetricResult(
    #     name='mock_metric',
    #     value=1.0,
    #     unit='seconds'
    # )
    # mock.cleanup.return_value = None
    # return mock
    pass


@pytest.fixture
def mock_process():
    """
    Provide a mock psutil.Process for testing.

    Returns:
        Mock: Mock Process with standard methods

    Example:
        def test_process_monitoring(mock_process):
            mem = mock_process.memory_info()
            assert mem.rss > 0
    """
    # TODO: Implement
    # from unittest.mock import Mock
    #
    # mock = Mock()
    # mock.pid = 12345
    # mock.memory_info.return_value = Mock(rss=1024*1024*100, vms=1024*1024*200)
    # mock.cpu_percent.return_value = 25.0
    # mock.cpu_times.return_value = Mock(user=1.0, system=0.5)
    # mock.io_counters.return_value = Mock(
    #     read_bytes=1000,
    #     write_bytes=500,
    #     read_count=10,
    #     write_count=5
    # )
    # return mock
    pass


# ============================================================================
# Isolation Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def isolate_tests():
    """
    Isolate tests from each other (autouse).

    - Resets global state
    - Cleans up resources
    - Ensures test independence

    This fixture runs automatically for all tests.
    """
    # TODO: Implement
    # Setup: Save current state
    # Yield: Run test
    # Teardown: Restore state
    pass


@pytest.fixture
def no_database():
    """
    Prevent database creation during test.

    Useful for testing error handling when database is unavailable.

    Example:
        def test_no_db_error(no_database):
            with pytest.raises(DatabaseUnavailable):
                db = BenchmarkDatabase('/nonexistent/db.sqlite')
    """
    # TODO: Implement
    pass


# ============================================================================
# Parametrization Helpers
# ============================================================================

# Common parameter combinations
WARMUP_RUNS_COMBINATIONS = [
    (0, 1),
    (1, 5),
    (3, 10),
    (5, 20),
]

ISOLATION_LEVELS = [
    'minimal',
    'moderate',
    'maximum',
]

METRIC_COMBINATIONS = [
    ['wall_time'],
    ['wall_time', 'cpu_time'],
    ['wall_time', 'cpu_time', 'python_memory'],
    ['wall_time', 'cpu_time', 'python_memory', 'disk_io'],
]


# ============================================================================
# Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "linux_only: marks tests that only run on Linux"
    )
    config.addinivalue_line(
        "markers", "macos_only: marks tests that only run on macOS"
    )
    config.addinivalue_line(
        "markers", "windows_only: marks tests that only run on Windows"
    )
    config.addinivalue_line(
        "markers", "integration: marks integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks end-to-end tests"
    )


# ============================================================================
# Helper Functions
# ============================================================================

def create_sample_function():
    """
    Create a sample function for benchmarking.

    Returns:
        callable: Function that can be benchmarked
    """
    def sample_func(n=100):
        """Sample function that computes sum."""
        return sum(range(n))
    return sample_func


def create_sample_shell_command():
    """
    Create a sample shell command for benchmarking.

    Returns:
        str: Shell command string
    """
    import sys
    if sys.platform == 'win32':
        return 'echo test'
    else:
        return 'echo test'
