"""
In-process comparison of alternative implementations.

This is the front door of PlainBench: hand it two or more callables that do
the same job, and it measures them back-to-back and tells you which one wins
and by how much.

    from plainbench import compare

    result = compare({
        "sorted_builtin": lambda: sorted(data),
        "heapq_nsmallest": lambda: heapq.nsmallest(len(data), data),
    })
    result.print()

Combined with the mock datastores in plainbench.mocks, compare_profiles()
answers the bigger question: which *design* wins under which infrastructure
assumptions — without deploying any infrastructure.
"""

import gc
import math
import statistics
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence


def format_time(seconds: float) -> str:
    """Render a duration with a sensible unit (ns/µs/ms/s)."""
    if seconds < 1e-6:
        return f"{seconds * 1e9:.0f}ns"
    if seconds < 1e-3:
        return f"{seconds * 1e6:.1f}µs"
    if seconds < 1.0:
        return f"{seconds * 1e3:.2f}ms"
    return f"{seconds:.3f}s"


@dataclass
class CandidateStats:
    """Timing statistics for one candidate in a comparison."""

    name: str
    times: List[float]

    @property
    def runs(self) -> int:
        return len(self.times)

    @property
    def mean(self) -> float:
        return statistics.fmean(self.times)

    @property
    def median(self) -> float:
        return statistics.median(self.times)

    @property
    def stddev(self) -> float:
        return statistics.stdev(self.times) if len(self.times) > 1 else 0.0

    @property
    def min(self) -> float:
        return min(self.times)

    @property
    def max(self) -> float:
        return max(self.times)

    def percentile(self, p: float) -> float:
        """Nearest-rank percentile of the measured times."""
        ordered = sorted(self.times)
        rank = max(1, math.ceil(p / 100 * len(ordered)))
        return ordered[rank - 1]

    def __repr__(self) -> str:
        return (
            f"CandidateStats({self.name!r}, mean={format_time(self.mean)}, "
            f"stddev={format_time(self.stddev)}, runs={self.runs})"
        )


class ComparisonResult:
    """Result of compare(): per-candidate stats plus ranking helpers."""

    def __init__(self, candidates: "Dict[str, CandidateStats]"):
        self.candidates = candidates

    def __getitem__(self, name: str) -> CandidateStats:
        return self.candidates[name]

    def __iter__(self):
        return iter(self.candidates.values())

    @property
    def fastest(self) -> str:
        """Name of the candidate with the lowest mean time."""
        return min(self.candidates.values(), key=lambda c: c.mean).name

    @property
    def slowest(self) -> str:
        """Name of the candidate with the highest mean time."""
        return max(self.candidates.values(), key=lambda c: c.mean).name

    def speedup(self, name: str, over: Optional[str] = None) -> float:
        """
        How many times faster `name` is than `over` (default: the slowest).

        A value of 2.0 means `name` takes half the time of `over`.
        """
        over = over or self.slowest
        return self.candidates[over].mean / self.candidates[name].mean

    def table(self) -> str:
        """Format the comparison as a plain-text table, fastest first."""
        ranked = sorted(self.candidates.values(), key=lambda c: c.mean)
        best = ranked[0]
        headers = ["candidate", "mean", "stddev", "min", "max", "vs fastest"]
        rows = []
        for c in ranked:
            relative = "fastest" if c is best else f"{c.mean / best.mean:.2f}x slower"
            rows.append(
                [
                    c.name,
                    format_time(c.mean),
                    format_time(c.stddev),
                    format_time(c.min),
                    format_time(c.max),
                    relative,
                ]
            )
        return _render_table(headers, rows)

    def print(self) -> None:
        """Print the comparison table to stdout."""
        print(self.table())

    def __repr__(self) -> str:
        return f"ComparisonResult({list(self.candidates)}, fastest={self.fastest!r})"


