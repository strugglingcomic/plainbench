# Development

## Setup

```bash
pip install -e ".[dev]"
pytest              # full suite, a few seconds
ruff check .
```

## What's where

- `plainbench/comparison.py` — `compare()` / `compare_profiles()`, the primary API
- `plainbench/mocks/` — SQLite-backed Postgres/Redis/Kafka mocks; latency
  profiles live in `mocks/base.py` (`NETWORK_PROFILES`, `LatencyConfig`)
- `plainbench/demo.py` — the flagship demo (`plainbench demo`)
- `plainbench/decorators/` — `@benchmark`, stored measurements
- `plainbench/storage/` — SQLite schema and queries
- `plainbench/analysis/` — cross-run comparison, Welch's t-test, regressions
- `plainbench/cli/main.py` — `runs` / `show` / `compare` / `demo`
- `plainbench/shell/`, `plainbench/metrics/`, `plainbench/isolation/` —
  shell benchmarking, metric collectors, isolation strategies

## Principles

1. **Local first**: a laptop and SQLite are the only requirements. New
   features must not add infrastructure or heavyweight dependencies.
2. **Comparison over absolute numbers**: the product is "A vs B under
   assumption X", not microsecond-perfect measurements.
3. **Honest tests**: no stub tests that pass while asserting nothing. If a
   feature isn't tested, it isn't claimed.
4. **Small surface**: prefer improving `compare()` / profiles / mocks over
   adding new subsystems.

## Known gaps / ideas

- Mock latency model covers round trips and typical per-op costs, not
  contention or tail behavior under load.
- `compare()` measures wall time only; memory comparison could reuse the
  existing metric collectors.
- A `plainbench export` command (JSON/CSV) would help CI dashboards.
