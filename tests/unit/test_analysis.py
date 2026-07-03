"""Unit tests for run comparison and regression detection."""

import pytest

from plainbench.analysis import RunComparison, compare_runs, detect_regressions
from plainbench.storage.database import BenchmarkDatabase


class FakeMetric:
    def __init__(self, value):
        self.value = value


def store_run(db, name, times):
    return db.store_benchmark_results(
        benchmark_name=name,
        measurements=[{"wall_time": FakeMetric(t)} for t in times],
        metadata={},
    )


@pytest.fixture
def db_with_regression(tmp_path):
    """Baseline run ~10ms, current run ~20ms for the same benchmark."""
    path = str(tmp_path / "bench.db")
    with BenchmarkDatabase(path) as db:
        baseline = store_run(db, "bench", [0.010, 0.011, 0.010, 0.009, 0.010])
        current = store_run(db, "bench", [0.020, 0.021, 0.020, 0.019, 0.020])
    return path, baseline, current


class TestCompareRuns:
    def test_detects_slowdown(self, db_with_regression):
        path, baseline, current = db_with_regression
        comparisons = compare_runs(path, baseline, current)
        assert len(comparisons) == 1
        c = comparisons[0]
        assert c.benchmark_name == "bench"
        assert c.change == pytest.approx(1.0, rel=0.1)  # ~100% slower
        assert c.is_significant
        assert c.is_regression()
        assert not c.is_improvement()

    def test_direction_matters(self, db_with_regression):
        path, baseline, current = db_with_regression
        # Reversed: current is faster than baseline
        c = compare_runs(path, current, baseline)[0]
        assert c.is_improvement()
        assert not c.is_regression()
        assert c.speedup > 1.5

    def test_accepts_open_database(self, db_with_regression):
        path, baseline, current = db_with_regression
        with BenchmarkDatabase(path) as db:
            assert len(compare_runs(db, baseline, current)) == 1
            # Database is still usable afterwards (not closed by compare_runs)
            assert db.get_latest_run() is not None

    def test_no_common_benchmarks(self, tmp_path):
        path = str(tmp_path / "bench.db")
        with BenchmarkDatabase(path) as db:
            run_a = store_run(db, "alpha", [0.01, 0.01])
            run_b = store_run(db, "beta", [0.01, 0.01])
        assert compare_runs(path, run_a, run_b) == []

    def test_identical_runs_not_flagged(self, tmp_path):
        path = str(tmp_path / "bench.db")
        times = [0.010, 0.011, 0.009, 0.010, 0.010]
        with BenchmarkDatabase(path) as db:
            run_a = store_run(db, "bench", times)
            run_b = store_run(db, "bench", times)
        c = compare_runs(path, run_a, run_b)[0]
        assert not c.is_regression()
        assert not c.is_improvement()


class TestDetectRegressions:
    def test_returns_only_regressions(self, db_with_regression):
        path, baseline, current = db_with_regression
        regressions = detect_regressions(path, baseline, current)
        assert [r.benchmark_name for r in regressions] == ["bench"]
        # And nothing when comparing the other way
        assert detect_regressions(path, current, baseline) == []

    def test_threshold_filters_small_changes(self, db_with_regression):
        path, baseline, current = db_with_regression
        # 100% slowdown is below a 200% threshold
        assert detect_regressions(path, baseline, current, threshold=2.0) == []


class TestRunComparisonModel:
    def test_change_and_speedup(self):
        c = RunComparison("x", baseline_mean=0.010, current_mean=0.005, p_value=0.001, is_significant=True)
        assert c.change == pytest.approx(-0.5)
        assert c.speedup == pytest.approx(2.0)
