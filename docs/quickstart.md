# PlainBench Quick Start

Five minutes from install to comparing designs under infrastructure you
haven't deployed.

## Install

```bash
git clone https://github.com/strugglingcomic/plainbench.git
cd plainbench
pip install -e .
```

Requires Python 3.8+. Runtime dependencies are `psutil` and `click`.

## 1. See the point

```bash
plainbench demo
```

Runs three designs (N+1 queries, batched query, warm cache) under three
infrastructure assumptions and prints the winner matrix. Takes ~15 seconds,
needs no infrastructure.

## 2. Compare two implementations

```python
import heapq, random
from plainbench import compare

data = [random.random() for _ in range(50_000)]

result = compare({
    "full_sort": lambda: sorted(data)[:10],
    "heapq_nsmallest": lambda: heapq.nsmallest(10, data),
})
result.print()

print(result.fastest)                       # "heapq_nsmallest"
print(result.speedup("heapq_nsmallest"))    # e.g. 11.7
print(result["full_sort"].mean)             # seconds, float
```

`compare()` interleaves candidates round-robin and pauses GC during timed
calls. Options: `runs=10`, `warmup=2`, `args=(...)`, `kwargs={...}`.

## 3. Add infrastructure assumptions

Mock datastores speak the client APIs you already use, backed by SQLite,
with per-operation latencies plus a network round trip for the chosen
profile (`in_process`, `same_host`, `same_zone`, `same_region`,
`cross_region`, `cross_continent`):

```python
from plainbench import compare_profiles
from plainbench.mocks import MockRedis

def read_one_by_one(profile):
    redis = MockRedis(database="cache.db", profile=profile)
    try:
        return [redis.get(f"user:{i}") for i in range(20)]
    finally:
        redis.close()

def read_pipelined(profile):
    redis = MockRedis(database="cache.db", profile=profile)
    try:
        with redis.pipeline() as pipe:
            for i in range(20):
                pipe.get(f"user:{i}")
            return pipe.execute()
    finally:
        redis.close()

compare_profiles(
    {"one_by_one": read_one_by_one, "pipelined": read_pipelined},
    profiles=["in_process", "same_zone", "cross_region"],
).print()
```

See [mock-datastores.md](mock-datastores.md) for the Postgres and Kafka
mocks, decorator injection, and custom latencies.

## 4. Track results over time

```python
from plainbench import benchmark

@benchmark(name="sum_squares", runs=10, warmup=3)
def sum_squares(n=100_000):
    return sum(i * i for i in range(n))

sum_squares()   # every measurement stored in ./benchmarks.db
```

Inspect and compare from the CLI:

```bash
plainbench runs             # list stored runs
plainbench show             # stats for the latest run
plainbench show --run-id 3
plainbench compare 1 2      # exit code 1 if a significant regression
```

Set `PLAINBENCH_DATABASE` or pass `--database/-d` to use a different file.

Programmatic access:

```python
from plainbench import BenchmarkDatabase
from plainbench.analysis import compare_runs, detect_regressions

with BenchmarkDatabase("./benchmarks.db") as db:
    run = db.get_latest_run()
    print(db.get_run_wall_times(run.run_id))

for c in compare_runs("./benchmarks.db", baseline_run_id=1, current_run_id=2):
    print(c.benchmark_name, f"{c.change:+.1%}", c.is_regression())
```

## 5. Benchmark shell commands

```python
from plainbench.shell import benchmark_shell

result = benchmark_shell("gzip -9 < big.log > /dev/null", runs=5, warmup=1)
print(result.mean_time, result.stddev_time, result.peak_memory)
```

## Decorator options

```python
@benchmark(
    name="my_bench",            # default: function name
    warmup=3,                   # untimed iterations
    runs=10,                    # timed iterations
    metrics=["wall_time", "cpu_time", "python_memory"],
    isolation="minimal",        # or "moderate" (CPU pinning, GC), "maximum"
    disable_gc=True,
    store=True,                 # set False to skip the database
    database=None,              # default: ./benchmarks.db
)
```

Available metrics: `wall_time`, `cpu_time`, `python_memory` (tracemalloc),
`process_memory` (psutil), `disk_io` (platform-dependent).

## Next steps

- [examples/](../examples/) — runnable examples
- [mock-datastores.md](mock-datastores.md) — the mock layer in depth
- [research.md](research.md) — where the latency numbers come from
