"""Unit tests for the plainbench CLI."""

import pytest
from click.testing import CliRunner

from plainbench.cli.main import cli
from plainbench.storage.database import BenchmarkDatabase


class FakeMetric:
    def __init__(self, value):
        self.value = value


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def populated_db(tmp_path):
    path = str(tmp_path / "bench.db")
    with BenchmarkDatabase(path) as db:
        run1 = db.store_benchmark_results(
            "fibonacci",
            [{"wall_time": FakeMetric(t)} for t in [0.010, 0.011, 0.010, 0.010, 0.009]],
            {},
        )
        run2 = db.store_benchmark_results(
            "fibonacci",
            [{"wall_time": FakeMetric(t)} for t in [0.020, 0.021, 0.020, 0.020, 0.019]],
            {},
        )
    return path, run1, run2


class TestRunsCommand:
    def test_lists_runs(self, runner, populated_db):
        path, run1, run2 = populated_db
        result = runner.invoke(cli, ["runs", "-d", path])
        assert result.exit_code == 0
        assert "fibonacci" in result.output
        assert str(run1) in result.output and str(run2) in result.output

    def test_empty_database(self, runner, tmp_path):
        result = runner.invoke(cli, ["runs", "-d", str(tmp_path / "empty.db")])
        assert result.exit_code == 0
        assert "No benchmark runs" in result.output


class TestShowCommand:
    def test_shows_latest_by_default(self, runner, populated_db):
        path, _, run2 = populated_db
        result = runner.invoke(cli, ["show", "-d", path])
        assert result.exit_code == 0
        assert f"Run {run2}" in result.output
        assert "fibonacci" in result.output
        assert "mean" in result.output

    def test_shows_specific_run(self, runner, populated_db):
        path, run1, _ = populated_db
        result = runner.invoke(cli, ["show", "-d", path, "--run-id", str(run1)])
        assert result.exit_code == 0
        assert f"Run {run1}" in result.output

    def test_missing_run(self, runner, populated_db):
        path, _, _ = populated_db
        result = runner.invoke(cli, ["show", "-d", path, "--run-id", "999"])
        assert result.exit_code == 0
        assert "No measurements" in result.output


class TestCompareCommand:
    def test_regression_exits_nonzero(self, runner, populated_db):
        path, run1, run2 = populated_db
        result = runner.invoke(cli, ["compare", str(run1), str(run2), "-d", path])
        assert result.exit_code == 1
        assert "REGRESSION" in result.output

    def test_improvement_exits_zero(self, runner, populated_db):
        path, run1, run2 = populated_db
        result = runner.invoke(cli, ["compare", str(run2), str(run1), "-d", path])
        assert result.exit_code == 0
        assert "improvement" in result.output

    def test_no_common_benchmarks(self, runner, tmp_path):
        path = str(tmp_path / "bench.db")
        with BenchmarkDatabase(path) as db:
            run_a = db.store_benchmark_results("a", [{"wall_time": FakeMetric(0.01)}], {})
            run_b = db.store_benchmark_results("b", [{"wall_time": FakeMetric(0.01)}], {})
        result = runner.invoke(cli, ["compare", str(run_a), str(run_b), "-d", path])
        assert result.exit_code == 1
        assert "No benchmarks in common" in result.output


class TestCliBasics:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        for command in ["runs", "show", "compare", "demo"]:
            assert command in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "plainbench" in result.output
