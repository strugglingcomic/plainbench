"""Platform detection utilities."""

import platform
import sys
from typing import Dict


def get_platform_info() -> Dict[str, str]:
    """
    Get platform information.

    Returns:
        Dictionary with platform details
    """
    return {
        "system": platform.system(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "machine": platform.machine(),
    }


def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith("linux")


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform == "darwin"


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32"
