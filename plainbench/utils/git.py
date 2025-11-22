"""Git integration utilities."""

import subprocess
from typing import Optional, Tuple


def get_git_info() -> Tuple[Optional[str], Optional[str], bool]:
    """
    Get current Git information.

    Returns:
        Tuple of (commit_hash, branch, is_dirty)
    """
    try:
        # Get commit hash
        commit_hash = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )

        # Get branch name
        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )

        # Check if working directory is dirty
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL
        ).decode()
        is_dirty = len(status.strip()) > 0

        return commit_hash, branch, is_dirty

    except (subprocess.CalledProcessError, FileNotFoundError):
        # Git not available or not in a git repository
        return None, None, False


def get_commit_hash() -> Optional[str]:
    """Get current Git commit hash."""
    commit_hash, _, _ = get_git_info()
    return commit_hash


def get_branch() -> Optional[str]:
    """Get current Git branch name."""
    _, branch, _ = get_git_info()
    return branch


def is_dirty() -> bool:
    """Check if working directory has uncommitted changes."""
    _, _, dirty = get_git_info()
    return dirty
