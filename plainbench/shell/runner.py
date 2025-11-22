"""
Shell command benchmarking with process monitoring.
"""

import subprocess
import time
import statistics
from typing import Optional, List, Dict, Any, Union
import psutil

from .monitor import ProcessMonitor
from .results import ShellCommandResult, ShellBenchmarkResult


class ShellCommandRunner:
    """
    Runner for executing and monitoring shell commands.

    Provides comprehensive resource monitoring using psutil.
    """

    def __init__(
        self,
        command: Union[str, List[str]],
        shell: bool = True,
        capture_output: bool = False,
        timeout: Optional[float] = None,
        monitoring_mode: str = "snapshot",
        monitoring_interval: float = 0.1,
    ):
        """
        Initialize shell command runner.

        Args:
            command: Shell command to execute
            shell: Execute via shell (default: True)
            capture_output: Capture stdout/stderr (default: False)
            timeout: Command timeout in seconds
            monitoring_mode: 'snapshot' or 'continuous'
            monitoring_interval: Polling interval for continuous mode (seconds)
        """
        self.command = command
        self.shell = shell
        self.capture_output = capture_output
        self.timeout = timeout
        self.monitoring_mode = monitoring_mode
        self.monitoring_interval = monitoring_interval

    def run_command(self) -> ShellCommandResult:
        """
        Execute the command once with monitoring.

        Returns:
            ShellCommandResult with metrics and output

        Raises:
            subprocess.TimeoutExpired: If timeout is exceeded
            FileNotFoundError: If command is not found
        """
        # Validate command
        if isinstance(self.command, str):
            if not self.command or not self.command.strip():
                raise ValueError("Command cannot be empty")
        elif isinstance(self.command, (list, tuple)):
            if not self.command or len(self.command) == 0:
                raise ValueError("Command cannot be empty")
        else:
            raise TypeError(f"Command must be str, list, or tuple, not {type(self.command)}")

        # Start timing
        start_time = time.perf_counter()

        # Start subprocess
        proc = subprocess.Popen(
            self.command,
            shell=self.shell,
            stdout=subprocess.PIPE if self.capture_output else subprocess.DEVNULL,
            stderr=subprocess.PIPE if self.capture_output else subprocess.DEVNULL,
        )

        # Wrap with psutil for monitoring
        try:
            ps_proc = psutil.Process(proc.pid)
        except psutil.NoSuchProcess:
            # Process already terminated (very fast execution)
            ps_proc = None

        # Start monitoring
        monitor = None
        if ps_proc:
            monitor = ProcessMonitor(
                ps_proc,
                mode=self.monitoring_mode,
                interval=self.monitoring_interval
            )
            monitor.start()

        # Wait for process to complete with timeout
        try:
            if self.timeout:
                stdout, stderr = proc.communicate(timeout=self.timeout)
            else:
                stdout, stderr = proc.communicate()
        except subprocess.TimeoutExpired:
            # Kill process on timeout
            proc.kill()
            if monitor:
                monitor.stop()
            raise

        # Stop monitoring
        metrics = {}
        if monitor:
            metrics = monitor.stop()

        # End timing
        end_time = time.perf_counter()
        wall_time = end_time - start_time

        # Decode output
        stdout_str = None
        stderr_str = None
        if self.capture_output:
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else None
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else None

        # Build result
        return ShellCommandResult(
            command=self.command,
            exit_code=proc.returncode,
            wall_time=wall_time,
            stdout=stdout_str,
            stderr=stderr_str,
            peak_memory=metrics.get('peak_memory'),
            cpu_percent=metrics.get('cpu_percent'),
            read_bytes=metrics.get('read_bytes'),
            write_bytes=metrics.get('write_bytes'),
        )


