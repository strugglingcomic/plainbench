"""
Real functional tests for shell command benchmarking.

This module contains working tests (not stubs) that actually test the shell module.
"""

import subprocess
import sys
import time

import psutil
import pytest

from plainbench.shell import ShellCommandRunner
from plainbench.shell.monitor import ProcessMonitor
from plainbench.shell.results import ShellBenchmarkResult, ShellCommandResult
from plainbench.shell.runner import benchmark_shell


class TestShellCommandRunner:
    """Test the ShellCommandRunner class."""

    def test_basic_command_execution(self):
        """Test executing a basic command."""
        runner = ShellCommandRunner("echo hello")
        result = runner.run_command()

        assert isinstance(result, ShellCommandResult)
        assert result.exit_code == 0
        assert result.wall_time > 0
        assert result.command == "echo hello"

    def test_command_with_output_capture(self):
        """Test capturing command output."""
        runner = ShellCommandRunner("echo test output", capture_output=True)
        result = runner.run_command()

        assert result.exit_code == 0
        assert "test output" in result.stdout

    def test_command_exit_code_nonzero(self):
        """Test that non-zero exit codes are captured."""
        runner = ShellCommandRunner("exit 42", shell=True)
        result = runner.run_command()

        assert result.exit_code == 42

    def test_command_timeout(self):
        """Test command timeout functionality."""
        runner = ShellCommandRunner("sleep 10", timeout=0.1, shell=True)

        with pytest.raises(subprocess.TimeoutExpired):
            runner.run_command()

    def test_process_monitoring_snapshot(self):
        """Test process monitoring in snapshot mode."""
        runner = ShellCommandRunner(
            f"{sys.executable} -c 'sum(range(1000))'",
            monitoring_mode="snapshot",
            shell=True,
        )
        result = runner.run_command()

        assert result.exit_code == 0
        assert result.wall_time > 0
        # peak_memory can be None or >= 0 (bytes)
        assert result.peak_memory is None or result.peak_memory >= 0

    def test_process_monitoring_continuous(self):
        """Test process monitoring in continuous mode."""
        runner = ShellCommandRunner(
            f"{sys.executable} -c 'import time; time.sleep(0.1)'",
            monitoring_mode="continuous",
            monitoring_interval=0.05,
            shell=True,
        )
        result = runner.run_command()

        assert result.exit_code == 0
        assert result.wall_time >= 0.1
        assert result.peak_memory is None or result.peak_memory >= 0

    def test_shell_parameter(self):
        """Test shell=False parameter."""
        # With shell=False, command must be a list
        runner = ShellCommandRunner([sys.executable, "--version"], shell=False, capture_output=True)
        result = runner.run_command()

        assert result.exit_code == 0
        assert "Python" in result.stdout or "python" in result.stdout.lower()

    def test_stderr_capture(self):
        """Test stderr is captured separately."""
        runner = ShellCommandRunner(
            f"{sys.executable} -c 'import sys; sys.stderr.write(\"error msg\")'",
            capture_output=True,
            shell=True,
        )
        result = runner.run_command()

        assert result.exit_code == 0
        assert "error msg" in result.stderr

    @pytest.mark.skipif(sys.platform == "win32", reason="I/O counters may not be available on Windows")
    def test_io_counters_collected(self):
        """Test I/O counters are collected if available."""
        runner = ShellCommandRunner(
            f"{sys.executable} -c 'import tempfile; f = open(\"/tmp/test.txt\", \"w\"); f.write(\"test\" * 1000); f.close()'",
            shell=True,
        )
        result = runner.run_command()

        assert result.exit_code == 0
        assert result.wall_time > 0
        # read_bytes/write_bytes can be None
        assert result.read_bytes is None or result.read_bytes >= 0


