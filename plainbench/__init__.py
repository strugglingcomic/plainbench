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

__all__ = [
    "__version__",
    "benchmark",
    "BenchmarkDatabase",
    "BenchmarkConfig",
]