def compare(
    candidates: Dict[str, Callable[..., Any]],
    *,
    runs: int = 10,
    warmup: int = 2,
    args: Sequence[Any] = (),
    kwargs: Optional[Dict[str, Any]] = None,
) -> ComparisonResult:
    """
    Benchmark several callables against each other, in-process.

    Candidates are measured in interleaved rounds (A, B, C, A, B, C, ...)
    rather than back-to-back blocks, so slow drift in machine load biases
    all candidates equally. Garbage collection is paused during each timed
    call.

    Args:
        candidates: Mapping of display name -> zero-or-more-arg callable.
            All candidates are called with the same args/kwargs.
        runs: Measured iterations per candidate.
        warmup: Untimed iterations per candidate before measuring.
        args: Positional arguments passed to every candidate.
        kwargs: Keyword arguments passed to every candidate.

    Returns:
        ComparisonResult with per-candidate stats and ranking helpers.
    """
    if len(candidates) < 2:
        raise ValueError("compare() needs at least two candidates")
    if runs <= 0:
        raise ValueError(f"runs must be > 0, got {runs}")
    if warmup < 0:
        raise ValueError(f"warmup must be >= 0, got {warmup}")
    kwargs = kwargs or {}

    for _ in range(warmup):
        for func in candidates.values():
            func(*args, **kwargs)

    times: Dict[str, List[float]] = {name: [] for name in candidates}
    for _ in range(runs):
        for name, func in candidates.items():
            gc.collect()
            gc_was_enabled = gc.isenabled()
            gc.disable()
            try:
                start = time.perf_counter()
                func(*args, **kwargs)
                times[name].append(time.perf_counter() - start)
            finally:
                if gc_was_enabled:
                    gc.enable()

    return ComparisonResult(
        {name: CandidateStats(name, measured) for name, measured in times.items()}
    )


class ProfileComparison:
    """Result of compare_profiles(): a candidates × profiles matrix."""

    def __init__(self, results: "Dict[str, ComparisonResult]"):
        # profile name -> ComparisonResult
        self.results = results

    def __getitem__(self, profile: str) -> ComparisonResult:
        return self.results[profile]

    @property
    def profiles(self) -> List[str]:
        return list(self.results)

    def winners(self) -> Dict[str, str]:
        """Fastest candidate per profile."""
        return {profile: result.fastest for profile, result in self.results.items()}

    def table(self) -> str:
        """Format mean times as a candidates × profiles matrix, winners starred."""
        first = next(iter(self.results.values()))
        names = list(first.candidates)
        headers = ["candidate"] + self.profiles
        rows = []
        for name in names:
            row = [name]
            for profile in self.profiles:
                result = self.results[profile]
                cell = format_time(result[name].mean)
                if result.fastest == name:
                    cell += " *"
                row.append(cell)
            rows.append(row)
        legend = "* fastest for that profile"
        return _render_table(headers, rows) + "\n" + legend

    def print(self) -> None:
        """Print the matrix table to stdout."""
        print(self.table())

    def __repr__(self) -> str:
        return f"ProfileComparison(profiles={self.profiles}, winners={self.winners()})"


def compare_profiles(
    candidates: Dict[str, Callable[[str], Any]],
    profiles: Iterable[str] = ("in_process", "same_zone", "cross_region"),
    *,
    runs: int = 5,
    warmup: int = 1,
) -> ProfileComparison:
    """
    Benchmark competing designs under different infrastructure assumptions.

    Each candidate is a callable taking a profile name (e.g. 'same_zone');
    it should build its mock datastores with that profile and run the
    workload. See plainbench.mocks.NETWORK_PROFILES for available profiles.

    Args:
        candidates: Mapping of design name -> callable(profile).
        profiles: Infrastructure profiles to sweep over.
        runs: Measured iterations per candidate per profile.
        warmup: Untimed iterations per candidate per profile.

    Returns:
        ProfileComparison: a candidates × profiles matrix of timings.

    Example:
        def n_plus_one(profile):
            with MockPostgresConnection(profile=profile) as db:
                ...  # one query per row

        def batched(profile):
            with MockPostgresConnection(profile=profile) as db:
                ...  # single JOIN

        compare_profiles({"n_plus_one": n_plus_one, "batched": batched}).print()
    """
    results = {}
    for profile in profiles:
        bound = {
            name: _bind_profile(func, profile) for name, func in candidates.items()
        }
        results[profile] = compare(bound, runs=runs, warmup=warmup)
    return ProfileComparison(results)


def _bind_profile(func: Callable[[str], Any], profile: str) -> Callable[[], Any]:
    def call() -> Any:
        return func(profile)

    return call


def _render_table(headers: List[str], rows: List[List[str]]) -> str:
    """Minimal fixed-width plain-text table."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def render_row(cells: List[str]) -> str:
        # First column left-aligned, the rest right-aligned
        parts = [cells[0].ljust(widths[0])]
        parts += [cell.rjust(widths[i + 1]) for i, cell in enumerate(cells[1:])]
        return "  ".join(parts).rstrip()

    lines = [render_row(headers)]
    lines.append("  ".join("-" * w for w in widths))
    lines.extend(render_row(row) for row in rows)
    return "\n".join(lines)
