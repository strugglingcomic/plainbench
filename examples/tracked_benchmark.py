"""
Track benchmark results over time with @benchmark and the CLI.

Each call of a decorated function stores its measurements in a local SQLite
database (./benchmarks.db by default), so you can compare runs across code
changes and catch regressions.

Run:
    python examples/tracked_benchmark.py
    plainbench runs
    plainbench show
    plainbench compare 1 2   # after a second run; exit code 1 on regression
"""

from plainbench import benchmark


@benchmark(name="sum_of_squares", runs=10, warmup=3)
def sum_of_squares(n=200_000):
    return sum(i * i for i in range(n))


@benchmark(name="join_strings", runs=10, warmup=3)
def join_strings(n=20_000):
    return ",".join(str(i) for i in range(n))


if __name__ == "__main__":
    sum_of_squares()
    join_strings()
    print("Two benchmarks stored in ./benchmarks.db")
    print("Inspect them with: plainbench runs / plainbench show")
