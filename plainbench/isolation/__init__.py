"""
Isolation strategies for reproducible benchmarking.

Provides three levels of isolation:
- Minimal: Basic subprocess isolation
- Moderate: CPU pinning, GC control (recommended)
- Maximum: Docker containers, cgroups (for CI/CD)
"""

from plainbench.isolation.base import IsolationStrategy

__all__ = ['IsolationStrategy']
