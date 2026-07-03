"""Benchmark decorator for Python functions."""

import functools
import gc
import inspect
from contextlib import contextmanager
from typing import Any, Callable, List, Optional

from ..config.settings import BenchmarkConfig
from ..isolation.factory import create_isolation_strategy
from ..metrics.registry import get_metric_registry
from ..storage.database import BenchmarkDatabase


@contextmanager
def _benchmark_session(isolation: str, metric_names: List[str]):
    """Set up isolation and metric collectors, tearing both down afterwards."""
    isolation_strategy = create_isolation_strategy(isolation)
    collectors = get_metric_registry().create_collectors(metric_names)

    isolation_strategy.setup()
    try:
        for collector in collectors:
            collector.setup()
        try:
            yield collectors
        finally:
            for collector in collectors:
                collector.cleanup()
    finally:
        isolation_strategy.teardown()


@contextmanager
def _measured(collectors, disable_gc: bool, measurements: List[dict]):
    """Measure one iteration: the with-block body is the timed call."""
    if disable_gc:
        gc.collect()
        gc.disable()
    try:
        for collector in collectors:
            collector.start()

        yield

        metric_results = {}
        for collector in collectors:
            metric_result = collector.stop()
            metric_results[metric_result.name] = metric_result
        measurements.append(metric_results)
    finally:
        if disable_gc:
            gc.enable()


def _store_results(
    benchmark_name: str,
    measurements: List[dict],
    warmup: int,
    runs: int,
    isolation: str,
    disable_gc: bool,
    database: Optional[str],
) -> None:
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

    Each call of the decorated function runs warmup + measurement
    iterations, collects the requested metrics, and (by default) stores
    the measurements in a local SQLite database for later comparison.

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
        metric_names = metrics if metrics is not None else ["wall_time", "cpu_time", "python_memory"]

        def validate() -> None:
            if warmup < 0:
                raise ValueError(f"warmup must be >= 0, got {warmup}")
            if runs <= 0:
                raise ValueError(f"runs must be > 0, got {runs}")

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapper(*args, **func_kwargs) -> Any:
                validate()
                with _benchmark_session(isolation, metric_names) as collectors:
                    for _ in range(warmup):
                        await func(*args, **func_kwargs)

                    measurements: List[dict] = []
                    for _ in range(runs):
                        with _measured(collectors, disable_gc, measurements):
                            result = await func(*args, **func_kwargs)

                    if store:
                        _store_results(
                            benchmark_name, measurements, warmup, runs,
                            isolation, disable_gc, database,
                        )
                    return result

        else:

            @functools.wraps(func)
            def wrapper(*args, **func_kwargs) -> Any:
                validate()
                with _benchmark_session(isolation, metric_names) as collectors:
                    for _ in range(warmup):
                        func(*args, **func_kwargs)

                    measurements: List[dict] = []
                    for _ in range(runs):
                        with _measured(collectors, disable_gc, measurements):
                            result = func(*args, **func_kwargs)

                    if store:
                        _store_results(
                            benchmark_name, measurements, warmup, runs,
                            isolation, disable_gc, database,
                        )
                    return result

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
