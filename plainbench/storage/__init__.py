"""
Storage module for benchmark results.

Provides SQLite-backed storage with:
- Database schema management
- Data models (dataclasses)
- Query helpers
- Schema migrations
"""

from plainbench.storage.database import BenchmarkDatabase
from plainbench.storage.models import (
    Environment,
    BenchmarkRun,
    Benchmark,
    Measurement,
    BenchmarkStatistics,
    BenchmarkComparison,
)

__all__ = [
    'BenchmarkDatabase',
    'Environment',
    'BenchmarkRun',
    'Benchmark',
    'Measurement',
    'BenchmarkStatistics',
    'BenchmarkComparison',
]