def benchmark_shell(
    command: Union[str, List[str]],
    warmup: int = 1,
    runs: int = 5,
    metrics: Optional[List[str]] = None,
    monitoring_mode: str = "snapshot",
    monitoring_interval: float = 0.1,
    timeout: Optional[float] = None,
    capture_output: bool = False,
    shell: bool = True,
    store: bool = True,
    database: Optional[str] = None,
    name: Optional[str] = None,
    isolation: str = "minimal",
) -> ShellBenchmarkResult:
    """
    Benchmark a shell command.

    Args:
        command: Shell command to execute
        warmup: Number of warmup iterations (default: 1)
        runs: Number of measurement iterations (default: 5)
        metrics: List of metrics to collect (default: all available)
        monitoring_mode: 'snapshot' or 'continuous' (default: 'snapshot')
        monitoring_interval: Sampling interval for continuous mode (default: 0.1s)
        timeout: Command timeout in seconds
        capture_output: Capture stdout/stderr (default: False)
        shell: Execute via shell (default: True)
        store: Store results in database (default: True)
        database: Database path (optional)
        name: Benchmark name (optional)
        isolation: Isolation strategy ('minimal', 'moderate', 'maximum')

    Returns:
        ShellBenchmarkResult with aggregated statistics

    Raises:
        subprocess.TimeoutExpired: If timeout is exceeded
        FileNotFoundError: If command is not found
        ValueError: If command is empty

    Example:
        >>> result = benchmark_shell('echo hello', runs=10)
        >>> print(f"Mean time: {result.mean_time:.3f}s")
    """
    from ..isolation.factory import create_isolation_strategy

    # Create isolation strategy
    isolation_strategy = create_isolation_strategy(isolation)

    # Setup isolation
    isolation_strategy.setup()

    try:
        # Create runner
        runner = ShellCommandRunner(
            command=command,
            shell=shell,
            capture_output=capture_output,
            timeout=timeout,
            monitoring_mode=monitoring_mode,
            monitoring_interval=monitoring_interval,
        )

        # Warmup phase
        for _ in range(warmup):
            subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                timeout=timeout,
                check=False,
            )

        # Measurement phase
        measurements: List[ShellCommandResult] = []

        for _ in range(runs):
            result = runner.run_command()
            measurements.append(result)
    finally:
        # Teardown isolation
        isolation_strategy.teardown()

    # Aggregate statistics
    aggregated = _aggregate_measurements(measurements)

    # Get last run's output and exit code
    last_measurement = measurements[-1]

    # Get isolation metadata
    isolation_metadata = isolation_strategy.get_metadata()

    return ShellBenchmarkResult(
        command=command,
        exit_code=last_measurement.exit_code,
        iterations=runs,
        mean_time=aggregated['mean_time'],
        median_time=aggregated['median_time'],
        stddev_time=aggregated['stddev_time'],
        min_time=aggregated['min_time'],
        max_time=aggregated['max_time'],
        mean_memory=aggregated.get('mean_memory'),
        peak_memory=aggregated.get('peak_memory'),
        total_read_bytes=aggregated.get('total_read_bytes'),
        total_write_bytes=aggregated.get('total_write_bytes'),
        stdout=last_measurement.stdout,
        stderr=last_measurement.stderr,
        raw_measurements=measurements,
        metadata={
            'warmup': warmup,
            'monitoring_mode': monitoring_mode,
            'monitoring_interval': monitoring_interval,
            'isolation': isolation_metadata,
        }
    )


def _aggregate_measurements(
    measurements: List[ShellCommandResult]
) -> Dict[str, Any]:
    """
    Aggregate measurements into statistics.

    Args:
        measurements: List of ShellCommandResult objects

    Returns:
        Dictionary of aggregated statistics
    """
    # Extract timing values
    times = [m.wall_time for m in measurements]

    # Calculate timing statistics
    aggregated = {
        'mean_time': statistics.mean(times),
        'median_time': statistics.median(times),
        'stddev_time': statistics.stdev(times) if len(times) > 1 else 0.0,
        'min_time': min(times),
        'max_time': max(times),
    }

    # Memory statistics
    memory_values = [m.peak_memory for m in measurements if m.peak_memory is not None]
    if memory_values:
        aggregated['mean_memory'] = int(statistics.mean(memory_values))
        aggregated['peak_memory'] = max(memory_values)

    # I/O statistics
    read_values = [m.read_bytes for m in measurements if m.read_bytes is not None]
    write_values = [m.write_bytes for m in measurements if m.write_bytes is not None]

    if read_values:
        aggregated['total_read_bytes'] = sum(read_values)
    if write_values:
        aggregated['total_write_bytes'] = sum(write_values)

    return aggregated
