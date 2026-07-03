"""Unit tests for the @benchmark decorator."""

import asyncio

import pytest

from plainbench import benchmark
from plainbench.storage.database import BenchmarkDatabase


class TestBenchmarkDecorator:
    def test_returns_function_result(self, tmp_path):
        @benchmark(runs=2, warmup=0, database=str(tmp_path / "b.db"))
        def add(a, b):
            return a + b

        assert add(2, 3) == 5

    def test_stores_measurements(self, tmp_path):
        db_path = str(tmp_path / "b.db")

        @benchmark(name="stored", runs=4, warmup=1, database=db_path)
        def work():
            return sum(range(1000))

        work()

        db = BenchmarkDatabase(db_path)
        db.initialize()
        try:
            run = db.get_latest_run()
            assert run is not None
            wall_times = db.get_run_wall_times(run.run_id)
            assert list(wall_times) == ["stored"]
            assert len(wall_times["stored"]) == 4
            assert run.configurations["runs"] == "4"
        finally:
            db.close()

    def test_store_false_skips_database(self, tmp_path):
        db_path = tmp_path / "b.db"

        @benchmark(runs=2, warmup=0, store=False, database=str(db_path))
        def work():
            return 1

        work()
        assert not db_path.exists()

    def test_defaults_to_function_name(self):
        @benchmark(runs=1, warmup=0, store=False)
        def my_function():
            return 1

        assert my_function._benchmark_name == "my_function"
        assert my_function._is_benchmark

    def test_invalid_parameters_raise_at_call_time(self):
        @benchmark(runs=0, store=False)
        def bad_runs():
            return 1

        @benchmark(warmup=-1, store=False)
        def bad_warmup():
            return 1

        with pytest.raises(ValueError, match="runs"):
            bad_runs()
        with pytest.raises(ValueError, match="warmup"):
            bad_warmup()

    def test_async_function(self, tmp_path):
        db_path = str(tmp_path / "b.db")

        @benchmark(name="async_work", runs=2, warmup=0, database=db_path)
        async def work():
            await asyncio.sleep(0)
            return 42

        assert asyncio.run(work()) == 42

        db = BenchmarkDatabase(db_path)
        db.initialize()
        try:
            run = db.get_latest_run()
            assert len(db.get_run_wall_times(run.run_id)["async_work"]) == 2
        finally:
            db.close()

    def test_metadata_config_attached(self):
        @benchmark(runs=7, warmup=2, metrics=["wall_time"], store=False)
        def work():
            return 1

        assert work._benchmark_config == {
            "warmup": 2,
            "runs": 7,
            "metrics": ["wall_time"],
            "isolation": "minimal",
        }
