# PlainBench Test Strategy

**Version:** 1.0
**Date:** 2025-11-22
**Status:** Design Phase

---

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Organization](#test-organization)
3. [Unit Testing Strategy](#unit-testing-strategy)
4. [Integration Testing Strategy](#integration-testing-strategy)
5. [Test Fixtures and Utilities](#test-fixtures-and-utilities)
6. [Mocking Strategy](#mocking-strategy)
7. [Coverage Goals](#coverage-goals)
8. [CI/CD Considerations](#cicd-considerations)
9. [Platform-Specific Testing](#platform-specific-testing)
10. [Performance Testing](#performance-testing)

---

## Testing Philosophy

### Core Principles

1. **Fast Feedback**: Unit tests should run in milliseconds; full suite in seconds
2. **Reliability**: Tests should be deterministic and not flaky
3. **Isolation**: Each test should be independent and not affect others
4. **Clarity**: Test names and assertions should clearly communicate intent
5. **Maintainability**: Tests should be easy to update as the system evolves

### Test Pyramid

```
                    /\
                   /  \
                  / E2E\      ~5% - End-to-end integration tests
                 /______\
                /        \
               /Integration\   ~15% - Multi-component integration
              /____________\
             /              \
            /   Unit Tests   \  ~80% - Fast, isolated unit tests
           /_________________ \
```

**Distribution Goal:**
- **80% Unit Tests**: Fast, isolated, comprehensive coverage
- **15% Integration Tests**: Verify components work together
- **5% E2E Tests**: Full workflow validation

---

## Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared pytest fixtures
│
├── unit/                       # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_metrics.py         # Metrics collectors
│   ├── test_decorators.py      # Decorator functionality
│   ├── test_shell.py           # Shell command runner
│   ├── test_isolation.py       # Isolation strategies
│   ├── test_storage.py         # Database operations
│   ├── test_analysis.py        # Statistical analysis
│   ├── test_config.py          # Configuration management
│   └── test_cli.py             # CLI commands
│
├── integration/                # Integration tests
│   ├── __init__.py
│   ├── test_decorator_e2e.py   # Decorator end-to-end
│   ├── test_shell_e2e.py       # Shell command end-to-end
│   ├── test_cli_integration.py # CLI workflows
│   └── test_migrations.py      # Database migrations
│
├── benchmarks/                 # Example benchmarks (also serve as tests)
│   ├── __init__.py
│   ├── test_python_functions.py
│   └── test_shell_commands.py
│
└── fixtures/                   # Test data and utilities
    ├── __init__.py
    ├── README.md
    ├── sample_functions.py     # Sample benchmark functions
    ├── sample_configs.py       # Sample configurations
    ├── mock_data.py            # Mock metric data
    └── test_scripts/           # Shell scripts for testing
        ├── fast_script.sh
        ├── slow_script.sh
        └── io_intensive.sh
```

### Naming Conventions

**Test Files:**
- Prefix with `test_`: `test_metrics.py`
- Mirror source structure: `plainbench/metrics/timing.py` → `tests/unit/test_metrics.py`

**Test Functions:**
- Prefix with `test_`: `test_wall_time_collector_accuracy()`
- Use descriptive names: `test_benchmark_decorator_preserves_function_metadata()`
- Pattern: `test_<component>_<behavior>_<condition>()`

**Test Classes:**
- Prefix with `Test`: `TestWallTimeCollector`
- Group related tests: All timing tests in `TestTimingCollectors`

**Fixtures:**
- Use lowercase with underscores: `temp_database`, `mock_process`
- Descriptive names indicating what they provide

---

## Unit Testing Strategy

### What to Test

**Core Functionality:**
1. **Happy path**: Normal, expected usage
2. **Edge cases**: Boundary conditions, empty inputs, zeros
3. **Error conditions**: Invalid inputs, missing dependencies
4. **State transitions**: Setup → start → stop → cleanup
5. **Return values**: Correct types, correct values, correct units

**NOT Tested in Unit Tests:**
- Actual timing accuracy (too slow, environment-dependent)
- Real subprocess execution (use mocks)
- Actual database writes (use in-memory DB)
- Real file I/O (use tempfiles or mocks)

### What to Mock

**External Dependencies:**
1. **System calls**: `time.perf_counter()`, `time.process_time()`
2. **Process monitoring**: `psutil.Process`, `psutil.cpu_percent()`
3. **Memory tracking**: `tracemalloc` functions
4. **Subprocess**: `subprocess.Popen`, `subprocess.run()`
5. **File system**: File reads/writes for config
6. **Git operations**: Git command execution

**Why Mock:**
- **Speed**: Mocked tests run in microseconds vs. real operations
- **Determinism**: Controlled return values eliminate flakiness
- **Isolation**: Tests don't depend on system state
- **Edge cases**: Can simulate rare error conditions

### Mock Libraries

**Primary:** `unittest.mock` (standard library)
- `Mock`: Generic mock object
- `MagicMock`: Mock with magic methods
- `patch`: Context manager/decorator for patching
- `patch.object`: Patch specific object attributes

**Example:**
```python
from unittest.mock import Mock, patch

@patch('time.perf_counter')
def test_wall_time_collector(mock_perf_counter):
    mock_perf_counter.side_effect = [0.0, 1.5]  # start, end

    collector = WallTimeCollector()
    collector.setup()
    collector.start()
    result = collector.stop()

    assert result.value == 1.5
    assert result.unit == "seconds"
```

### Test Data Strategy

**Deterministic Data:**
- Use fixed values for reproducibility
- Example: Always use `[1, 2, 3, 4, 5]` for statistical tests
- Pre-computed expected results

**Parametrized Tests:**
Use `pytest.mark.parametrize` for multiple inputs:
```python
@pytest.mark.parametrize("values,expected_mean", [
    ([1, 2, 3], 2.0),
    ([10, 20, 30], 20.0),
    ([1.5, 2.5, 3.5], 2.5),
])
def test_mean_calculation(values, expected_mean):
    assert statistics.mean(values) == expected_mean
```

### Assertions

**Use Specific Assertions:**
- `assert value == expected` - Equality
- `assert value is None` - Identity
- `assert 0.99 < value < 1.01` - Ranges for floats
- `pytest.approx(expected, rel=0.01)` - Approximate equality
- `assert isinstance(obj, Type)` - Type checking
- `with pytest.raises(Exception)` - Exception testing

**Example:**
```python
def test_metric_result_structure():
    result = MetricResult(
        name="test_metric",
        value=42.0,
        unit="seconds"
    )

    assert result.name == "test_metric"
    assert result.value == pytest.approx(42.0)
    assert result.unit == "seconds"
    assert result.metadata is None
```

---

## Integration Testing Strategy

### What to Test

**Component Interactions:**
1. **Decorator → Metrics → Storage**: Full benchmark flow
2. **Shell → Metrics → Storage**: Shell command benchmarking
3. **CLI → All Components**: Command-line workflows
4. **Storage → Analysis**: Data persistence and retrieval
5. **Config → Components**: Configuration propagation

### Real vs. Mock Dependencies

**Use Real:**
- SQLite database (in-memory for speed)
- File system (with temporary directories)
- Simple shell commands (`echo`, `true`, `false`)
- Real metric collectors (but brief executions)

**Keep Mocked:**
- Long-running processes
- External services
- Network calls
- Heavy I/O operations

### Integration Test Patterns

**Pattern 1: End-to-End Decorator**
```python
def test_decorator_full_workflow(temp_database):
    """Test complete decorator workflow with real database."""

    @benchmark(warmup=1, runs=3, database=temp_database)
    def sample_function():
        return sum(range(100))

    # Execute
    result = sample_function()

    # Verify execution
    assert result == 4950

    # Verify database storage
    db = BenchmarkDatabase(temp_database)
    runs = db.get_all_runs()
    assert len(runs) == 1

    measurements = db.get_measurements(runs[0].run_id)
    assert len(measurements) == 3  # 3 runs
```

**Pattern 2: CLI Integration**
```python
def test_cli_run_command(temp_dir, temp_database):
    """Test CLI run command with real benchmark files."""
    from click.testing import CliRunner
    from plainbench.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, [
        'run',
        str(temp_dir),
        '--database', temp_database,
        '--runs', '3'
    ])

    assert result.exit_code == 0
    assert 'Benchmark complete' in result.output
```

### Database Testing

**Use In-Memory SQLite:**
```python
@pytest.fixture
def memory_database():
    """Provide in-memory SQLite database for tests."""
    db = BenchmarkDatabase(':memory:')
    db.initialize()
    yield db
    db.close()
```

**Test Schema:**
- Table creation
- Foreign key constraints
- Index creation
- Default values

**Test Operations:**
- INSERT, UPDATE, DELETE
- Query methods
- Transaction handling
- Concurrent access (WAL mode)

### Temporary Files and Directories

**Use pytest tmpdir:**
```python
def test_with_temp_directory(tmp_path):
    """Test using temporary directory."""
    test_file = tmp_path / "benchmark.py"
    test_file.write_text("# test content")

    # Run test
    result = process_file(test_file)

    # Assertions
    assert result is not None
```

---

## Test Fixtures and Utilities

### Shared Fixtures (conftest.py)

**Database Fixtures:**
```python
@pytest.fixture
def temp_database(tmp_path):
    """Temporary SQLite database."""
    db_path = tmp_path / "test.db"
    db = BenchmarkDatabase(str(db_path))
    db.initialize()
    yield str(db_path)
    db.close()

@pytest.fixture
def populated_database(temp_database):
    """Database with sample data."""
    db = BenchmarkDatabase(temp_database)
    # Insert sample runs, benchmarks, measurements
    yield temp_database
```

**Mock Data Fixtures:**
```python
@pytest.fixture
def sample_measurements():
    """Sample measurement data for testing."""
    return [
        Measurement(
            measurement_id=None,
            run_id=1,
            benchmark_id=1,
            iteration=i,
            wall_time=1.0 + i * 0.1,
            cpu_time=0.9 + i * 0.1,
            peak_memory=1024 * 1024 * (10 + i),
            current_memory=1024 * 1024 * (8 + i),
            read_bytes=0,
            write_bytes=0,
            exit_code=0,
        )
        for i in range(10)
    ]
```

**Configuration Fixtures:**
```python
@pytest.fixture
def minimal_config():
    """Minimal benchmark configuration."""
    return BenchmarkConfig(
        default_warmup=1,
        default_runs=3,
        default_isolation='minimal',
    )
```

### Fixture Scopes

**Function Scope (default):** New instance per test
```python
@pytest.fixture
def temp_file(tmp_path):
    # Created fresh for each test
    pass
```

**Session Scope:** Shared across all tests
```python
@pytest.fixture(scope="session")
def expensive_resource():
    # Created once for entire test session
    pass
```

**Module Scope:** Shared across tests in same file
```python
@pytest.fixture(scope="module")
def shared_database():
    # Created once per test module
    pass
```

### Parametrized Fixtures

```python
@pytest.fixture(params=['minimal', 'moderate', 'maximum'])
def isolation_level(request):
    """Test with all isolation levels."""
    return request.param

def test_isolation_strategy(isolation_level):
    # Runs 3 times, once per parameter
    strategy = create_isolation_strategy(isolation_level)
    assert strategy.is_available()
```

---

## Mocking Strategy

### Time Mocking

**Mock perf_counter:**
```python
@patch('time.perf_counter')
def test_timing(mock_time):
    mock_time.side_effect = [0.0, 1.5, 3.2, 5.0]
    # Test timing logic
```

**Mock datetime:**
```python
from freezegun import freeze_time

@freeze_time("2025-11-22 12:00:00")
def test_timestamp():
    # Time is frozen at specified moment
    pass
```

### Process Mocking

**Mock psutil.Process:**
```python
@patch('psutil.Process')
def test_process_monitoring(mock_process_class):
    mock_proc = Mock()
    mock_proc.memory_info.return_value = Mock(rss=1024*1024*100)
    mock_proc.cpu_percent.return_value = 25.0
    mock_process_class.return_value = mock_proc

    # Test code using psutil.Process
```

**Mock subprocess:**
```python
@patch('subprocess.Popen')
def test_shell_command(mock_popen):
    mock_proc = Mock()
    mock_proc.poll.side_effect = [None, None, 0]  # Running, then done
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (b"output", b"")
    mock_popen.return_value = mock_proc

    # Test shell command execution
```

### Memory Mocking

**Mock tracemalloc:**
```python
@patch('tracemalloc.is_tracing', return_value=False)
@patch('tracemalloc.start')
@patch('tracemalloc.get_traced_memory', return_value=(1024*1024, 2048*1024))
@patch('tracemalloc.stop')
def test_tracemalloc_collector(mock_stop, mock_get, mock_start, mock_is_tracing):
    collector = TraceMallocCollector()
    collector.setup()
    collector.start()
    result = collector.stop()
    collector.cleanup()

    assert result.value == 2048*1024  # peak memory
```

### Database Mocking

**Generally DON'T mock database:**
- Use in-memory SQLite instead
- Fast enough for unit tests
- Tests actual SQL logic
- Catches schema errors

**When to mock:**
- Testing error handling (connection failures)
- Testing retry logic
- External database connections (PostgreSQL, etc.)

### File System Mocking

**Use real temp files:**
```python
def test_config_loading(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
    default_warmup: 5
    default_runs: 10
    """)

    config = load_config(config_file)
    assert config.default_warmup == 5
```

**Mock only for error testing:**
```python
@patch('builtins.open', side_effect=PermissionError)
def test_config_permission_error(mock_open):
    with pytest.raises(PermissionError):
        load_config('config.yaml')
```

---

## Coverage Goals

### Target Coverage

**Overall Target:** 90%+

**Per-Module Targets:**
- **Core modules** (metrics, storage): 95%+
- **Decorator system**: 90%+
- **CLI commands**: 85%+
- **Utilities**: 90%+

### Coverage Measurement

**Tool:** `pytest-cov`

```bash
# Run tests with coverage
pytest --cov=plainbench --cov-report=html --cov-report=term

# Coverage report
---------- coverage: platform linux, python 3.11 -----------
Name                              Stmts   Miss  Cover
-----------------------------------------------------
plainbench/__init__.py                5      0   100%
plainbench/metrics/base.py           25      1    96%
plainbench/metrics/timing.py         30      2    93%
...
-----------------------------------------------------
TOTAL                              1500     75    95%
```

### What NOT to Cover

**Exclude from coverage:**
1. **Platform-specific code** that can't run on test platform
2. **Defensive error handling** for rare conditions
3. **CLI formatting** and output (hard to test, low value)
4. **Debug logging** statements

**Mark with `# pragma: no cover`:**
```python
def platform_specific_function():
    if sys.platform == 'darwin':  # pragma: no cover
        # macOS-specific code
        pass
```

### Coverage Gaps

**Acceptable Gaps:**
- Platform-specific branches
- Emergency error handlers
- Deprecated code paths

**Unacceptable Gaps:**
- Core business logic
- Data transformations
- Calculation functions
- Public APIs

---

## CI/CD Considerations

### Test Stages

**Stage 1: Fast Tests (< 10 seconds)**
```yaml
fast-tests:
  script:
    - pytest tests/unit -v --maxfail=1
  timeout: 2m
```

**Stage 2: Full Test Suite (< 1 minute)**
```yaml
full-tests:
  script:
    - pytest tests/ -v --cov=plainbench
  timeout: 5m
```

**Stage 3: Integration Tests (< 2 minutes)**
```yaml
integration-tests:
  script:
    - pytest tests/integration/ -v
  timeout: 5m
```

### Multi-Platform Testing

**Test on multiple platforms:**
```yaml
matrix:
  os: [ubuntu-latest, macos-latest, windows-latest]
  python: ['3.9', '3.10', '3.11', '3.12']
```

**Platform-specific markers:**
```python
@pytest.mark.linux_only
def test_cgroups_isolation():
    # Only runs on Linux
    pass

@pytest.mark.skipif(sys.platform == 'win32', reason="Unix only")
def test_resource_module():
    # Skips on Windows
    pass
```

### Test Artifacts

**Collect artifacts:**
- Coverage reports (HTML)
- Failed test screenshots
- Database files from failed tests
- Log files

```yaml
artifacts:
  when: always
  paths:
    - coverage/
    - test-results/
    - logs/
```

### Performance Regression Detection

**Automated benchmarks in CI:**
```yaml
benchmark-regression:
  script:
    - plainbench run tests/benchmarks/ --isolation=maximum
    - plainbench compare --baseline=main --threshold=0.05
  allow_failure: true  # Warning only, don't fail build
```

---

## Platform-Specific Testing

### Linux-Specific Tests

**Features to test:**
- cgroups isolation
- I/O counters (full support)
- CPU pinning
- Resource module metrics

```python
@pytest.mark.skipif(sys.platform != 'linux', reason="Linux only")
class TestLinuxSpecificFeatures:
    def test_io_counters_available(self):
        collector = IOCollector()
        assert collector.is_available()

    def test_cgroups_isolation(self):
        strategy = MaximumIsolation()
        assert strategy.is_available()
```

### macOS-Specific Tests

**Features to test:**
- Limited I/O counters
- Memory units (bytes vs KB)
- CPU pinning support

```python
@pytest.mark.skipif(sys.platform != 'darwin', reason="macOS only")
class TestMacOSFeatures:
    def test_io_counters_limited(self):
        collector = IOCollector()
        # May or may not be available
        result = collector.is_available()
        # Test handles both cases
```

### Windows-Specific Tests

**Features to test:**
- Partial I/O support
- Different path handling
- Subprocess behavior

```python
@pytest.mark.skipif(sys.platform != 'win32', reason="Windows only")
class TestWindowsFeatures:
    def test_path_handling(self):
        # Test Windows path separators
        pass
```

### Cross-Platform Tests

**Test graceful degradation:**
```python
def test_io_collector_platform_detection():
    """IO collector should detect platform support."""
    collector = IOCollector()
    is_available = collector.is_available()

    if sys.platform == 'linux':
        assert is_available is True
    # Other platforms may vary

    # Should not crash regardless of platform
    collector.setup()
    result = collector.stop()
    assert result.name == "disk_io"
```

---

## Performance Testing

### Benchmark the Benchmarker

**Measure overhead:**
```python
def test_decorator_overhead():
    """Measure decorator overhead."""

    def bare_function():
        return sum(range(1000))

    @benchmark(warmup=0, runs=100, store=False)
    def decorated_function():
        return sum(range(1000))

    # Measure bare function
    bare_times = []
    for _ in range(100):
        start = time.perf_counter()
        bare_function()
        bare_times.append(time.perf_counter() - start)

    # Overhead should be < 1% for functions > 1ms
    bare_mean = statistics.mean(bare_times)
    # Note: This is a meta-test, not a regular unit test
```

### Test Database Performance

**Test with realistic data volumes:**
```python
@pytest.mark.slow
def test_database_bulk_insert_performance(temp_database):
    """Test database can handle bulk inserts efficiently."""
    db = BenchmarkDatabase(temp_database)

    # Insert 10,000 measurements
    start = time.perf_counter()
    for i in range(10000):
        db.insert_measurement(...)
    elapsed = time.perf_counter() - start

    # Should complete in reasonable time
    assert elapsed < 5.0  # 5 seconds for 10k inserts
```

---

## Test Maintenance

### Keep Tests Fast

**Strategies:**
1. Use in-memory databases
2. Mock slow operations
3. Minimize setup/teardown
4. Use appropriate fixture scopes
5. Run expensive tests only in CI

**Marks for slow tests:**
```python
@pytest.mark.slow
def test_expensive_operation():
    # Only runs with: pytest -m slow
    pass
```

### Keep Tests Independent

**Each test should:**
- Not rely on execution order
- Clean up after itself
- Not share mutable state
- Not affect other tests

**Anti-pattern:**
```python
# BAD: Shared state
shared_db = None

def test_a():
    global shared_db
    shared_db = create_db()

def test_b():
    # Depends on test_a running first!
    query(shared_db)
```

**Good pattern:**
```python
# GOOD: Independent tests
@pytest.fixture
def db():
    database = create_db()
    yield database
    database.close()

def test_a(db):
    insert_data(db)

def test_b(db):
    # Fresh database
    query(db)
```

### Test Documentation

**Docstrings for complex tests:**
```python
def test_benchmark_comparison_with_significance():
    """
    Test benchmark comparison with statistical significance.

    This test verifies that:
    1. Comparisons correctly calculate speedup factor
    2. Statistical significance is determined using t-test
    3. Results are stored in comparison table
    4. Edge cases (identical results, missing data) are handled
    """
    # Test implementation
```

---

## Summary

### Key Testing Principles

1. **Fast**: Unit tests in milliseconds, full suite in seconds
2. **Isolated**: Use mocks for external dependencies
3. **Deterministic**: No flaky tests, reproducible results
4. **Comprehensive**: 90%+ coverage, all edge cases
5. **Maintainable**: Clear names, good documentation

### Test Execution

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=plainbench --cov-report=html

# Run specific test file
pytest tests/unit/test_metrics.py

# Run specific test
pytest tests/unit/test_metrics.py::test_wall_time_collector

# Run with verbose output
pytest -v

# Run and stop at first failure
pytest -x

# Run only fast tests
pytest -m "not slow"

# Run with parallel execution
pytest -n auto
```

### Success Criteria

- **All tests pass** on all supported platforms
- **Coverage ≥ 90%** for core modules
- **Fast feedback**: Full suite runs in < 60 seconds
- **No flaky tests**: 100% deterministic
- **CI/CD integrated**: Automated testing on every commit

---

**End of Test Strategy Document**
