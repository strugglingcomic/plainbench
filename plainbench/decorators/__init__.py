"""
Decorator system for benchmarking Python functions.

Provides the @benchmark decorator for easy function benchmarking with
automatic warmup, multiple runs, and metrics collection.
"""

from plainbench.decorators.benchmark import benchmark

__all__ = ['benchmark']
