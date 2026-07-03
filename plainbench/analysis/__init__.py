"""
Analysis of stored benchmark runs: comparison and regression detection.
"""

from plainbench.analysis.comparison import (
    RunComparison,
    compare_runs,
    detect_regressions,
)

__all__ = ["RunComparison", "compare_runs", "detect_regressions"]
