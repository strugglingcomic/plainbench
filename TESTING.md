# PlainBench Testing Strategy

This document describes the comprehensive testing strategy implemented for PlainBench to ensure code quality, reliability, and maintainability.

## Table of Contents

- [Overview](#overview)
- [Test Coverage Goals](#test-coverage-goals)
- [Testing Infrastructure](#testing-infrastructure)
- [Test Organization](#test-organization)
- [Running Tests](#running-tests)
- [Continuous Integration](#continuous-integration)
- [Code Quality](#code-quality)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Current Coverage Status](#current-coverage-status)
- [Contributing](#contributing)

## Overview

PlainBench uses a multi-layered testing approach combining:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test realistic workflows with mock data stores
- **Linting**: Enforce code style and catch common errors
- **Type Checking**: Optional static type analysis
- **Coverage Tracking**: Monitor test coverage across the codebase

## Test Coverage Goals

**Target**: 80% code coverage across all modules

### Current Module Coverage

| Module | Coverage | Status |
|--------|----------|--------|
| Shell (runner.py) | 91.67% | ✅ Excellent |
| Shell (monitor.py) | 84.93% | ✅ Good |
| Shell (results.py) | 100% | ✅ Complete |
| Storage (models.py) | 100% | ✅ Complete |
| Storage (schema.py) | 100% | ✅ Complete |
| Mocks (overall) | 15-36% | ⚠️ Needs improvement |
| Decorators | 8.11% | ⚠️ Needs improvement |
| Utils | 0% | ⚠️ Needs tests |

## Testing Infrastructure

### Test Framework

- **pytest**: Primary test runner
- **pytest-cov**: Coverage measurement
- **pytest-asyncio**: Async function testing
- **pytest-mock**: Mocking support
- **pytest-timeout**: Timeout control
- **hypothesis**: Property-based testing (available)

### Configuration

Test configuration is defined in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
addopts = [
    "-v",
    "--strict-markers",
    "--cov=plainbench",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
    "benchmark: marks tests as benchmarks",
    "requires_docker: marks tests that require Docker",
    "requires_linux: marks tests that require Linux",
]
timeout = 300
```

## Test Organization

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── unit/                       # Unit tests
│   ├── test_analysis.py        # Analysis module tests (100%)
│   ├── test_config.py          # Configuration tests (100%)
│   ├── test_decorators.py      # Decorator tests (needs improvement)
│   ├── test_isolation.py       # Isolation strategy tests (100%)
│   ├── test_metrics.py         # Metrics collector tests (91.9%)
│   ├── test_mocks.py           # Mock data store tests
│   ├── test_shell.py           # Shell benchmarking tests (stubs)
│   ├── test_shell_real.py      # Working shell tests (✅ NEW)
│   └── test_storage.py         # Storage/database tests (100%)
└── integration/                # Integration tests
    ├── test_decorator_e2e.py   # End-to-end decorator tests
    ├── test_shell_e2e.py       # End-to-end shell tests
    ├── test_mock_postgres_integration.py  # Postgres mock integration (✅ NEW)
    ├── test_mock_redis_integration.py     # Redis mock integration (✅ NEW)
    └── test_mock_kafka_integration.py     # Kafka mock integration (✅ NEW)
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=plainbench --cov-report=html
```

### Run Specific Test File

```bash
pytest tests/unit/test_shell_real.py -v
```

### Run Integration Tests Only

```bash
pytest tests/integration/ -v
```

### Run with Markers

```bash
# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit
```

### Coverage Reports

After running tests with coverage, reports are generated in:

- **Terminal**: Immediate feedback with missing lines
- **HTML**: `htmlcov/index.html` - Interactive browsable report
- **XML**: `coverage.xml` - For CI/CD integration

## Continuous Integration

### GitHub Actions Workflows

Three CI workflows are configured:

#### 1. Linting (`lint.yml`)

Runs on all pushes and PRs to `main` and `claude/**` branches.

**Jobs**:
- **Ruff Linter**: Check code style and common errors
- **MyPy**: Optional type checking (non-blocking)

```yaml
# Triggered on: push to main/claude/**, PRs to main
# Runs: ruff check, ruff format --check, mypy
```

#### 2. Tests (`test.yml`)

Comprehensive test matrix across Python versions and operating systems.

**Matrix**:
- Python: 3.8, 3.9, 3.10, 3.11, 3.12
- OS: Ubuntu, macOS, Windows (reduced matrix for efficiency)

**Features**:
- Parallel test execution across matrix
- Coverage reporting to Codecov
- Coverage threshold checking (80% target)
- Artifacts: HTML coverage reports (30-day retention)

#### 3. PR Checks (`pr-checks.yml`)

Fast checks for pull requests.

**Jobs**:
- Lint & format verification
- Full test suite
- Coverage report with threshold check

## Code Quality

### Linting with Ruff

Ruff is a fast, modern Python linter that combines multiple tools:

```toml
[tool.ruff]
line-length = 100
target-version = "py38"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "SIM", # flake8-simplify
]
```

**Run linting**:
```bash
ruff check plainbench/ tests/
```

**Auto-fix issues**:
```bash
ruff check plainbench/ --fix
```

**Format code**:
```bash
ruff format plainbench/ tests/
```

### Type Checking (Optional)

MyPy provides static type analysis:

```bash
mypy plainbench/
```

Configuration in `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
check_untyped_defs = true
strict_equality = true
```

## Pre-commit Hooks

Pre-commit hooks automatically run checks before each commit.

### Setup

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

### Configured Hooks

1. **Standard Hooks** (from pre-commit-hooks)
   - Trailing whitespace removal
   - End-of-file fixer
   - YAML/JSON/TOML validation
   - Large file check (max 1MB)
   - Merge conflict detection
   - Debug statement detection

2. **Ruff** (linting and formatting)
   - Auto-fix linting issues
   - Format code

3. **MyPy** (type checking)
   - Type validation (non-blocking for tests/examples)

4. **Pytest** (local test runner)
   - Runs tests before commit
   - Stops at first failure for quick feedback

## Current Coverage Status

### Overall Coverage: ~58% → Target: 80%

**High Coverage Modules** (>80%):
- ✅ Shell runner: 91.67%
- ✅ Shell monitor: 84.93%
- ✅ Shell results: 100%
- ✅ Storage models: 100%
- ✅ Storage schema: 100%
- ✅ Analysis: High coverage
- ✅ Configuration: High coverage

**Needs Improvement** (<40%):
- ⚠️ Decorators: 8.11%
- ⚠️ Metrics collectors: 32-53%
- ⚠️ Utils (git, platform): 0%
- ⚠️ Mocks: 15-36%
- ⚠️ Storage database: 21.26%

## Realistic Testing Examples

### E-Commerce Application Example

A comprehensive e-commerce order processing example demonstrates:

- PostgreSQL for order database
- Redis for caching
- Kafka for event streaming
- Realistic latency simulation
- Complete business logic benchmarking

**Location**: `examples/realistic_ecommerce_app.py`

**Usage**:
```bash
python examples/realistic_ecommerce_app.py
```

### Integration Tests

New integration tests demonstrate real-world scenarios:

- **PostgreSQL**: CRUD operations, transactions, joins, analytics
- **Redis**: Caching patterns, sessions, rate limiting, leaderboards
- **Kafka**: Event streaming, clickstreams, order pipelines, aggregations

**Run integration tests**:
```bash
pytest tests/integration/test_mock_*_integration.py -v
```

## Contributing

### Writing New Tests

1. **Unit Tests**: Test individual functions/classes in isolation
   - Place in `tests/unit/test_<module>.py`
   - Use mocks for external dependencies
   - Aim for >90% coverage per module

2. **Integration Tests**: Test complete workflows
   - Place in `tests/integration/test_<feature>_integration.py`
   - Use mock data stores for realistic testing
   - Test end-to-end scenarios

3. **Test Naming Convention**:
   - Test classes: `TestFeatureName`
   - Test methods: `test_specific_behavior`
   - Be descriptive: `test_order_creation_with_insufficient_inventory`

### Before Submitting PR

1. **Run tests locally**:
   ```bash
   pytest
   ```

2. **Check coverage**:
   ```bash
   pytest --cov=plainbench --cov-report=term-missing
   ```

3. **Run linting**:
   ```bash
   ruff check plainbench/ --fix
   ruff format plainbench/
   ```

4. **Verify pre-commit hooks pass**:
   ```bash
   pre-commit run --all-files
   ```

5. **Ensure coverage meets target** (80%)

### Test Best Practices

1. **Arrange-Act-Assert Pattern**:
   ```python
   def test_feature():
       # Arrange: Set up test data
       config = BenchmarkConfig(runs=5)

       # Act: Execute the feature
       result = benchmark_function(config)

       # Assert: Verify the outcome
       assert result.iterations == 5
   ```

2. **Use Fixtures for Repeated Setup**:
   ```python
   @pytest.fixture
   def temp_database():
       db = Database(":memory:")
       yield db
       db.close()
   ```

3. **Test Edge Cases**:
   - Empty inputs
   - Null/None values
   - Large datasets
   - Concurrent access
   - Error conditions

4. **Keep Tests Fast**:
   - Use in-memory databases
   - Mock slow operations
   - Mark slow tests with `@pytest.mark.slow`

## Roadmap

### Short Term (Next PR)
- [ ] Add utils module tests (git, platform)
- [ ] Improve decorator test coverage to >80%
- [ ] Add more mock data store tests
- [ ] Fix integration test imports
- [ ] Reach 80% overall coverage

### Medium Term
- [ ] Add CLI tests (when CLI is implemented)
- [ ] Add mutation testing
- [ ] Add performance regression tests
- [ ] Set up coverage badges
- [ ] Add benchmark comparison in CI

### Long Term
- [ ] Property-based testing with Hypothesis
- [ ] Fuzz testing for robust inputs
- [ ] Performance profiling in CI
- [ ] Cross-platform compatibility matrix
- [ ] Docker-based integration tests

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

## Questions?

For questions about testing:
- Review existing tests in `tests/` for examples
- Check this documentation for guidance
- Open an issue on GitHub for help
