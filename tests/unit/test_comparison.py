"""Unit tests for the compare() / compare_profiles() API."""

import time

import pytest

from plainbench.comparison import (
    CandidateStats,
    ProfileComparison,
    compare,
    compare_profiles,
    format_time,
)


def fast():
    return sum(range(100))


def slow():
    time.sleep(0.002)
    return sum(range(100))


class TestCompare:
    def test_identifies_fastest_and_slowest(self):
        result = compare({"fast": fast, "slow": slow}, runs=3, warmup=1)
        assert result.fastest == "fast"
        assert result.slowest == "slow"

    def test_speedup_relative_to_slowest(self):
        result = compare({"fast": fast, "slow": slow}, runs=3, warmup=1)
        assert result.speedup("fast") > 1.0
        assert result.speedup("fast", over="slow") == pytest.approx(
            result["slow"].mean / result["fast"].mean
        )

    def test_collects_requested_number_of_runs(self):
        result = compare({"a": fast, "b": fast}, runs=5, warmup=0)
        assert result["a"].runs == 5
        assert result["b"].runs == 5

    def test_passes_shared_args(self):
        result = compare(
            {"double": lambda x: x * 2, "square": lambda x: x * x},
            runs=2,
            warmup=0,
            args=(21,),
        )
        assert set(result.candidates) == {"double", "square"}

    def test_requires_two_candidates(self):
        with pytest.raises(ValueError, match="at least two"):
            compare({"only": fast}, runs=1)

    def test_rejects_bad_runs_and_warmup(self):
        with pytest.raises(ValueError, match="runs"):
            compare({"a": fast, "b": fast}, runs=0)
        with pytest.raises(ValueError, match="warmup"):
            compare({"a": fast, "b": fast}, runs=1, warmup=-1)

    def test_table_lists_all_candidates(self):
        result = compare({"fast": fast, "slow": slow}, runs=2, warmup=0)
        table = result.table()
        assert "fast" in table and "slow" in table
        assert "fastest" in table
        assert "slower" in table

    def test_iteration_yields_stats(self):
        result = compare({"a": fast, "b": fast}, runs=2, warmup=0)
        names = {stats.name for stats in result}
        assert names == {"a", "b"}


class TestCandidateStats:
    def test_statistics(self):
        stats = CandidateStats("x", [1.0, 2.0, 3.0, 4.0])
        assert stats.mean == 2.5
        assert stats.median == 2.5
        assert stats.min == 1.0
        assert stats.max == 4.0
        assert stats.stddev == pytest.approx(1.29099, rel=1e-4)
        assert stats.percentile(50) == 2.0
        assert stats.percentile(100) == 4.0

    def test_single_sample_has_zero_stddev(self):
        assert CandidateStats("x", [1.0]).stddev == 0.0


class TestCompareProfiles:
    def test_candidates_receive_each_profile(self):
        seen = []

        def design_a(profile):
            seen.append(("a", profile))

        def design_b(profile):
            seen.append(("b", profile))

        result = compare_profiles(
            {"a": design_a, "b": design_b},
            profiles=["in_process", "same_host"],
            runs=1,
            warmup=0,
        )
        assert isinstance(result, ProfileComparison)
        assert result.profiles == ["in_process", "same_host"]
        assert ("a", "in_process") in seen
        assert ("b", "same_host") in seen

    def test_winners_per_profile(self):
        def quick(profile):
            pass

        def slow_design(profile):
            time.sleep(0.002)

        result = compare_profiles(
            {"quick": quick, "slow": slow_design},
            profiles=["in_process"],
            runs=2,
            warmup=0,
        )
        assert result.winners() == {"in_process": "quick"}

    def test_matrix_table_contains_profiles_and_star(self):
        result = compare_profiles(
            {"a": lambda p: None, "b": lambda p: time.sleep(0.001)},
            profiles=["in_process", "same_host"],
            runs=1,
            warmup=0,
        )
        table = result.table()
        assert "in_process" in table and "same_host" in table
        assert "*" in table


class TestFormatTime:
    def test_units(self):
        assert format_time(5e-9) == "5ns"
        assert format_time(5e-6) == "5.0µs"
        assert format_time(5e-3) == "5.00ms"
        assert format_time(5.0) == "5.000s"
