"""Base isolation strategy interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IsolationStrategy(ABC):
    """
    Abstract base class for isolation strategies.

    Isolation strategies control the environment in which benchmarks run
    to ensure reproducible and reliable performance measurements.

    Lifecycle:
        1. setup() - Prepare isolation environment
        2. [benchmark execution]
        3. teardown() - Restore previous environment
    """

    @abstractmethod
    def setup(self) -> None:
        """
        Set up the isolation environment before benchmark execution.

        This method is called once before any benchmark runs.
        It should prepare the environment for isolated execution.
        """
        pass

    @abstractmethod
    def teardown(self) -> None:
        """
        Tear down the isolation environment after benchmark execution.

        This method is called once after all benchmark runs complete.
        It should restore the environment to its previous state.
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get isolation metadata to store with benchmark results.

        Returns:
            Dictionary of isolation-related metadata
        """
        return {
            "strategy": self.__class__.__name__,
        }
