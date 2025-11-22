# PlainBench Repository Structure

**Version:** 1.0
**Date:** 2025-11-22

---

## Table of Contents

1. [Overview](#overview)
2. [Directory Structure](#directory-structure)
3. [Package Organization](#package-organization)
4. [Documentation Structure](#documentation-structure)
5. [Test Structure](#test-structure)
6. [Configuration Files](#configuration-files)
7. [Examples and Demos](#examples-and-demos)

---

## Overview

PlainBench is organized as a modern Python package following best practices for code organization, testing, and documentation. The structure supports:

- **Modular architecture** with clear separation of concerns
- **Extensible design** for custom metrics and isolation strategies
- **Comprehensive testing** with unit, integration, and benchmark tests
- **Rich documentation** with examples and API references
- **CI/CD ready** configuration

---

## Directory Structure

```
plainbench/
├── .github/                      # GitHub Actions workflows
│   └── workflows/
│       ├── tests.yml            # Automated testing
│       ├── benchmarks.yml       # Performance regression detection
│       └── publish.yml          # PyPI publishing
│
├── docs/                        # Documentation
│   ├── architecture/           # Architecture and design docs
│   │   ├── repository-structure.md
│   │   ├── technical-specification.md
│   │   └── configuration-schema.md
│   ├── api/                    # API documentation
│   │   ├── decorators.md
│   │   ├── shell.md
│   │   ├── storage.md
│   │   └── cli.md
│   ├── guides/                 # User guides
│   │   ├── quickstart.md
│   │   ├── python-functions.md
│   │   ├── shell-commands.md
│   │   ├── isolation.md
│   │   ├── comparison.md
│   │   └── best-practices.md
│   ├── research.md             # Research findings
│   └── index.md                # Documentation home
│
├── plainbench/                 # Main package
│   ├── __init__.py            # Package initialization, public API
│   ├── __version__.py         # Version string
│   │
│   ├── metrics/               # Metrics collection
│   │   ├── __init__.py
│   │   ├── base.py           # Base metric collector interface
│   │   ├── timing.py         # Wall time and CPU time
│   │   ├── memory.py         # tracemalloc and psutil memory
│   │   ├── cpu.py            # CPU usage and affinity
│   │   ├── io.py             # Disk I/O metrics
│   │   └── registry.py       # Metric registry for custom metrics
│   │
│   ├── decorators/           # Decorator system
│   │   ├── __init__.py
│   │   ├── benchmark.py      # Main @benchmark decorator
│   │   ├── context.py        # Context manager for manual timing
│   │   └── hooks.py          # Pre/post execution hooks
│   │
│   ├── shell/                # Shell command benchmarking
│   │   ├── __init__.py
│   │   ├── runner.py         # Shell command execution
│   │   ├── monitor.py        # Process monitoring with psutil
│   │   └── resource.py       # Unix resource module integration
│   │
│   ├── isolation/            # Isolation strategies
│   │   ├── __init__.py
│   │   ├── base.py           # Base isolation interface
│   │   ├── minimal.py        # Minimal isolation (subprocess only)
│   │   ├── moderate.py       # Moderate (CPU pinning, GC control)
│   │   ├── maximum.py        # Maximum (Docker, cgroups)
│   │   └── factory.py        # Isolation strategy factory
│   │
│   ├── storage/              # Data persistence
│   │   ├── __init__.py
│   │   ├── database.py       # SQLite database manager
│   │   ├── schema.py         # Database schema definitions
│   │   ├── models.py         # Data models (dataclasses)
│   │   ├── queries.py        # Common query patterns
│   │   └── migrations/       # Database migrations
│   │       └── __init__.py
│   │
│   ├── analysis/             # Results analysis
│   │   ├── __init__.py
│   │   ├── statistics.py     # Statistical computations
│   │   ├── comparison.py     # Benchmark comparison
│   │   ├── regression.py     # Regression detection
│   │   └── export.py         # Export to various formats
│   │
│   ├── config/               # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py       # Configuration classes
│   │   ├── loader.py         # Config file loading (YAML/TOML)
│   │   └── defaults.py       # Default configurations
│   │
│   ├── cli/                  # Command-line interface
│   │   ├── __init__.py
│   │   ├── main.py           # Main CLI entry point
│   │   ├── commands/         # CLI commands
│   │   │   ├── __init__.py
│   │   │   ├── run.py        # Run benchmarks
│   │   │   ├── compare.py    # Compare results
│   │   │   ├── show.py       # Show results
│   │   │   ├── export.py     # Export results
│   │   │   └── init.py       # Initialize new benchmark suite
│   │   └── formatters.py     # Output formatting
│   │
│   └── utils/                # Utilities
│       ├── __init__.py
│       ├── platform.py       # Platform detection
│       ├── environment.py    # Environment info collection
│       ├── git.py            # Git integration
│       └── validation.py     # Input validation
│
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── conftest.py           # pytest fixtures
│   │
│   ├── unit/                 # Unit tests
│   │   ├── __init__.py
│   │   ├── test_metrics.py
│   │   ├── test_decorators.py
│   │   ├── test_shell.py
│   │   ├── test_isolation.py
│   │   ├── test_storage.py
│   │   ├── test_analysis.py
│   │   └── test_config.py
│   │
│   ├── integration/          # Integration tests
│   │   ├── __init__.py
│   │   ├── test_end_to_end.py
│   │   ├── test_database.py
│   │   └── test_cli.py
│   │
│   ├── benchmarks/           # Example benchmarks for testing
│   │   ├── __init__.py
│   │   ├── test_python_functions.py
│   │   └── test_shell_commands.py
│   │
│   └── fixtures/             # Test fixtures and data
│       ├── sample_config.yaml
│       ├── sample_results.json
│       └── test_scripts/
│           └── slow_script.sh
│
├── examples/                 # Example usage
│   ├── README.md
│   ├── basic_decorator.py    # Simple decorator usage
│   ├── shell_commands.py     # Shell command benchmarking
│   ├── custom_metrics.py     # Custom metric collector
│   ├── comparison.py         # Comparing implementations
│   ├── isolation_levels.py   # Different isolation strategies
│   └── advanced/
│       ├── queue_benchmark.py    # Queue implementation comparison
│       ├── sqlite_scenarios.py   # SQLite usage patterns
│       └── algorithm_analysis.py # Algorithm comparison
│
├── scripts/                  # Development and maintenance scripts
│   ├── setup_dev.sh         # Development environment setup
│   ├── run_benchmarks.sh    # Run benchmark suite
│   ├── generate_docs.sh     # Generate documentation
│   └── check_performance.py # Check for performance regressions
│
├── .github/                  # GitHub configuration
│   ├── workflows/
│   └── ISSUE_TEMPLATE/
│
├── .gitignore               # Git ignore patterns
├── .editorconfig            # Editor configuration
├── pyproject.toml           # Project configuration and dependencies
├── setup.py                 # Setup script (for compatibility)
├── README.md                # Project README
├── LICENSE                  # License file
├── CHANGELOG.md             # Version changelog
├── CONTRIBUTING.md          # Contribution guidelines
└── plainbench.yaml.example  # Example configuration file
```

---

## Package Organization

### Core Modules

#### `plainbench/__init__.py`
Exports the public API for easy imports:

```python
from plainbench.decorators import benchmark
from plainbench.shell import benchmark_shell
from plainbench.storage import BenchmarkDatabase
from plainbench.analysis import compare_benchmarks
```

#### `plainbench/metrics/`
**Purpose:** Collect various performance metrics.

- `base.py`: Abstract base class for all metric collectors
- `timing.py`: Wall time and CPU time using `time.perf_counter()` and `time.process_time()`
- `memory.py`: Memory profiling with `tracemalloc` and `psutil`
- `cpu.py`: CPU usage, affinity, and core pinning
- `io.py`: Disk I/O metrics via `psutil`
- `registry.py`: Plugin registry for custom metrics

**Extension Point:** Users can register custom metric collectors.

#### `plainbench/decorators/`
**Purpose:** Decorator-based benchmarking for Python functions.

- `benchmark.py`: Main `@benchmark` decorator with configurable parameters
- `context.py`: Context manager for manual timing control
- `hooks.py`: Pre/post execution hooks for custom setup/teardown

**Key Features:**
- Automatic warmup and multiple runs
- Configurable metrics collection
- Statistical analysis
- Database persistence

#### `plainbench/shell/`
**Purpose:** Black-box benchmarking of shell commands.

- `runner.py`: Execute shell commands and capture output
- `monitor.py`: Real-time process monitoring with `psutil`
- `resource.py`: Unix resource module for additional metrics

**Supports:**
- Both snapshot and continuous monitoring modes
- Platform-specific optimizations
- Timeout handling

#### `plainbench/isolation/`
**Purpose:** Implement different isolation strategies.

- `base.py`: Abstract isolation interface
- `minimal.py`: Basic subprocess isolation
- `moderate.py`: CPU pinning, GC control, environment control
- `maximum.py`: Docker containers, cgroups (Linux)
- `factory.py`: Factory pattern for selecting isolation strategy

**Three-tier Strategy:**
1. **Minimal**: Default, no special requirements
2. **Moderate**: CPU pinning, recommended for local development
3. **Maximum**: Containers/cgroups, best for CI/CD

#### `plainbench/storage/`
**Purpose:** Persist benchmark results to SQLite database.

- `database.py`: Database connection and transaction management
- `schema.py`: SQL schema definitions
- `models.py`: Python dataclasses for type safety
- `queries.py`: Common query patterns and helpers
- `migrations/`: Database schema migrations

**Schema:**
- `benchmark_runs`: Benchmark execution metadata
- `benchmarks`: Benchmark definitions
- `measurements`: Raw measurement data
- `benchmark_statistics`: Pre-computed aggregates
- `environments`: System environment metadata
- `configurations`: Configuration parameters

#### `plainbench/analysis/`
**Purpose:** Analyze and compare benchmark results.

- `statistics.py`: Statistical computations (mean, median, stddev, percentiles)
- `comparison.py`: Compare benchmark results with t-tests
- `regression.py`: Detect performance regressions
- `export.py`: Export to JSON, CSV, HTML formats

**Features:**
- Statistical significance testing
- Trend analysis over time
- Regression detection with configurable thresholds

#### `plainbench/config/`
**Purpose:** Configuration management.

- `settings.py`: Configuration dataclasses
- `loader.py`: Load from YAML/TOML files
- `defaults.py`: Default configuration values

**Supports:**
- File-based configuration
- Environment variable overrides
- CLI argument overrides
- Per-benchmark configuration

#### `plainbench/cli/`
**Purpose:** Command-line interface.

- `main.py`: CLI entry point using Click
- `commands/`: Individual CLI commands
  - `run.py`: Run benchmarks
  - `compare.py`: Compare results
  - `show.py`: Display results
  - `export.py`: Export data
  - `init.py`: Initialize benchmark suite
- `formatters.py`: Pretty-printing for terminal output

#### `plainbench/utils/`
**Purpose:** Shared utilities.

- `platform.py`: Detect OS, CPU, memory
- `environment.py`: Collect environment metadata
- `git.py`: Git repository integration
- `validation.py`: Input validation helpers

---

## Documentation Structure

### `docs/architecture/`
Technical architecture and design documents for maintainers and contributors.

### `docs/api/`
API reference documentation for each module, automatically generated from docstrings.

### `docs/guides/`
User guides and tutorials:

- **quickstart.md**: Get started in 5 minutes
- **python-functions.md**: Benchmark Python functions with decorators
- **shell-commands.md**: Benchmark shell commands
- **isolation.md**: Understanding isolation strategies
- **comparison.md**: Comparing implementations
- **best-practices.md**: Best practices for accurate benchmarking

---

## Test Structure

### `tests/unit/`
Fast, isolated unit tests for individual modules. Use mocks to avoid I/O and subprocess calls.

**Coverage Target:** 90%+

### `tests/integration/`
Integration tests that verify modules work together correctly. May use actual database and subprocess calls.

**Tests:**
- End-to-end benchmark workflows
- Database persistence and retrieval
- CLI command execution

### `tests/benchmarks/`
Example benchmarks used for testing the framework itself. Also serve as examples for users.

### `tests/fixtures/`
Shared test data and fixtures.

---

## Configuration Files

### `pyproject.toml`
Modern Python project configuration following PEP 517/518:
- Project metadata
- Dependencies (runtime and development)
- Tool configurations (pytest, black, mypy, ruff)
- Build system configuration

### `.gitignore`
Ignore patterns for:
- Python bytecode (`__pycache__/`, `*.pyc`)
- Virtual environments (`venv/`, `.env/`)
- IDE files (`.vscode/`, `.idea/`)
- Build artifacts (`dist/`, `build/`, `*.egg-info`)
- Database files (`*.db`, `*.sqlite`)
- Benchmark results (`results/`, `*.benchmark`)

### `.editorconfig`
Consistent coding style across editors:
- UTF-8 encoding
- LF line endings
- 4 spaces for Python
- Trailing whitespace trimming

### `plainbench.yaml.example`
Example configuration file users can copy and customize.

---

## Examples and Demos

### `examples/`
Practical examples demonstrating various use cases:

1. **basic_decorator.py**: Simple function benchmarking
2. **shell_commands.py**: Shell command benchmarking
3. **custom_metrics.py**: Adding custom metrics
4. **comparison.py**: Comparing different implementations
5. **isolation_levels.py**: Different isolation strategies
6. **advanced/**: Complex real-world scenarios

**Purpose:**
- Onboarding new users
- Testing framework features
- Demonstrating best practices

Each example is fully documented and runnable.

---

## Design Rationale

### Modular Organization
Each package has a single, well-defined responsibility, making the codebase easier to:
- Understand
- Test
- Extend
- Maintain

### Separation of Concerns
- **Metrics collection** is independent of **storage**
- **Decorators** are independent of **shell commands**
- **Isolation strategies** are pluggable

This allows users to:
- Use only the parts they need
- Replace components with custom implementations
- Extend functionality without modifying core code

### Extension Points
Key extension points for users:
1. **Custom metrics**: Implement `MetricCollector` interface
2. **Custom isolation**: Implement `IsolationStrategy` interface
3. **Custom storage**: Implement `StorageBackend` interface (future)
4. **Custom analysis**: Use the query API to build custom analysis tools

### Testing Strategy
- **Unit tests**: Fast, isolated, high coverage
- **Integration tests**: Verify components work together
- **Example benchmarks**: Real-world usage patterns

### Documentation-First
Comprehensive documentation ensures:
- Easy onboarding
- Clear API contracts
- Maintainability
- Community contributions

---

## Future Considerations

### Potential Additions
- `plainbench/plugins/`: Third-party plugin system
- `plainbench/remote/`: Remote benchmark execution
- `plainbench/web/`: Web UI for results visualization
- `plainbench/storage/backends/`: Alternative storage backends (PostgreSQL, InfluxDB)

### Scalability
The modular architecture supports future enhancements without major refactoring.

---

**End of Repository Structure Document**
