"""Unit tests for SQLite storage."""

from datetime import datetime

from plainbench.storage.database import BenchmarkDatabase
from plainbench.storage.models import BenchmarkRun, Environment, Measurement


def make_environment():
    return Environment(
        environment_id=None,
        python_version="3.11",
        platform="test",
        processor="test",
        cpu_count=4,
        memory_total=0,
        hostname="test",
        created_at=datetime.now(),
    )


class TestBenchmarkDatabase:
    def test_initialize_in_memory(self):
        db = BenchmarkDatabase(":memory:")
        db.initialize()
        assert db.conn is not None
        db.close()

    def test_initialize_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "bench.db"
        db = BenchmarkDatabase(str(path))
        db.initialize()
        db.close()
        assert path.exists()

    def test_environment_roundtrip(self):
        with BenchmarkDatabase(":memory:") as db:
            env_id = db.insert_environment(make_environment())
            env = db.get_environment(env_id)
            assert env.python_version == "3.11"
            assert env.cpu_count == 4

    def test_run_roundtrip_with_configurations(self):
        with BenchmarkDatabase(":memory:") as db:
            env_id = db.insert_environment(make_environment())
            run_id = db.insert_run(
                BenchmarkRun(
                    run_id=None,
                    timestamp=datetime.now(),
                    git_commit_hash="abc123",
                    git_branch="main",
                    git_is_dirty=False,
                    environment_id=env_id,
                    configurations={"runs": "10"},
                )
            )
            run = db.get_run(run_id)
            assert run.git_commit_hash == "abc123"
            assert run.configurations == {"runs": "10"}

    def test_get_or_create_benchmark_is_idempotent(self):
        with BenchmarkDatabase(":memory:") as db:
            first = db.get_or_create_benchmark("bench", "function")
            second = db.get_or_create_benchmark("bench", "function")
            assert first == second

    def test_store_benchmark_results_and_query_wall_times(self):
        class FakeMetric:
            def __init__(self, value):
                self.value = value

        with BenchmarkDatabase(":memory:") as db:
            run_id = db.store_benchmark_results(
                benchmark_name="stored",
                measurements=[
                    {"wall_time": FakeMetric(0.01)},
                    {"wall_time": FakeMetric(0.02)},
                ],
                metadata={"runs": "2"},
            )
            wall_times = db.get_run_wall_times(run_id)
            assert wall_times == {"stored": [0.01, 0.02]}

    def test_get_latest_run(self):
        with BenchmarkDatabase(":memory:") as db:
            assert db.get_latest_run() is None
            env_id = db.insert_environment(make_environment())
            for i in range(2):
                db.insert_run(
                    BenchmarkRun(
                        run_id=None,
                        timestamp=datetime(2026, 1, 1 + i),
                        git_commit_hash=None,
                        git_branch=None,
                        git_is_dirty=False,
                        environment_id=env_id,
                    )
                )
            assert db.get_latest_run().timestamp == datetime(2026, 1, 2)

    def test_measurements_filtered_by_run_and_benchmark(self):
        with BenchmarkDatabase(":memory:") as db:
            env_id = db.insert_environment(make_environment())
            run_id = db.insert_run(
                BenchmarkRun(
                    run_id=None,
                    timestamp=datetime.now(),
                    git_commit_hash=None,
                    git_branch=None,
                    git_is_dirty=False,
                    environment_id=env_id,
                )
            )
            bench_id = db.get_or_create_benchmark("m", "function")
            db.insert_measurement(
                Measurement(
                    measurement_id=None,
                    run_id=run_id,
                    benchmark_id=bench_id,
                    iteration=0,
                    wall_time=0.5,
                    cpu_time=None,
                    peak_memory=None,
                    current_memory=None,
                    read_bytes=None,
                    write_bytes=None,
                    exit_code=None,
                )
            )
            found = db.get_measurements(run_id=run_id, benchmark_id=bench_id)
            assert len(found) == 1
            assert found[0].wall_time == 0.5
            assert db.get_measurements(run_id=run_id + 999) == []
