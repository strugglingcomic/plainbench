"""
Analysis module for benchmark results.

Provides:
- Statistical computations (mean, median, stddev, percentiles)
- Benchmark comparison with significance testing
- Performance regression detection
- Export functionality (JSON, CSV, HTML)
"""

from plainbench.analysis.comparison import compare_runs, detect_regressions

__all__ = ['compare_runs', 'detect_regressions']
