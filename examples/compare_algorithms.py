"""
Compare pure-Python implementations with plainbench.compare().

Three ways to find the 10 smallest values in a large list.

Run:
    python examples/compare_algorithms.py
"""

import heapq
import random

from plainbench import compare

data = [random.random() for _ in range(100_000)]


def full_sort():
    return sorted(data)[:10]


def heap_nsmallest():
    return heapq.nsmallest(10, data)


def manual_scan():
    best = sorted(data[:10])
    for value in data[10:]:
        if value < best[-1]:
            best.pop()
            # insert keeping order
            lo = 0
            while lo < len(best) and best[lo] < value:
                lo += 1
            best.insert(lo, value)
    return best


if __name__ == "__main__":
    result = compare(
        {
            "full_sort": full_sort,
            "heapq_nsmallest": heap_nsmallest,
            "manual_scan": manual_scan,
        },
        runs=10,
        warmup=2,
    )
    result.print()
    print()
    print(f"fastest: {result.fastest} "
          f"({result.speedup(result.fastest):.1f}x faster than {result.slowest})")
