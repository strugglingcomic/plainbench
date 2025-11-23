"""Minimal isolation strategy - basic GC control only."""

from typing import Any, Dict

from .base import IsolationStrategy


class MinimalIsolation(IsolationStrategy):
    """
    Minimal isolation strategy.

    This strategy provides basic isolation through:
    - Garbage collection control (handled by decorator)
    - No process or environment modifications

    This is the lightest-weight isolation option and is suitable
    for most benchmarking scenarios where external interference
    is minimal.
    """

    def setup(self) -> None:
        """
        Set up minimal isolation.

        For minimal isolation, we don't need to do any special setup.
        GC control is handled by the decorator itself.
        """
        # No special setup needed for minimal isolation
        pass

    def teardown(self) -> None:
        """
        Tear down minimal isolation.

        For minimal isolation, we don't need to do any special teardown.
        """
        # No special teardown needed for minimal isolation
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Get isolation metadata."""
        metadata = super().get_metadata()
        metadata["level"] = "minimal"
        metadata["gc_control"] = True
        return metadata
