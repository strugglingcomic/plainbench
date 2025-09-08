# Project: **PlainBench** — a single-binary, SQLite-backed sandbox

*MIT License - A benchmarking and fault injection framework for SQLite-backed queue systems*

## 1) Why SQLite for the queue too?

* **Zero infra, one file per subsystem.** Separate DB files for the **queue** and the **mock app DB** mean write locks in one don't stall the other. SQLite's WAL mode gives many readers + one writer concurrently, which is perfect for a local sandbox. ([SQLite][1])
* **Modern SQLite features** (CTEs + `RETURNING` + UPSERT) let us implement safe "claim/ack/nack" without exotic locking. ([SQLite][2])
* **Known constraints** are fine for our use case: one writer at a time, serialized writes, WAL on local disk only. We'll design around those. ([Oldmoe's blog][3], [SQLite][1])

Also worth noting: plenty of OSS proves this pattern is viable for embedded job queues (we'll go further by adding lanes, fault injection, and metrics out of the box): e.g., **goqite**, **backlite**, **persist-queue**, **litequeue**, **sqliteq**, **plainjob**. ([maragudk.github.io][4], [GitHub][5], [Go Packages][6])

---

## 2) High-level architecture (all local)

```
plainbench (single binary)
├─ queue.db       # SQLite file for topics, messages, leases, metrics cache (optional)
├─ app.db         # SQLite file for your "mock application DB"
├─ faults/        # latency + failure injector wrapping all queue and DB ops
├─ ingest/        # JSONL/CSV replay; synthetic generators
├─ tui/           # terminal dashboard (depths, rates, p50/p95/p99)
└─ cli/           # plainbench ... commands
```

**SQLite settings (each DB separately):**

* `PRAGMA journal_mode=WAL;` – concurrent readers & writer, faster commits.
* `PRAGMA synchronous=NORMAL` (or `FULL` when you want max durability).
* `PRAGMA busy_timeout=...` – friendlier behavior under write contention.
* Optional: tune WAL checkpointing (`wal_autocheckpoint`, manual checkpoints). ([SQLite][1])

---

## 3) Queue data model (in SQLite)

### Tables

```sql
-- Topic metadata
CREATE TABLE topics (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);

-- Messages
CREATE TABLE messages (
  id INTEGER PRIMARY KEY,
  topic_id INTEGER NOT NULL REFERENCES topics(id),
  lane TEXT NOT NULL DEFAULT 'normal',
  priority INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK(status IN ('ready','leased','done','dead')),
  visible_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  lease_until DATETIME,               -- visibility timeout/leasing
  consumer_id TEXT,                   -- which worker holds the lease
  attempts INTEGER NOT NULL DEFAULT 0,
  headers TEXT,                       -- JSON
  payload BLOB NOT NULL,
  inserted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  acked_at DATETIME
);

-- Backoff & dead-letter thresholds (optional)
CREATE TABLE topic_policies (
  topic_id INTEGER PRIMARY KEY REFERENCES topics(id),
  max_attempts INTEGER NOT NULL DEFAULT 10,
  base_backoff_ms INTEGER NOT NULL DEFAULT 1000
);

-- Helpful indexes
CREATE INDEX idx_ready_scan
  ON messages(topic_id, lane, status, visible_at, priority DESC, id);
CREATE INDEX idx_lease_scan
  ON messages(topic_id, status, lease_until);
```

### "Claim one" (visibility-timeout lease)

* Keep the transaction **tiny**: `BEGIN IMMEDIATE` → claim one row → commit.
* Use a CTE to pick one candidate, then `UPDATE … RETURNING` to atomically claim it.

```sql
-- in app code: BEGIN IMMEDIATE;
WITH candidate AS (
  SELECT id FROM messages
  WHERE topic_id = ?1
    AND lane = ?2
    AND status = 'ready'
    AND visible_at <= CURRENT_TIMESTAMP
  ORDER BY priority DESC, id
  LIMIT 1
)
UPDATE messages
   SET status = 'leased',
       lease_until = DATETIME('now', '+' || ?3 || ' seconds'),
       consumer_id = ?4
 WHERE id IN (SELECT id FROM candidate)
RETURNING *; -- gives the worker the claimed row
-- COMMIT;
```

This pattern relies on `RETURNING` (SQLite ≥ 3.35). If you must support older SQLite, select the id first, then update in the same transaction. ([SQLite][2])

### Ack / Nack / Dead-letter

```sql
-- ACK (only the leasing worker can ack)
UPDATE messages
   SET status='done', acked_at=CURRENT_TIMESTAMP
 WHERE id=?1 AND status='leased' AND consumer_id=?2
RETURNING *;

-- NACK (requeue with backoff)
UPDATE messages
   SET status='ready',
       attempts = attempts + 1,
       visible_at = DATETIME(
         'now',
         '+' || (SELECT base_backoff_ms FROM topic_policies WHERE topic_id=messages.topic_id)/1000
         || ' seconds'
       ),
       lease_until=NULL,
       consumer_id=NULL
 WHERE id=?1 AND status='leased' AND consumer_id=?2
RETURNING *;

-- Dead-letter when attempts exceed policy
UPDATE messages
   SET status='dead', lease_until=NULL, consumer_id=NULL
 WHERE id=?1 AND attempts >= (SELECT max_attempts FROM topic_policies WHERE topic_id=messages.topic_id)
RETURNING *;
```

**Why not `SELECT … FOR UPDATE`?** SQLite doesn't support it; your write txn is the lock. Using `BEGIN IMMEDIATE` ensures the claim is atomic without phantom competing writers. ([cockroachlabs.com][7], [SQLite][8])

---

## 4) Lanes, priority, fairness

* **Lane** is a column. Your scheduler decides which lane to attempt first (e.g., weighted: try `priority` lane 3× as often as `normal`).
* **Priority** is a simple integer; "claim one" orders by `priority DESC, id`.
* Enforce *at-least-once* delivery by design (possible redelivery on crash). That's standard for disk-backed queues and fine for a sandbox. (See SQLite-queue OSS patterns for reference.) ([GitHub][9], [maragudk.github.io][4])

---

## 5) Fault & latency injection (the fun part)

Wrap *every* queue and DB call through a small adapter:

```text
op() {
  maybe_sleep(latency_model)        # fixed / uniform / normal / tail-spike
  maybe_fail(error_rate)            # timeout / transient error / crash-after-commit
  return underlying_sqlite_call()
}
```

* **Latency models**: fixed, uniform, normal, and a "p95 spike" mode (probabilistic long tail).
* **Failures**: timeouts (`SQLITE_BUSY` after `busy_timeout`), transient errors, crashes right after a commit to test recovery.
* Seed the RNG so runs are reproducible (`--seed=...`).
* Simulate DB slowness too by putting the same wrappers around the **app.db** connector.

SQLite knobs you'll expose for the queue:
`busy_timeout` (or `PRAGMA busy_timeout`), `journal_mode=WAL`, `synchronous=NORMAL|FULL`, optional `wal_autocheckpoint`/explicit checkpointing to keep WAL sizes tame. ([SQLite][10])

---

## 6) Observability & tooling

* **Metrics**: write JSONL to disk (per topic/lane/worker): enqueue/dequeue/ack/nack rates; processing latency histograms; queue depth snapshots.
* **Events**: structured timeline (enqueue→claim→ack).
* **TUI**: top-like dashboard reading JSONL.
* Optional: store lightweight counters in `queue.db` as a cache, but keep the hot path append-only (JSONL) to avoid extra writes during contention.

---

## 7) CLI + config (example)

```yaml
# plainbench.yaml
sqlite:
  queue_file: "./queue.db"
  app_file: "./app.db"
  pragmas:
    journal_mode: WAL
    synchronous: NORMAL
    busy_timeout_ms: 5000
    wal_autocheckpoint_pages: 1000

topics:
  - name: orders
    lanes:
      - name: priority
        weight: 3
      - name: normal
        weight: 1
    max_attempts: 5
    base_backoff_ms: 750

faults:
  queue:
    latency: {type: p95_spike, base_ms: 5, p95_ms: 40, spike_prob: 0.01}
    error_rate: 0.002
  db:
    latency: {type: normal, mean_ms: 8, std_ms: 4}
    error_rate: 0.001

workers:
  - name: order-processor
    cmd: ["./bin/process-orders", "--mode", "mock"]
    concurrency: 8
```

CLI sketch:

```
plainbench init
plainbench topic create orders --lanes priority,normal
plainbench ingest jsonl fixtures/orders/*.jsonl --topic orders --lane normal
plainbench run --config plainbench.yaml
plainbench stats --topic orders
plainbench replay --from runs/2025-09-08.manifest.json
```

---

## 8) Implementation roadmap

### Phase 0 — Boot the queue engine

* SQLite connector with WAL + `busy_timeout`. Expose PRAGMAs in config. ([SQLite][1])
* Schema + migrations.
* Enqueue, claim (with `BEGIN IMMEDIATE` + CTE + `RETURNING`), ack, nack. ([SQLite][8])
* Weighted lane scheduler and basic worker loop (external process or in-proc plugin).
* Minimal metrics (JSONL) + `stats` CLI.

### Phase 1 — Faults + DB mock

* Fault adapter (latency models, error injections, seeded RNG).
* Stand-up **app.db** with fixtures + wrappers so you can simulate slow/failed "DB calls" too.
* TUI dashboard (depths, rates, p50/p95/p99).

### Phase 2 — Backoff, dead-letter, replay

* Exponential backoff option; dead-letter promotion; per-topic policies.
* Run recorder (config + seed + hashes) and replayer for A/B algorithm testing.

### Phase 3 — Polishing & perf hygiene

* Batch enqueue/ack APIs; **manual checkpoint** at idle (`PRAGMA wal_checkpoint`) to trim WAL growth; optional auto-checkpoint tuning. ([SQLite][1])
* "Lease sweeper" to return expired leases (where `lease_until < now`).
* Examples: order processing scenario with 1M JSONL messages.

---

## 9) Concurrency model & guardrails (SQLite specifics)

* **Single writer** means keep write transactions tiny (claim & ack are fast). Long compute happens **outside** the txn while the row is leased. ([Oldmoe's blog][3])
* Use `BEGIN IMMEDIATE` to avoid the race from "read then try to write." Expect an occasional `SQLITE_BUSY`; `busy_timeout` reduces spurious failures. ([SQLite][8])
* WAL is **local-disk only** (don't put `queue.db` on a network filesystem). ([SQLite][1])
* No `SELECT … FOR UPDATE`; leases via status+timestamps are the portable pattern. ([cockroachlabs.com][7])

---

## 10) API sketch (language-agnostic)

```text
Queue.open(db_path)
Topic.create(name, lanes[], max_attempts, base_backoff_ms)
Queue.enqueue(topic, lane, payload, priority=0, headers={}) -> id
Queue.claim(topic, lane, lease_seconds, consumer_id) -> Message | None
Queue.ack(id, consumer_id)
Queue.nack(id, consumer_id)
Queue.extend_lease(id, consumer_id, extra_seconds)
Queue.stats(topic) -> {depth_per_lane, rates, p50/p95/p99}
```

---

## 11) Known trade-offs (and why they're fine here)

* **"DB as queue" concerns** (contention, scalability) are real in production discussions, but this project is a *local sandbox* for DS&A prototyping and fault testing—so the simplicity wins. For balance, see both the anti-pattern arguments and practical SQL-queue write-ups. ([mikehadlow.blogspot.com][11], [Notch][12])

---

## 12) Pointers for your README / design doc

* WAL overview & concurrency (many readers/one writer; local FS only). ([SQLite][1])
* Transaction modes (`DEFERRED/IMMEDIATE/EXCLUSIVE`) and why we use IMMEDIATE for claim. ([SQLite][8])
* `RETURNING` for atomic claim/ack, and UPSERT for idempotent enqueue. ([SQLite][2])
* Busy handling (`sqlite3_busy_timeout` / `PRAGMA busy_timeout`). ([SQLite][10])
* Optional WAL checkpoint tuning. ([SQLite][1])

---

### Bonus: prior art to crib from (queue-only libs)

* **goqite** (Go, SQS-like semantics on SQLite). ([maragudk.github.io][4], [GitHub][13])
* **backlite** (Go, task queues + web UI on SQLite). ([GitHub][5])
* **persist-queue** (Python, SQLite & file queues). ([GitHub][9])
* **litequeue** (Python, zero deps). ([GitHub][14])
* **sqliteq** (Go). ([Go Packages][6])
* **plainjob** (TS/Bun, "15k jobs/s" claim). ([GitHub][15])

These confirm feasibility, but none bundle your **lanes + failure injector + TUI + DB-mock** together—that's where **PlainBench** will stand out.

If you want, I can turn this into a starter repo layout with migrations, the claim/ack SQL wired up, and a tiny worker loop to process 1M JSONL messages with artificial p95 spikes.

[1]: https://sqlite.org/wal.html?utm_source=chatgpt.com "Write-Ahead Logging - SQLite"
[2]: https://sqlite.org/lang_returning.html?utm_source=chatgpt.com "RETURNING - SQLite"
[3]: https://oldmoe.blog/2024/07/08/the-write-stuff-concurrent-write-transactions-in-sqlite/?utm_source=chatgpt.com "The Write Stuff: Concurrent Write Transactions in SQLite"
[4]: https://maragudk.github.io/goqite/?utm_source=chatgpt.com "goqite"
[5]: https://github.com/mikestefanello/backlite?utm_source=chatgpt.com "GitHub - mikestefanello/backlite: Type-safe, persistent, embedded task ..."
[6]: https://pkg.go.dev/github.com/goptics/sqliteq?utm_source=chatgpt.com "sqliteq package - github.com/goptics/sqliteq - Go Packages"
[7]: https://www.cockroachlabs.com/blog/select-for-update/?utm_source=chatgpt.com "What is SELECT FOR UPDATE in SQL (with examples)?"
[8]: https://sqlite.org/lang_transaction.html?utm_source=chatgpt.com "Transaction - SQLite"
[9]: https://github.com/peter-wangxu/persist-queue?utm_source=chatgpt.com "persist-queue - A thread-safe, disk-based queue for Python - GitHub"
[10]: https://sqlite.org/c3ref/busy_timeout.html?utm_source=chatgpt.com "Set A Busy Timeout - SQLite"
[11]: https://mikehadlow.blogspot.com/2012/04/database-as-queue-anti-pattern.html?utm_source=chatgpt.com "Code rant: The Database As Queue Anti-Pattern - Blogger"
[12]: https://wearenotch.com/blog/practical-queueing-using-sql-part-1-rationale-and-general-design/?utm_source=chatgpt.com "Practical Queueing Using SQL (Part 1) - Notch"
[13]: https://github.com/maragudk/goqite/blob/main/README.md?utm_source=chatgpt.com "goqite/README.md at main · maragudk/goqite · GitHub"
[14]: https://github.com/ianozsvald/litequeue?utm_source=chatgpt.com "GitHub - ianozsvald/litequeue: Batteries-included lightweight queueing ..."
[15]: https://github.com/justplainstuff/plainjob?utm_source=chatgpt.com "GitHub - justplainstuff/plainjob: SQLite-backed job queue processing ..."