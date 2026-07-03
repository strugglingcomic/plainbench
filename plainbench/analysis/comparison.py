"""Comparison and regression detection across stored benchmark runs."""

import math
import statistics
from dataclasses import dataclass
from typing import List, Union

from plainbench.storage.database import BenchmarkDatabase


@dataclass
class RunComparison:
    """Change in one benchmark between two stored runs."""

    benchmark_name: str
    baseline_mean: float
    current_mean: float
    p_value: float
    is_significant: bool

    @property
    def change(self) -> float:
        """Relative change in mean wall time (+0.10 = 10% slower)."""
        return (self.current_mean - self.baseline_mean) / self.baseline_mean

    @property
    def speedup(self) -> float:
        """baseline_mean / current_mean (>1 means the current run is faster)."""
        return self.baseline_mean / self.current_mean

    def is_regression(self, threshold: float = 0.05) -> bool:
        """True if significantly slower than baseline by more than threshold."""
        return self.is_significant and self.change > threshold

    def is_improvement(self, threshold: float = 0.05) -> bool:
        """True if significantly faster than baseline by more than threshold."""
        return self.is_significant and self.change < -threshold


def _welch_t_p_value(a: List[float], b: List[float]) -> float:
    """
    Two-sided p-value for Welch's t-test using a normal approximation.

    Good enough to flag obviously-real differences in benchmark timings
    without pulling in scipy; for small sample counts it slightly
    understates the p-value.
    """
    if len(a) < 2 or len(b) < 2:
        return 1.0

    var_a = statistics.variance(a)
    var_b = statistics.variance(b)
    se = math.sqrt(var_a / len(a) + var_b / len(b))
    if se == 0.0:
        return 0.0 if statistics.fmean(a) != statistics.fmean(b) else 1.0

    t = (statistics.fmean(a) - statistics.fmean(b)) / se
    return math.erfc(abs(t) / math.sqrt(2))


def compare_runs(
    database: Union[str, BenchmarkDatabase],
    baseline_run_id: int,
    current_run_id: int,
    alpha: float = 0.05,
) -> List[RunComparison]:
    """
    Compare wall times of two stored runs, benchmark by benchmark.

    Args:
        database: Database path or an initialized BenchmarkDatabase
        baseline_run_id: Run to compare against
        current_run_id: Run being evaluated
        alpha: Significance level for the t-test

    Returns:
        One RunComparison per benchmark present in both runs.
    """
    own_db = isinstance(database, str)
    db = BenchmarkDatabase(database) if own_db else database
    if own_db:
        db.initialize()

    try:
        baseline = db.get_run_wall_times(baseline_run_id)
        current = db.get_run_wall_times(current_run_id)
    finally:
        if own_db:
            db.close()

    comparisons = []
    for name in sorted(set(baseline) & set(current)):
        p_value = _welch_t_p_value(baseline[name], current[name])
        comparisons.append(
            RunComparison(
                benchmark_name=name,
                baseline_mean=statistics.fmean(baseline[name]),
                current_mean=statistics.fmean(current[name]),
                p_value=p_value,
                is_significant=p_value < alpha,
            )
        )
    return comparisons


def detect_regressions(
    database: Union[str, BenchmarkDatabase],
    baseline_run_id: int,
    current_run_id: int,
    threshold: float = 0.05,
    alpha: float = 0.05,
) -> List[RunComparison]:
    """
    Return benchmarks that got significantly slower between two runs.

    Args:
        database: Database path or an initialized BenchmarkDatabase
        baseline_run_id: Run to compare against
        current_run_id: Run being evaluated
        threshold: Minimum relative slowdown to count (0.05 = 5%)
        alpha: Significance level for the t-test
    """
    return [
        c
        for c in compare_runs(database, baseline_run_id, current_run_id, alpha=alpha)
        if c.is_regression(threshold)
    ]
