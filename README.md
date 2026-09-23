# PlainBench

**Benchmark your system designs against infrastructure you haven't deployed.**

[![CI](https://github.com/strugglingcomic/plainbench/actions/workflows/ci.yml/badge.svg)](https://github.com/strugglingcomic/plainbench/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

PlainBench is a simple, local-first benchmarking library for one job: **comparing
alternatives** — algorithms, query strategies, caching designs — and seeing how the
comparison changes under different infrastructure assumptions. Everything runs on
your laptop. There is nothing to deploy: datastores (Postgres, Redis, Kafka) are
SQLite-backed mocks with realistic, configurable latency profiles, and results are
stored in a single local SQLite file.

## The demo

```bash
pip install -e . && plainbench demo    # ~15 seconds, no infrastructure required
```

Three designs for the same job — render order stats for 15 users:

- `n_plus_one` — one query per user (15 database round trips)
- `batched` — one GROUP BY query for everyone (2 round trips)
- `cached` — one warm Redis GET per user (15 cache round trips)

PlainBench runs the identical code under three infrastructure assumptions and
prints the matrix (real output, measured on a laptop):

```
candidate   in_process  same_zone  cross_region
----------  ----------  ---------  ------------
n_plus_one     882.0µs    36.38ms        1.833s
batched      597.9µs *   3.69ms *    124.36ms *
cached         646.0µs    18.21ms      907.68ms
* fastest for that profile

What this tells you:
  - In-process, the designs are within noise of each other (all ~600µs).
  - In the same zone, batching is already 9.9x faster than N+1 queries.
  - Cross-region, batching wins by 15x over N+1 — and even a 100%-hit cache
    is 7.3x slower, because round trips, not per-op speed, dominate.
```

On your laptop the three designs are indistinguishable. Add a real network and the
design choice is worth 15x — and you learned that without provisioning a database,
a cache, or a second region.

## Install

```bash
git clone https://github.com/strugglingcomic/plainbench.git
cd plainbench
pip install -e .
```

Dependencies: `psutil` and `click`. That's it.

## Compare implementations

The front door is `compare()` — hand it callables that do the same job:

```python
import heapq, random
from plainbench import compare

data = [random.random() for _ in range(50_000)]

result = compare({
    "full_sort": lambda: sorted(data)[:10],
    "heapq_nsmallest": lambda: heapq.nsmallest(10, data),
})
result.print()
```

```
candidate           mean   stddev      min      max     vs fastest
---------------  -------  -------  -------  -------  -------------
heapq_nsmallest  763.7µs   78.3µs  689.9µs  871.0µs        fastest
full_sort         8.90ms  800.7µs   8.27ms  10.25ms  11.66x slower
```

Candidates are measured in interleaved rounds (A, B, A, B, ...) with GC paused
during timed calls, so background drift biases everyone equally.

## Compare designs across infrastructure assumptions

The mock datastores accept a `profile` describing where the real system would
live. Each mock operation then costs its typical processing latency plus that
profile's network round trip:

| profile           | round trip | typical situation                |
|-------------------|-----------:|----------------------------------|
| `in_process`      |        0ms | no network, raw mock speed       |
| `same_host`       |     0.05ms | loopback / unix socket           |
| `same_zone`       |      0.5ms | same availability zone           |
| `same_region`     |        2ms | cross-AZ within a region         |
| `cross_region`    |       60ms | e.g. us-east ↔ us-west           |
| `cross_continent` |      150ms | e.g. us ↔ eu/apac                |

Write each design as a function of the profile, and sweep:

```python
from plainbench import compare_profiles
from plainbench.mocks import MockPostgresConnection

def n_plus_one(profile):
    with MockPostgresConnection(database="orders.db", profile=profile) as db:
        cursor = db.cursor()
        return [
            cursor.execute("SELECT SUM(amount) FROM orders WHERE user_id = ?", (uid,)).fetchone()
            for uid in range(1, 16)
        ]

def batched(profile):
    with MockPostgresConnection(database="orders.db", profile=profile) as db:
        cursor = db.cursor()
        cursor.execute("SELECT user_id, SUM(amount) FROM orders GROUP BY user_id")
        return cursor.fetchall()

compare_profiles(
    {"n_plus_one": n_plus_one, "batched": batched},
    profiles=["in_process", "same_zone", "cross_region"],
).print()
```

The mocks speak the client APIs you already use — `MockPostgresConnection` is
DB-API/psycopg2-shaped (with Postgres→SQLite SQL translation), `MockRedis` is
redis-py-shaped, `MockKafkaProducer`/`MockKafkaConsumer` are kafka-python-shaped —
so benchmark code reads like production code. Decorator injection is available
too:

```python
from plainbench import use_mock_redis

@use_mock_redis(profile="same_zone")
def cache_reads(redis):
    return [redis.get(f"user:{i}") for i in range(100)]
```

Latency defaults are based on published figures for production systems
(see [docs/research.md](docs/research.md)) and every number is overridable via
`custom_latencies={...}` or a fully custom `LatencyConfig`.

## Track results over time

`@benchmark` measures a function (warmup + timed runs, GC control, optional CPU
pinning) and stores every measurement in a local SQLite database:

```python
from plainbench import benchmark

@benchmark(name="ingest", runs=20, warmup=3)
def ingest():
    ...

ingest()  # measurements saved to ./benchmarks.db
```

Then inspect and compare runs from the CLI:

```bash
plainbench runs                  # list stored runs
plainbench show                  # stats for the latest run
plainbench compare 1 2           # baseline vs current; exit code 1 on regression
```

`plainbench compare` uses Welch's t-test so noise isn't reported as a regression,
which makes it usable as a CI gate.

Shell commands can be benchmarked black-box too:

```python
from plainbench.shell import benchmark_shell

result = benchmark_shell("sqlite3 test.db 'SELECT count(*) FROM users'", runs=10)
print(result.mean_time, result.stddev_time)
```

## What PlainBench is (and isn't)

**It is** a fast way to get *realistic comparative* numbers: which design wins,
by roughly how much, and how that answer changes with your infrastructure
assumptions — before you commit to deploying anything.

**It isn't** a load tester or a substitute for measuring the real system. Mock
latencies model network round trips and typical per-operation costs; they don't
model contention, connection pool exhaustion, cache eviction, or tail latency
under load. Use PlainBench to choose between designs; validate the winner with
real infrastructure.

## Layout

```
plainbench/
├── comparison.py     # compare(), compare_profiles() — the front door
├── mocks/            # SQLite-backed Postgres/Redis/Kafka with latency profiles
├── decorators/       # @benchmark for tracked, stored measurements
├── shell/            # black-box shell command benchmarking
├── storage/          # single-file SQLite result store
├── analysis/         # cross-run comparison and regression detection
├── isolation/        # GC control, CPU pinning, optional cgroups/Docker
├── metrics/          # wall/cpu time, Python heap, process memory, disk I/O
├── demo.py           # `plainbench demo`
└── cli/              # runs / show / compare / demo
```

## Development

```bash
pip install -e ".[dev]"
pytest            # ~160 tests, a few seconds
ruff check .
```

## License

MIT — see [LICENSE](LICENSE).
