"""
PlainBench: A Python benchmarking framework with SQLite storage.

PlainBench provides:
- Python function benchmarking via decorators
- Shell command benchmarking
- Multiple metrics: timing, CPU, memory, I/O
- SQLite-backed storage for historical analysis
- Configurable isolation strategies
- Statistical analysis and comparison

Basic usage:

    from plainbench import benchmark

    @benchmark()
    def my_function():
        return sum(range(1000000))

For more information, see the documentation at:
https://github.com/yourusername/plainbench
"""

from plainbench.__version__ import __version__
from plainbench.config.settings import BenchmarkConfig
from plainbench.decorators.benchmark import benchmark
from plainbench.storage.database import BenchmarkDatabase

# Import mock decorators (optional, requires mocks module)
try:
    from plainbench.mocks import (
        use_mock_datastore,
        use_mock_kafka,
        use_mock_postgres,
        use_mock_redis,
    )

    _MOCKS_AVAILABLE = True
except ImportError:
    _MOCKS_AVAILABLE = False

__all__ = [
    "__version__",
    "benchmark",
    "BenchmarkDatabase",
    "BenchmarkConfig",
]

# Add mock decorators to __all__ if available
if _MOCKS_AVAILABLE:
    __all__.extend(
        [
            "use_mock_postgres",
            "use_mock_kafka",
            "use_mock_redis",
            "use_mock_datastore",
        ]
    )
