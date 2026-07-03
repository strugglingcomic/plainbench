"""
PlainBench: a simple, local-first benchmarking library for comparing
algorithms and system designs under different infrastructure assumptions.

Everything runs on your laptop. Datastores (Postgres, Redis, Kafka) are
SQLite-backed mocks with realistic, configurable latency profiles, so you
can see how competing designs behave on real infrastructure — without
deploying any.

Compare implementations:

    from plainbench import compare

    result = compare({
        "sorted": lambda: sorted(data),
        "heapq": lambda: heapq.nsmallest(len(data), data),
    })
    result.print()

Compare designs across infrastructure assumptions:

    from plainbench import compare_profiles

    compare_profiles(
        {"n_plus_one": n_plus_one, "batched": batched},
        profiles=["in_process", "same_zone", "cross_region"],
    ).print()

Track results over time with @benchmark, which stores measurements in a
local SQLite database for later comparison and regression detection.
"""

from plainbench.__version__ import __version__
from plainbench.comparison import (
    CandidateStats,
    ComparisonResult,
    ProfileComparison,
    compare,
    compare_profiles,
)
from plainbench.config.settings import BenchmarkConfig
from plainbench.decorators.benchmark import benchmark
from plainbench.mocks import (
    NETWORK_PROFILES,
    LatencyConfig,
    use_mock_datastore,
    use_mock_kafka,
    use_mock_postgres,
    use_mock_redis,
)
from plainbench.storage.database import BenchmarkDatabase

__all__ = [
    "__version__",
    # Comparison (the front door)
    "compare",
    "compare_profiles",
    "CandidateStats",
    "ComparisonResult",
    "ProfileComparison",
    # Tracked benchmarking
    "benchmark",
    "BenchmarkDatabase",
    "BenchmarkConfig",
    # Mock datastores
    "use_mock_postgres",
    "use_mock_kafka",
    "use_mock_redis",
    "use_mock_datastore",
    "LatencyConfig",
    "NETWORK_PROFILES",
]
