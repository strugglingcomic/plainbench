"""Maximum isolation strategy - subprocess and environment isolation."""

import os
import warnings
from typing import Dict, Any, List, Optional, Set

from .base import IsolationStrategy
from .moderate import ModerateIsolation
from .system_utils import (
    get_platform,
    check_system_tuning,
    is_aslr_enabled,
    disable_aslr,
)


class MaximumIsolation(IsolationStrategy):
    """
    Maximum isolation strategy.

    This strategy provides maximum isolation through:
    - All features from ModerateIsolation (CPU pinning, priority, GC control)
    - Environment variable cleanup (minimal env for reproducibility)
    - System tuning checks with detailed warnings
    - ASLR control (Linux only, requires permissions)
    - Subprocess execution support (via environment preparation)

    This is the most robust isolation level, recommended for
    CI/CD and highly reproducible benchmarking requirements.

    Platform Support:
    - Linux: Full support including ASLR control and detailed system checks
    - macOS: Partial support (no ASLR control)
    - Windows: Basic support (environment cleanup and priority)

    Permission Requirements:
    - Most features: Standard user permissions
    - ASLR control: Requires root/admin (Linux only)
    - Process priority: May require elevated privileges

    Example:
        >>> isolation = MaximumIsolation(
        ...     cpu_cores=[0, 1, 2, 3],
        ...     minimal_env=True,
        ...     attempt_aslr_disable=True
        ... )
        >>> isolation.setup()
        >>> # Run benchmark
        >>> isolation.teardown()

    Note:
        For true subprocess isolation, use this strategy in combination
        with multiprocessing-based execution. This strategy prepares the
        environment but doesn't change the execution model.
    """

    def __init__(
        self,
        cpu_cores: Optional[List[int]] = None,
        set_priority: bool = True,
        minimal_env: bool = True,
        attempt_aslr_disable: bool = False,
        essential_env_vars: Optional[Set[str]] = None,
    ):
        """
        Initialize maximum isolation strategy.

        Args:
            cpu_cores: List of CPU cores to pin to (None = use first 4 or all available)
            set_priority: Whether to adjust process priority
            minimal_env: Whether to clean up environment variables
            attempt_aslr_disable: Whether to attempt ASLR disabling (requires root)
            essential_env_vars: Set of essential env vars to keep (adds to defaults)
        """
        # Initialize moderate isolation for base functionality
        self.moderate = ModerateIsolation(
            cpu_cores=cpu_cores,
            set_priority=set_priority,
            warn_tuning=True,
        )

        self.minimal_env = minimal_env
        self.attempt_aslr_disable = attempt_aslr_disable

        # Default essential environment variables
        self.essential_vars: Set[str] = {
            'PATH',
            'HOME',
            'USER',
            'SHELL',
            'TERM',
            'LANG',
            'PYTHONHASHSEED',  # We set this ourselves
            'VIRTUAL_ENV',  # Preserve venv
            'CONDA_PREFIX',  # Preserve conda env
        }

        # Add user-specified essential vars
        if essential_env_vars:
            self.essential_vars.update(essential_env_vars)

        # State tracking
        self.original_env: Optional[Dict[str, str]] = None
        self.aslr_was_disabled: bool = False

    def setup(self) -> None:
        """
        Set up maximum isolation.

        Applies the following isolation measures:
        1. All moderate isolation features (CPU, priority, GC, PYTHONHASHSEED)
        2. Environment variable cleanup
        3. Detailed system tuning checks
        4. ASLR disabling (if requested and permitted)

        Note: Operations that fail due to permissions will emit warnings
        but won't prevent setup from completing.
        """
        # Perform detailed system checks
        self._check_system_tuning()

        # Set up moderate isolation features
        self.moderate.setup()

        # Clean up environment if requested
        if self.minimal_env:
            self._setup_minimal_environment()

        # Attempt ASLR disabling if requested
        if self.attempt_aslr_disable:
            self._attempt_disable_aslr()

    def _check_system_tuning(self) -> None:
        """Check and warn about system tuning settings."""
        info = check_system_tuning()

        if info['warnings']:
            warnings.warn(
                "System tuning warnings for maximum isolation:\n" +
                "\n".join(f"  - {w}" for w in info['warnings']),
                UserWarning,
                stacklevel=3
            )

        # Additional detailed checks for maximum isolation
        platform_name = info['platform']

        if platform_name == 'linux':
            # Check for cgroups availability (informational only)
            if os.path.exists('/sys/fs/cgroup'):
                # cgroups available but we're not using them directly
                pass

        elif platform_name in ('darwin', 'windows'):
            warnings.warn(
                f"Maximum isolation on {platform_name} has limited features. "
                "Consider using Linux for best results.",
                UserWarning,
                stacklevel=3
            )

    def _setup_minimal_environment(self) -> None:
        """
        Set up minimal environment by removing non-essential variables.

        This improves reproducibility by reducing environment-dependent behavior.
        """
        # Save original environment
        self.original_env = dict(os.environ)

        # Build minimal environment with only essential variables
        minimal_env = {}
        for key in self.essential_vars:
            if key in os.environ:
                minimal_env[key] = os.environ[key]

        # Clear all environment variables
        os.environ.clear()

        # Restore only essential ones
        os.environ.update(minimal_env)

        # Ensure PYTHONHASHSEED is set (might have been cleared)
        os.environ['PYTHONHASHSEED'] = '0'

    def _attempt_disable_aslr(self) -> None:
        """
        Attempt to disable ASLR for maximum reproducibility.

        Warning:
            This has security implications and requires root privileges.
            Only use on isolated benchmark systems.
        """
        platform_name = get_platform()

        if platform_name != 'linux':
            warnings.warn(
                f"ASLR control not supported on {platform_name}. "
                "Only Linux supports ASLR control.",
                UserWarning,
                stacklevel=3
            )
            return

        # Check current ASLR status
        aslr_enabled = is_aslr_enabled()

        if aslr_enabled is None:
            warnings.warn(
                "Cannot determine ASLR status. Skipping ASLR control.",
                UserWarning,
                stacklevel=3
            )
            return

        if not aslr_enabled:
            # Already disabled
            self.aslr_was_disabled = True
            return

        # Try to disable ASLR
        success = disable_aslr()

        if success:
            warnings.warn(
                "ASLR has been disabled for maximum isolation. "
                "This has security implications. "
                "ASLR will be re-enabled on teardown.",
                UserWarning,
                stacklevel=3
            )
            self.aslr_was_disabled = False
        else:
            warnings.warn(
                "Failed to disable ASLR (requires root privileges). "
                "Benchmarks may have slight variance due to ASLR. "
                "Run with sudo/root for maximum isolation.",
                UserWarning,
                stacklevel=3
            )

    def teardown(self) -> None:
        """
        Tear down maximum isolation.

        Restores all settings to their original values:
        1. All moderate isolation features
        2. Environment variables
        3. ASLR (if it was enabled originally)
        """
        # Restore environment variables
        if self.original_env is not None:
            os.environ.clear()
            os.environ.update(self.original_env)

        # Restore ASLR if we disabled it
        if self.attempt_aslr_disable and not self.aslr_was_disabled:
            # Try to re-enable ASLR
            platform_name = get_platform()
            if platform_name == 'linux':
                try:
                    from pathlib import Path
                    aslr_path = Path('/proc/sys/kernel/randomize_va_space')
                    if aslr_path.exists():
                        # Re-enable with conservative ASLR (value=1)
                        aslr_path.write_text('1\n')
                except (OSError, PermissionError):
                    warnings.warn(
                        "Failed to re-enable ASLR. You may need to manually restore it.",
                        UserWarning,
                        stacklevel=2
                    )

        # Teardown moderate isolation
        self.moderate.teardown()

    def get_metadata(self) -> Dict[str, Any]:
        """Get isolation metadata."""
        # Get moderate isolation metadata first
        moderate_meta = self.moderate.get_metadata()

        # Start with base metadata
        metadata = super().get_metadata()

        # Merge moderate metadata (but preserve our strategy name)
        metadata.update(moderate_meta)

        # Override with maximum-specific values
        metadata["strategy"] = self.__class__.__name__
        metadata["level"] = "maximum"
        metadata["minimal_environment"] = self.minimal_env
        metadata["aslr_control_attempted"] = self.attempt_aslr_disable

        # Add system tuning info
        sys_info = check_system_tuning()
        metadata["system_tuning"] = {
            "platform": sys_info['platform'],
            "cpu_governor": sys_info['cpu_governor'],
            "turbo_boost_enabled": sys_info['turbo_boost_enabled'],
            "aslr_enabled": sys_info['aslr_enabled'],
            "has_warnings": len(sys_info['warnings']) > 0,
        }

        return metadata
