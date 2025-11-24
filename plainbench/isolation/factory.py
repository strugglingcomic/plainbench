"""Factory for creating isolation strategies."""

from typing import Dict, Type

from .base import IsolationStrategy
from .maximum import MaximumIsolation
from .minimal import MinimalIsolation
from .moderate import ModerateIsolation

# Registry of available isolation strategies
_ISOLATION_STRATEGIES: Dict[str, Type[IsolationStrategy]] = {
    "minimal": MinimalIsolation,
    "moderate": ModerateIsolation,
    "maximum": MaximumIsolation,
}


def create_isolation_strategy(level: str) -> IsolationStrategy:
    """
    Create an isolation strategy instance for the specified level.

    Args:
        level: Isolation level ("minimal", "moderate", or "maximum")

    Returns:
        IsolationStrategy instance

    Raises:
        ValueError: If the isolation level is not recognized

    Example:
        >>> strategy = create_isolation_strategy("minimal")
        >>> strategy.setup()
        >>> # ... run benchmark ...
        >>> strategy.teardown()
    """
    if level not in _ISOLATION_STRATEGIES:
        valid_levels = ", ".join(_ISOLATION_STRATEGIES.keys())
        raise ValueError(
            f"Unknown isolation level: {level}. "
            f"Valid levels are: {valid_levels}"
        )

    strategy_class = _ISOLATION_STRATEGIES[level]
    return strategy_class()


def get_available_strategies() -> list[str]:
    """
    Get list of available isolation strategy names.

    Returns:
        List of strategy names
    """
    return list(_ISOLATION_STRATEGIES.keys())


def register_isolation_strategy(name: str, strategy_class: Type[IsolationStrategy]) -> None:
    """
    Register a custom isolation strategy.

    Args:
        name: Strategy name
        strategy_class: IsolationStrategy subclass

    Raises:
        ValueError: If strategy_class is not an IsolationStrategy subclass
    """
    if not issubclass(strategy_class, IsolationStrategy):
        raise ValueError(
            f"{strategy_class} must be a subclass of IsolationStrategy"
        )

    _ISOLATION_STRATEGIES[name] = strategy_class
