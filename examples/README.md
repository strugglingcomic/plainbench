# PlainBench Examples

Each example is a standalone script. From the repository root:

```bash
plainbench demo                              # the flagship demo (start here)
python examples/compare_algorithms.py        # compare() on pure-Python code
python examples/infrastructure_profiles.py   # designs x infrastructure matrix
python examples/tracked_benchmark.py         # @benchmark + CLI history
```

| example | shows |
|---------|-------|
| `plainbench demo` | 3 designs (N+1 / batched / cached) × 3 infrastructure profiles; the winner flips as network latency grows. Source: `plainbench/demo.py`. |
| `compare_algorithms.py` | In-process A/B/C comparison with `compare()`: stats table, fastest, speedups. |
| `infrastructure_profiles.py` | `compare_profiles()` with `MockRedis`: chatty vs pipelined cache access from `in_process` to `cross_region`. |
| `tracked_benchmark.py` | `@benchmark` storing to SQLite, then `plainbench runs / show / compare` for history and regression gating. |
