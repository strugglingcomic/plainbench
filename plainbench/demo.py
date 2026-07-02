"""
The PlainBench flagship demo.

Three designs for the same job — render order stats for 15 users:

  n_plus_one   one query per user           (15 database round trips)
  batched      one GROUP BY query for all   (2 database round trips)
  cached       one warm Redis GET per user  (15 cache round trips)

On your laptop, with the database in-process, all three are sub-millisecond
and indistinguishable. PlainBench re-runs the same code under realistic
network latency profiles (same availability zone, cross-region) using
SQLite-backed mock datastores — no Postgres, no Redis, no deployment — and
shows you where the design choice starts to matter, and by how much.

Run it:

    python -m plainbench.demo
    # or, after pip install:
    plainbench demo
"""

import random
import tempfile
from pathlib import Path

from plainbench.comparison import ProfileComparison, compare, format_time
from plainbench.mocks import MockPostgresConnection, MockRedis

USERS = 15
ORDERS_PER_USER = 40
PROFILES = ["in_process", "same_zone", "cross_region"]


def seed(workdir: Path) -> None:
    """Create the shared datasets: an orders table and a warm cache."""
    rng = random.Random(42)

    with MockPostgresConnection(database=str(workdir / "pg.db")) as db:
        cursor = db.cursor()
        cursor.execute(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL)"
        )
        cursor.execute("CREATE INDEX idx_orders_user ON orders(user_id)")
        for user_id in range(1, USERS + 1):
            for _ in range(ORDERS_PER_USER):
                cursor.execute(
                    "INSERT INTO orders (user_id, amount) VALUES (?, ?)",
                    (user_id, round(rng.uniform(5, 500), 2)),
                )
        db.commit()

        # Warm the cache with precomputed stats (the cache's best case)
        redis = MockRedis(database=str(workdir / "redis.db"))
        for user_id in range(1, USERS + 1):
            cursor.execute(
                "SELECT COUNT(*), SUM(amount) FROM orders WHERE user_id = ?",
                (user_id,),
            )
            count, total = cursor.fetchone()
            redis.set(f"user:{user_id}:stats", f"{count}:{total:.2f}")
        redis.close()


def n_plus_one(workdir: Path, profile: str) -> list:
    """One query per user: simple code, one round trip per user."""
    with MockPostgresConnection(database=str(workdir / "pg.db"), profile=profile) as db:
        cursor = db.cursor()
        stats = []
        for user_id in range(1, USERS + 1):
            cursor.execute(
                "SELECT COUNT(*), SUM(amount) FROM orders WHERE user_id = ?",
                (user_id,),
            )
            stats.append(cursor.fetchone())
        return stats


def batched(workdir: Path, profile: str) -> list:
    """One GROUP BY query for all users: two round trips total."""
    with MockPostgresConnection(database=str(workdir / "pg.db"), profile=profile) as db:
        cursor = db.cursor()
        cursor.execute(
            "SELECT user_id, COUNT(*), SUM(amount) FROM orders "
            f"WHERE user_id <= {USERS} GROUP BY user_id"
        )
        return cursor.fetchall()


def cached(workdir: Path, profile: str) -> list:
    """One warm Redis GET per user: fast per-op, still one round trip each."""
    redis = MockRedis(database=str(workdir / "redis.db"), profile=profile)
    try:
        return [redis.get(f"user:{user_id}:stats") for user_id in range(1, USERS + 1)]
    finally:
        redis.close()


def run(runs: int = 3, warmup: int = 1) -> ProfileComparison:
    """Run the demo comparison and return the profile matrix."""
    with tempfile.TemporaryDirectory(prefix="plainbench-demo-") as tmp:
        workdir = Path(tmp)
        seed(workdir)

        designs = {
            "n_plus_one": n_plus_one,
            "batched": batched,
            "cached": cached,
        }

        results = {}
        for profile in PROFILES:
            print(f"  measuring under {profile} ...")
            results[profile] = compare(
                {
                    name: (lambda d=design, p=profile: d(workdir, p))
                    for name, design in designs.items()
                },
                runs=runs,
                warmup=warmup,
            )
        return ProfileComparison(results)


def main() -> None:
    print(__doc__.split("Run it:")[0])
    print(f"Comparing 3 designs x {len(PROFILES)} infrastructure profiles ...")
    matrix = run()

    print()
    matrix.print()
    print()

    # Spell out the punchline with real numbers from this machine
    zone, region = matrix["same_zone"], matrix["cross_region"]
    print("What this tells you:")
    print(
        f"  - In-process, the designs are within noise of each other "
        f"(all ~{format_time(matrix['in_process'][matrix['in_process'].fastest].mean)})."
    )
    print(
        f"  - In the same zone, batching is already "
        f"{zone.speedup('batched', over='n_plus_one'):.1f}x faster than N+1 queries."
    )
    print(
        f"  - Cross-region, batching wins by "
        f"{region.speedup('batched', over='n_plus_one'):.0f}x over N+1 — and even a "
        f"100%-hit cache is {region.speedup('batched', over='cached'):.1f}x slower, "
        f"because round trips, not per-op speed, dominate."
    )
    print()
    print(
        "No Postgres, no Redis, no deployment: SQLite-backed mocks with "
        "realistic latency profiles, measured on this machine just now."
    )


if __name__ == "__main__":
    main()
