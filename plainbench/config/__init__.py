"""
Configuration management module.

Provides:
- Configuration loading from YAML/TOML files
- Environment variable overrides
- Configuration validation
- Default configuration values
"""

from plainbench.config.settings import BenchmarkConfig

__all__ = ['BenchmarkConfig']
