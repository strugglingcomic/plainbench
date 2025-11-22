"""Benchmark decorator for Python functions."""

import functools
import gc
from typing import Any, Callable, List, Optional

from ..config.settings import BenchmarkConfig
from ..metrics.registry import get_metric_registry
from ..storage.database import BenchmarkDatabase


def benchmark(
    name: Optional[str] = None,
    warmup: int = 3,
    runs: int = 10,
    metrics: Optional[List[str]] = None,
    isolation: str = "minimal",
    disable_gc: bool = True,
    store: bool = True,
    database: Optional[str] = None,
    **kwargs,
) -> Callable:
    """
    Decorator for benchmarking Python functions.

    Args:
        name: Benchmark name (defaults to function name)
        warmup: Number of warmup iterations
        runs: Number of measurement iterations
        metrics: List of metrics to collect (default: ['wall_time', 'cpu_time', 'python_memory'])
        isolation: Isolation strategy ('minimal', 'moderate', 'maximum')
        disable_gc: Disable garbage collection during measurement
        store: Store results in database
        database: Database path (default: from config)
        **kwargs: Additional configuration options

    Example:
        @benchmark(warmup=5, runs=20, metrics=['wall_time', 'python_memory'])
        def my_function(n):
            return sum(range(n))
    """

    def decorator(func: Callable) -> Callable:
        benchmark_name = name or func.__name__

        # Default metrics
        if metrics is None:
            metric_names = ["wall_time", "cpu_time", "python_memory"]
        else:
            metric_names = metrics

        @functools.wraps(func)
        def wrapper(*args, **func_kwargs) -> Any:
            # Validate parameters
            if warmup < 0:
                raise ValueError(f"warmup must be >= 0, got {warmup}")
            if runs <= 0:
                raise ValueError(f"runs must be > 0, got {runs}")

            # Create metric collectors
            registry = get_metric_registry()
            collectors = registry.create_collectors(metric_names)

            # Setup collectors
            for collector in collectors:
                collector.setup()

            try:
                # Warmup phase
                for _ in range(warmup):
                    func(*args, **func_kwargs)

                # Measurement phase
                measurements = []

                for iteration in range(runs):
                    # Disable GC if requested
                    if disable_gc:
                        gc.collect()
                        gc.disable()

                    try:
                        # Start metrics
                        for collector in collectors:
                            collector.start()

                        # Execute function
                        result = func(*args, **func_kwargs)

                        # Stop metrics
                        metric_results = {}
                        for collector in collectors:
                            metric_result = collector.stop()
                            metric_results[metric_result.name] = metric_result

                        measurements.append(metric_results)

                    finally:
                        if disable_gc:
                            gc.enable()

                # Store results if requested
                if store:
                    db_path = database or BenchmarkConfig.get_default_database()
                    db = BenchmarkDatabase(db_path)
                    db.initialize()
                    try:
                        db.store_benchmark_results(
                            benchmark_name=benchmark_name,
                            measurements=measurements,
                            metadata={
                                "warmup": str(warmup),
                                "runs": str(runs),
                                "isolation": isolation,
                                "disable_gc": str(disable_gc),
                            },
                        )
                    finally:
                        db.close()

                return result

            finally:
                # Cleanup collectors
                for collector in collectors:
                    collector.cleanup()

        # Attach metadata for introspection
        wrapper._is_benchmark = True
        wrapper._benchmark_name = benchmark_name
        wrapper._benchmark_config = {
            "warmup": warmup,
            "runs": runs,
            "metrics": metric_names,
            "isolation": isolation,
        }

        return wrapper

    return decorator
