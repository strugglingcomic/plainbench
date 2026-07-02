"""
Compare two cache-access designs under different infrastructure assumptions.

Reading 20 keys from Redis one GET at a time versus one pipeline. In-process
the difference is noise; once the cache is across a real network, the
pipelined design wins by roughly the number of round trips saved.

No Redis required: MockRedis is SQLite-backed with realistic latencies.

Run:
    python examples/infrastructure_profiles.py
"""

import tempfile
from pathlib import Path

from plainbench import compare_profiles
from plainbench.mocks import MockRedis

KEYS = 20
workdir = Path(tempfile.mkdtemp(prefix="plainbench-example-"))
CACHE_DB = str(workdir / "cache.db")


def seed():
    redis = MockRedis(database=CACHE_DB)
    for i in range(KEYS):
        redis.set(f"user:{i}", f"user-{i}-payload")
    redis.close()


def one_by_one(profile):
    redis = MockRedis(database=CACHE_DB, profile=profile)
    try:
        return [redis.get(f"user:{i}") for i in range(KEYS)]
    finally:
        redis.close()


def pipelined(profile):
    redis = MockRedis(database=CACHE_DB, profile=profile)
    try:
        with redis.pipeline() as pipe:
            for i in range(KEYS):
                pipe.get(f"user:{i}")
            return pipe.execute()
    finally:
        redis.close()


if __name__ == "__main__":
    seed()
    matrix = compare_profiles(
        {"one_by_one": one_by_one, "pipelined": pipelined},
        profiles=["in_process", "same_zone", "same_region", "cross_region"],
        runs=3,
        warmup=1,
    )
    matrix.print()
    print()
    region = matrix["cross_region"]
    print(
        f"cross_region: pipelining is "
        f"{region.speedup('pipelined', over='one_by_one'):.1f}x faster "
        f"({KEYS} round trips collapsed into 1)"
    )
