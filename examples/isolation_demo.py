#!/usr/bin/env python3
"""
Demonstration of PlainBench isolation strategies.

This example shows how different isolation levels affect benchmarking.
"""

import time
from plainbench.decorators import benchmark


@benchmark(name="minimal_isolation", isolation="minimal", runs=5, warmup=2)
def test_minimal_isolation():
    """Benchmark with minimal isolation (default)."""
    # Simple computation
    result = sum(i**2 for i in range(10000))
    return result


@benchmark(name="moderate_isolation", isolation="moderate", runs=5, warmup=2)
def test_moderate_isolation():
    """Benchmark with moderate isolation (CPU pinning, priority, GC control)."""
    # Same computation with moderate isolation
    result = sum(i**2 for i in range(10000))
    return result


@benchmark(name="maximum_isolation", isolation="maximum", runs=5, warmup=2)
def test_maximum_isolation():
    """Benchmark with maximum isolation (environment cleanup, system checks)."""
    # Same computation with maximum isolation
    result = sum(i**2 for i in range(10000))
    return result


def main():
    """Run all isolation demonstrations."""
    print("PlainBench Isolation Strategy Demonstration")
    print("=" * 60)
    print()

    print("Testing Minimal Isolation...")
    print("-" * 60)
    test_minimal_isolation()
    print()

    print("Testing Moderate Isolation...")
    print("-" * 60)
    test_moderate_isolation()
    print()

    print("Testing Maximum Isolation...")
    print("-" * 60)
    test_maximum_isolation()
    print()

    print("=" * 60)
    print("All isolation strategies tested successfully!")
    print()
    print("Note: Check the database for detailed results and metadata.")


if __name__ == "__main__":
    main()
