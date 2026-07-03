"""
System utilities for isolation strategies.

Provides platform-specific utilities for:
- CPU governor detection and control
- Turbo boost detection
- ASLR (Address Space Layout Randomization) detection
- System tuning checks

These utilities are used by isolation strategies to detect and warn about
non-optimal system settings for benchmarking.
"""

import platform
import warnings
from pathlib import Path
from typing import List, Optional


def get_platform() -> str:
    """
    Get the current platform.

    Returns:
        'linux', 'darwin' (macOS), 'windows', or 'unknown'
    """
    system = platform.system().lower()
    if system == 'linux':
        return 'linux'
    elif system == 'darwin':
        return 'darwin'
    elif system == 'windows':
        return 'windows'
    else:
        return 'unknown'


def get_cpu_governor() -> Optional[str]:
    """
    Get the current CPU frequency governor (Linux only).

    Returns:
        Governor name (e.g., 'performance', 'powersave', 'ondemand') or None

    Note:
        Only works on Linux with cpufreq support.
    """
    if get_platform() != 'linux':
        return None

    try:
        # Try to read governor from first CPU
        governor_path = Path('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor')
        if governor_path.exists():
            return governor_path.read_text().strip()
    except (OSError, PermissionError):
        pass

    return None


def set_cpu_governor(governor: str) -> bool:
    """
    Set the CPU frequency governor (Linux only, requires root).

    Args:
        governor: Governor name ('performance', 'powersave', etc.)

    Returns:
        True if successful, False otherwise

    Warning:
        Requires root/sudo privileges. Will fail silently without permissions.
    """
    if get_platform() != 'linux':
        return False

    try:
        # Get all CPU paths
        cpu_dir = Path('/sys/devices/system/cpu')
        cpu_paths = list(cpu_dir.glob('cpu[0-9]*/cpufreq/scaling_governor'))

        if not cpu_paths:
            return False

        # Set governor for all CPUs
        for path in cpu_paths:
            try:
                path.write_text(governor + '\n')
            except (OSError, PermissionError):
                # Failed to write, likely due to permissions
                return False

        return True
    except Exception:
        return False


def is_turbo_boost_enabled() -> Optional[bool]:
    """
    Check if Intel Turbo Boost or AMD Turbo Core is enabled.

    Returns:
        True if enabled, False if disabled, None if cannot determine

    Note:
        - Linux: Checks intel_pstate/no_turbo or cpufreq/boost
        - macOS: Cannot reliably detect
        - Windows: Cannot reliably detect
    """
    if get_platform() == 'linux':
        # Check Intel Turbo Boost
        intel_path = Path('/sys/devices/system/cpu/intel_pstate/no_turbo')
        if intel_path.exists():
            try:
                # no_turbo=1 means turbo is DISABLED
                no_turbo = intel_path.read_text().strip()
                return no_turbo == '0'
            except (OSError, PermissionError):
                pass

        # Check AMD Turbo Core (or generic cpufreq boost)
        amd_path = Path('/sys/devices/system/cpu/cpufreq/boost')
        if amd_path.exists():
            try:
                boost = amd_path.read_text().strip()
                return boost == '1'
            except (OSError, PermissionError):
                pass

    return None


def disable_turbo_boost() -> bool:
    """
    Disable Turbo Boost (Linux only, requires root).

    Returns:
        True if successful, False otherwise

    Warning:
        Requires root/sudo privileges. Will fail silently without permissions.
    """
    if get_platform() != 'linux':
        return False

    try:
        # Try Intel Turbo Boost
        intel_path = Path('/sys/devices/system/cpu/intel_pstate/no_turbo')
        if intel_path.exists():
            try:
                intel_path.write_text('1\n')
                return True
            except (OSError, PermissionError):
                pass

        # Try AMD Turbo Core
        amd_path = Path('/sys/devices/system/cpu/cpufreq/boost')
        if amd_path.exists():
            try:
                amd_path.write_text('0\n')
                return True
            except (OSError, PermissionError):
                pass

    except Exception:
        pass

    return False


def is_aslr_enabled() -> Optional[bool]:
    """
    Check if Address Space Layout Randomization (ASLR) is enabled.

    Returns:
        True if enabled, False if disabled, None if cannot determine

    Note:
        - Linux: Checks /proc/sys/kernel/randomize_va_space
        - macOS: Cannot reliably detect (generally enabled)
        - Windows: Cannot reliably detect (generally enabled)
    """
    if get_platform() == 'linux':
        aslr_path = Path('/proc/sys/kernel/randomize_va_space')
        if aslr_path.exists():
            try:
                value = aslr_path.read_text().strip()
                # 0 = disabled, 1 = conservative, 2 = full
                return value != '0'
            except (OSError, PermissionError):
                pass

    return None


def disable_aslr() -> bool:
    """
    Disable ASLR (Linux only, requires root).

    Returns:
        True if successful, False otherwise

    Warning:
        - Requires root/sudo privileges
        - Has SECURITY IMPLICATIONS - only use on isolated benchmark systems
        - Will fail silently without permissions
    """
    if get_platform() != 'linux':
        return False

    try:
        aslr_path = Path('/proc/sys/kernel/randomize_va_space')
        if aslr_path.exists():
            try:
                aslr_path.write_text('0\n')
                return True
            except (OSError, PermissionError):
                pass
    except Exception:
        pass

    return False


def check_system_tuning() -> dict:
    """
    Check current system tuning settings for benchmarking.

    Returns:
        Dictionary with system tuning information:
        {
            'platform': str,
            'cpu_governor': Optional[str],
            'turbo_boost_enabled': Optional[bool],
            'aslr_enabled': Optional[bool],
            'warnings': List[str]
        }

    Example:
        >>> info = check_system_tuning()
        >>> if info['warnings']:
        ...     print("System tuning warnings:")
        ...     for warning in info['warnings']:
        ...         print(f"  - {warning}")
    """
    warnings_list: List[str] = []

    platform_name = get_platform()
    governor = get_cpu_governor()
    turbo = is_turbo_boost_enabled()
    aslr = is_aslr_enabled()

    # Check for non-optimal settings
    if governor and governor != 'performance':
        warnings_list.append(
            f"CPU governor is '{governor}' (recommended: 'performance'). "
            "This may cause performance variance."
        )

    if turbo is True:
        warnings_list.append(
            "Turbo Boost is enabled. This may cause performance variance. "
            "Consider disabling for reproducible benchmarks."
        )

    if aslr is True:
        warnings_list.append(
            "ASLR is enabled. This may cause slight performance variance. "
            "Consider disabling for highly reproducible benchmarks (requires root)."
        )

    return {
        'platform': platform_name,
        'cpu_governor': governor,
        'turbo_boost_enabled': turbo,
        'aslr_enabled': aslr,
        'warnings': warnings_list,
    }


def warn_system_tuning() -> None:
    """
    Check system tuning and emit warnings if not optimal for benchmarking.

    This is a convenience function that calls check_system_tuning() and
    emits Python warnings for any issues found.
    """
    info = check_system_tuning()

    if info['warnings']:
        for warning_msg in info['warnings']:
            warnings.warn(warning_msg, UserWarning, stacklevel=2)
