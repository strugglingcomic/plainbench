"""Moderate isolation strategy - CPU pinning and environment control."""

import gc
import os
import warnings
from typing import Any, Dict, List, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from .base import IsolationStrategy
from .system_utils import get_platform, warn_system_tuning


class ModerateIsolation(IsolationStrategy):
    """
    Moderate isolation strategy.

    This strategy provides enhanced isolation through:
    - CPU core pinning via psutil (platform-dependent)
    - Process priority adjustment (Unix: nice level, Windows: priority class)
    - Environment variable control (PYTHONHASHSEED=0 for reproducibility)
    - Garbage collection control (disable during measurement)
    - System tuning warnings

    This is the recommended isolation level for most production
    benchmarking scenarios.

    Platform Support:
    - Linux: Full support (CPU affinity, nice level)
    - macOS: CPU affinity may not be supported (graceful degradation)
    - Windows: Limited support (priority class via psutil)

    Permission Requirements:
    - CPU affinity: No special permissions required
    - Process priority: May require elevated privileges for high priority
    - Falls back gracefully if permissions are insufficient

    Example:
        >>> isolation = ModerateIsolation(cpu_cores=[0, 1, 2, 3])
        >>> isolation.setup()
        >>> # Run benchmark
        >>> isolation.teardown()
    """

    def __init__(
        self,
        cpu_cores: Optional[List[int]] = None,
        set_priority: bool = True,
        warn_tuning: bool = True,
    ):
        """
        Initialize moderate isolation strategy.

        Args:
            cpu_cores: List of CPU cores to pin to (None = use first 4 or all available)
            set_priority: Whether to adjust process priority
            warn_tuning: Whether to warn about non-optimal system tuning
        """
        self.cpu_cores = cpu_cores
        self.set_priority = set_priority
        self.warn_tuning = warn_tuning

        # State tracking for restoration
        self.original_affinity: Optional[List[int]] = None
        self.original_priority: Optional[int] = None
        self.original_pythonhashseed: Optional[str] = None
        self.gc_was_enabled: bool = False

        # Feature availability
        self.affinity_supported = False
        self.priority_supported = False

    def setup(self) -> None:
        """
        Set up moderate isolation.

        Applies the following isolation measures:
        1. CPU affinity pinning (if supported)
        2. Process priority adjustment (if supported)
        3. PYTHONHASHSEED=0 for reproducibility
        4. Disable garbage collection
        5. Check and warn about system tuning

        Note: Operations that fail due to permissions will emit warnings
        but won't prevent setup from completing.
        """
        # Warn about system tuning if requested
        if self.warn_tuning:
            warn_system_tuning()

        # Set up CPU affinity
        if PSUTIL_AVAILABLE:
            self._setup_cpu_affinity()

        # Set up process priority
        if PSUTIL_AVAILABLE and self.set_priority:
            self._setup_priority()

        # Set PYTHONHASHSEED for reproducibility
        self._setup_pythonhashseed()

        # Disable garbage collection
        self._setup_gc()

    def _setup_cpu_affinity(self) -> None:
        """Set up CPU affinity pinning."""
        try:
            process = psutil.Process()

            # Save original affinity
            try:
                self.original_affinity = process.cpu_affinity()
            except (AttributeError, OSError, NotImplementedError):
                # CPU affinity not supported on this platform
                self.affinity_supported = False
                return

            # Determine which cores to use
            if self.cpu_cores is not None:
                cores = self.cpu_cores
            else:
                # Use first 4 cores if available, otherwise use all
                cpu_count = psutil.cpu_count(logical=True) or 1
                num_cores = min(4, cpu_count)
                cores = list(range(num_cores))

            # Validate cores
            cpu_count = psutil.cpu_count(logical=True) or 1
            valid_cores = [c for c in cores if 0 <= c < cpu_count]

            if not valid_cores:
                warnings.warn(
                    f"Invalid CPU cores specified: {cores}. "
                    f"Valid range is 0-{cpu_count-1}. Skipping CPU pinning.",
                    UserWarning
                )
                return

            # Set CPU affinity
            try:
                process.cpu_affinity(valid_cores)
                self.affinity_supported = True
            except (AttributeError, OSError, NotImplementedError, PermissionError) as e:
                warnings.warn(
                    f"Failed to set CPU affinity to cores {valid_cores}: {e}. "
                    "Continuing without CPU pinning.",
                    UserWarning
                )
                self.affinity_supported = False

        except Exception as e:
            warnings.warn(
                f"Unexpected error setting up CPU affinity: {e}",
                UserWarning
            )

    def _setup_priority(self) -> None:
        """Set up process priority."""
        try:
            process = psutil.Process()
            platform_name = get_platform()

            # Save original priority
            try:
                if platform_name == 'windows':
                    self.original_priority = process.nice()
                else:
                    self.original_priority = process.nice()
            except (AttributeError, OSError):
                self.priority_supported = False
                return

            # Set high priority
            try:
                if platform_name == 'windows':
                    # Windows: Use HIGH_PRIORITY_CLASS
                    process.nice(psutil.HIGH_PRIORITY_CLASS)
                else:
                    # Unix: Use nice level -10 (higher priority)
                    # Note: This typically requires root/sudo for negative values
                    process.nice(-10)

                self.priority_supported = True

            except (PermissionError, OSError) as e:
                # Expected if running without elevated privileges
                warnings.warn(
                    f"Failed to set high process priority: {e}. "
                    "This may cause performance variance. "
                    "Consider running with elevated privileges for best results.",
                    UserWarning
                )
                self.priority_supported = False

        except Exception as e:
            warnings.warn(
                f"Unexpected error setting up process priority: {e}",
                UserWarning
            )

    def _setup_pythonhashseed(self) -> None:
        """Set PYTHONHASHSEED for reproducibility."""
        self.original_pythonhashseed = os.environ.get('PYTHONHASHSEED')
        os.environ['PYTHONHASHSEED'] = '0'

    def _setup_gc(self) -> None:
        """Disable garbage collection."""
        self.gc_was_enabled = gc.isenabled()
        if self.gc_was_enabled:
            gc.collect()  # Clean up before disabling
            gc.disable()

    def teardown(self) -> None:
        """
        Tear down moderate isolation.

        Restores all settings to their original values:
        1. CPU affinity
        2. Process priority
        3. PYTHONHASHSEED
        4. Garbage collection state
        """
        # Restore CPU affinity
        if self.affinity_supported and self.original_affinity is not None:
            try:
                process = psutil.Process()
                process.cpu_affinity(self.original_affinity)
            except (AttributeError, OSError, NotImplementedError):
                pass

        # Restore process priority
        if self.priority_supported and self.original_priority is not None:
            try:
                process = psutil.Process()
                process.nice(self.original_priority)
            except (AttributeError, OSError):
                pass

        # Restore PYTHONHASHSEED
        if self.original_pythonhashseed is not None:
            os.environ['PYTHONHASHSEED'] = self.original_pythonhashseed
        else:
            os.environ.pop('PYTHONHASHSEED', None)

        # Restore garbage collection
        if self.gc_was_enabled:
            gc.enable()

    def get_metadata(self) -> Dict[str, Any]:
        """Get isolation metadata."""
        metadata = super().get_metadata()
        metadata["level"] = "moderate"
        metadata["cpu_pinning"] = self.affinity_supported
        metadata["cpu_cores"] = self.cpu_cores
        metadata["priority_adjustment"] = self.priority_supported
        metadata["pythonhashseed"] = "0"
        metadata["gc_disabled"] = True
        metadata["platform"] = get_platform()
        return metadata
