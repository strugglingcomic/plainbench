"""
Isolation strategies for reproducible benchmarking.

Provides three levels of isolation:
- Minimal: Basic subprocess isolation
- Moderate: CPU pinning, GC control (recommended)
- Maximum: Docker containers, cgroups (for CI/CD)
"""

from plainbench.isolation.base import IsolationStrategy
from plainbench.isolation.factory import create_isolation_strategy, get_available_strategies

__all__ = ['IsolationStrategy', 'create_isolation_strategy', 'get_available_strategies']
