"""
Shell command benchmarking module.

Provides black-box benchmarking of shell commands with:
- Process monitoring via psutil
- Resource usage tracking
- Both snapshot and continuous monitoring modes
"""

from .monitor import ProcessMonitor
from .results import ShellBenchmarkResult, ShellCommandResult
from .runner import ShellCommandRunner, benchmark_shell

__all__ = [
    'benchmark_shell',
    'ShellCommandRunner',
    'ShellBenchmarkResult',
    'ShellCommandResult',
    'ProcessMonitor',
]