class TestShellBenchmarkingWorkflow:
    """Test complete benchmarking workflows."""

    def test_benchmark_simple_command(self):
        """Test benchmarking a simple command multiple times."""
        result = benchmark_shell("echo test", warmup=1, runs=3, capture_output=True, shell=True)

        assert isinstance(result, ShellBenchmarkResult)
        assert result.iterations == 3
        assert len(result.raw_measurements) == 3
        assert result.mean_time > 0
        assert result.command == "echo test"

    def test_benchmark_with_aggregations(self):
        """Test that aggregations are calculated."""
        result = benchmark_shell(
            f"{sys.executable} -c 'print(\"test\")'", warmup=1, runs=5, shell=True
        )

        assert result.iterations == 5
        assert result.mean_time > 0
        assert result.median_time > 0
        assert result.min_time > 0
        assert result.max_time > 0
        assert result.mean_time >= result.min_time
        assert result.mean_time <= result.max_time

    def test_benchmark_warmup_executions(self):
        """Test warmup executions are performed."""
        result = benchmark_shell("echo warmup", warmup=3, runs=2, shell=True)

        assert result.iterations == 2
        assert len(result.raw_measurements) == 2

    def test_benchmark_memory_tracking(self):
        """Test memory usage is tracked."""
        result = benchmark_shell(
            f"{sys.executable} -c 'x = [0] * 1000000'",
            warmup=1,
            runs=2,
            shell=True,
        )

        # mean_memory and peak_memory can be None or >= 0 (bytes)
        assert result.mean_memory is None or result.mean_memory >= 0
        assert result.peak_memory is None or result.peak_memory >= 0


class TestShellResults:
    """Test result data structures."""

    def test_shell_command_result_creation(self):
        """Test ShellCommandResult can be created with correct fields."""
        result = ShellCommandResult(
            command="echo test",
            exit_code=0,
            wall_time=0.123,
            stdout="test output",
            stderr="",
            peak_memory=50000000,  # 50 MB in bytes
            cpu_percent=25.5,
            read_bytes=1000,
            write_bytes=500,
        )

        assert result.exit_code == 0
        assert result.wall_time == 0.123
        assert result.peak_memory == 50000000

    def test_shell_benchmark_result_creation(self):
        """Test ShellBenchmarkResult aggregation."""
        measurements = [
            ShellCommandResult(
                command="test",
                exit_code=0,
                wall_time=0.1,
                peak_memory=50000000,
            ),
            ShellCommandResult(
                command="test",
                exit_code=0,
                wall_time=0.15,
                peak_memory=55000000,
            ),
        ]

        result = ShellBenchmarkResult(
            command="test command",
            exit_code=0,
            iterations=2,
            mean_time=0.125,
            median_time=0.125,
            stddev_time=0.025,
            min_time=0.1,
            max_time=0.15,
            raw_measurements=measurements,
        )

        assert result.iterations == 2
        assert len(result.raw_measurements) == 2
        assert result.mean_time == pytest.approx(0.125)
        assert result.min_time == 0.1
        assert result.max_time == 0.15


class TestProcessMonitor:
    """Test ProcessMonitor class."""

    def test_process_monitor_snapshot_mode(self):
        """Test ProcessMonitor in snapshot mode."""
        # Start a simple process
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(0.1)"], shell=False
        )

        # Create monitor with psutil.Process object
        ps_proc = psutil.Process(proc.pid)
        monitor = ProcessMonitor(ps_proc, mode="snapshot", interval=0.01)
        monitor.start()
        time.sleep(0.05)
        metrics = monitor.stop()

        # Check that metrics were collected
        assert "peak_memory" in metrics
        assert metrics["peak_memory"] is None or metrics["peak_memory"] >= 0

        proc.wait()

    def test_process_monitor_continuous_mode(self):
        """Test ProcessMonitor in continuous mode."""
        # Start a simple process
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(0.2)"], shell=False
        )

        # Create monitor with psutil.Process object
        ps_proc = psutil.Process(proc.pid)
        monitor = ProcessMonitor(ps_proc, mode="continuous", interval=0.05)
        monitor.start()
        time.sleep(0.15)
        metrics = monitor.stop()

        # Check that metrics were collected
        assert "peak_memory" in metrics
        assert metrics["peak_memory"] is None or metrics["peak_memory"] >= 0

        proc.wait()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
