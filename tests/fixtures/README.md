# Test Fixtures

This directory contains test fixtures and sample data for PlainBench tests.

## Contents

### `mock_data.py`
Mock data generators for testing:
- `create_sample_measurements()` - Generate sample measurement data
- `create_sample_runs()` - Populate database with sample benchmark runs
- `create_sample_environment()` - Create sample environment metadata
- `create_sample_statistics()` - Generate statistical data

### `sample_functions.py`
Sample Python functions for benchmarking tests:
- `fast_function()` - Quick execution for testing overhead
- `slow_function()` - Longer execution for accuracy tests
- `memory_intensive_function()` - Memory allocation tests
- `cpu_intensive_function()` - CPU-bound computation tests
- `io_intensive_function()` - I/O operation tests

### `sample_configs.py`
Sample configuration objects:
- `minimal_config()` - Minimal configuration
- `moderate_config()` - Standard configuration
- `maximum_config()` - Full-featured configuration
- `custom_metrics_config()` - Configuration with custom metrics

### `test_scripts/`
Shell scripts for testing shell command benchmarking:
- `fast_script.sh` - Quick script (< 100ms)
- `slow_script.sh` - Longer script (> 1s)
- `io_intensive.sh` - Script with file I/O
- `memory_intensive.sh` - Script that allocates memory
- `failing_script.sh` - Script that exits with error

## Usage

### Using Fixtures in Tests

Fixtures are automatically available via pytest's conftest.py:

```python
def test_something(sample_measurements):
    """sample_measurements fixture is injected by pytest."""
    stats = compute_statistics(sample_measurements)
    assert stats.mean > 0
```

### Loading Sample Data Programmatically

```python
from tests.fixtures.mock_data import create_sample_runs

def test_queries(temp_database):
    db = BenchmarkDatabase(temp_database)
    create_sample_runs(db)  # Populate with sample data

    # Now test queries
    runs = db.get_all_runs()
    assert len(runs) > 0
```

### Using Sample Functions

```python
from tests.fixtures.sample_functions import cpu_intensive_function

def test_benchmark_cpu():
    @benchmark()
    def wrapper():
        return cpu_intensive_function(n=1000)

    result = wrapper()
```

### Using Sample Scripts

```python
from pathlib import Path

def test_shell_benchmark():
    script_path = Path(__file__).parent / 'fixtures' / 'test_scripts' / 'fast_script.sh'
    result = benchmark_shell(str(script_path))
    assert result.exit_code == 0
```

## Adding New Fixtures

When adding new fixtures:

1. **Create the fixture file** in this directory
2. **Document the fixture** in this README
3. **Add pytest fixture** in `conftest.py` if needed
4. **Include usage examples** in docstrings

### Example: Adding a New Mock Data Generator

```python
# In mock_data.py
def create_sample_comparisons(db, baseline_run_id, current_run_id):
    """
    Create sample benchmark comparisons.

    Args:
        db: BenchmarkDatabase instance
        baseline_run_id: ID of baseline run
        current_run_id: ID of current run

    Returns:
        list[BenchmarkComparison]: Created comparisons
    """
    # Implementation here
    pass
```

## Fixture Data Characteristics

### Measurement Data
- **Sample size**: 10-100 measurements per test
- **Timing values**: Realistic (microseconds to seconds)
- **Memory values**: Realistic (KB to GB)
- **Variance**: Small stddev for stable tests

### Run Data
- **Number of runs**: 3-10 per test scenario
- **Git info**: Realistic commit hashes and branches
- **Timestamps**: Sequential, evenly spaced

### Environment Data
- **Platform**: Covers Linux, macOS, Windows
- **Python versions**: 3.9, 3.10, 3.11, 3.12
- **System specs**: Realistic CPU/memory configurations

## Best Practices

1. **Keep fixtures small**: Only include necessary data
2. **Make fixtures reusable**: Design for multiple test scenarios
3. **Use factories**: Prefer factory functions over fixed data
4. **Document assumptions**: Note any specific requirements
5. **Clean up**: Ensure fixtures don't leave side effects

## Performance Considerations

- Fixtures should load **quickly** (< 100ms)
- Use in-memory databases for **speed**
- Generate data on-demand rather than pre-loading
- Cache expensive fixtures with appropriate scope

## Platform-Specific Fixtures

Some fixtures behave differently by platform:

### Linux-Specific
- I/O counter fixtures (full support)
- cgroups-related data

### macOS-Specific
- Limited I/O data
- ru_maxrss in bytes (not KB)

### Windows-Specific
- Windows-specific path handling
- Limited subprocess metrics

Use `sys.platform` checks or pytest markers to handle platform differences:

```python
import sys
import pytest

@pytest.mark.skipif(sys.platform != 'linux', reason="Linux only")
def test_linux_feature(linux_specific_fixture):
    # Test code
    pass
```

## Troubleshooting

### Fixture Not Found
- Ensure fixture is defined in `conftest.py`
- Check fixture name matches parameter name
- Verify fixture scope is appropriate

### Fixture Cleanup Issues
- Use `yield` instead of `return` for cleanup
- Ensure cleanup code runs even on test failure
- Check for resource leaks (files, connections)

### Slow Tests
- Reduce fixture data size
- Use session-scoped fixtures for shared data
- Consider lazy loading for expensive fixtures

## Contributing

When contributing new fixtures:

1. Add to appropriate file (`mock_data.py`, `sample_functions.py`, etc.)
2. Update this README with usage examples
3. Add corresponding tests to verify fixture works
4. Document any platform-specific behavior
5. Keep fixtures focused and composable
