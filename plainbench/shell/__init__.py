"""
Shell command benchmarking module.

Provides black-box benchmarking of shell commands with:
- Process monitoring via psutil
- Resource usage tracking
- Both snapshot and continuous monitoring modes
"""

from plainbench.shell.runner import benchmark_shell, ShellBenchmarkResult

__all__ = ['benchmark_shell', 'ShellBenchmarkResult']
