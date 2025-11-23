"""
Shell command benchmarking module.

Provides black-box benchmarking of shell commands with:
- Process monitoring via psutil
- Resource usage tracking
- Both snapshot and continuous monitoring modes
"""

from .runner import benchmark_shell, ShellCommandRunner
from .results import ShellBenchmarkResult, ShellCommandResult
from .monitor import ProcessMonitor

__all__ = [
    'benchmark_shell',
    'ShellCommandRunner',
    'ShellBenchmarkResult',
    'ShellCommandResult',
    'ProcessMonitor',
]
