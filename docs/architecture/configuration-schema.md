# PlainBench Configuration Schema

**Version:** 1.0
**Date:** 2025-11-22

---

## Table of Contents

1. [Overview](#overview)
2. [Configuration File Formats](#configuration-file-formats)
3. [Complete Schema](#complete-schema)
4. [Configuration Sections](#configuration-sections)
5. [Environment Variables](#environment-variables)
6. [Configuration Precedence](#configuration-precedence)
7. [Examples](#examples)

---

## Overview

PlainBench supports flexible configuration through:
- **YAML configuration files** (recommended)
- **TOML configuration files** (alternative)
- **Environment variables** (overrides)
- **CLI arguments** (highest priority)
- **Programmatic configuration** (Python API)

### Configuration File Location

PlainBench searches for configuration files in the following order:
1. Path specified via `--config` CLI argument
2. `plainbench.yaml` in current directory
3. `plainbench.toml` in current directory
4. `.plainbench/config.yaml` in current directory
5. `~/.config/plainbench/config.yaml` (user-level)
6. Default built-in configuration

---

## Configuration File Formats

### YAML Format (Recommended)

**File:** `plainbench.yaml`

```yaml
# PlainBench Configuration
# https://github.com/yourusername/plainbench

# General settings
general:
  # Project name (used in reports)
  project_name: "My Project"

  # Default isolation level: minimal, moderate, maximum
  default_isolation: moderate

  # Default metrics to collect
  default_metrics:
    - wall_time
    - cpu_time
    - python_memory
    - process_memory
    - disk_io

# Benchmark execution settings
execution:
  # Default number of warmup iterations
  warmup_runs: 3

  # Default number of measurement iterations
  measurement_runs: 10

  # Disable garbage collection during measurements
  disable_gc: true

  # Timeout for individual benchmarks (seconds, null for no timeout)
  timeout: 300

  # Continue on benchmark failure
  continue_on_error: true

# Isolation configuration
isolation:
  minimal:
    # No special configuration needed
    enabled: true

  moderate:
    # CPU cores to pin to (null for auto-detection)
    cpu_affinity: [0, 1, 2, 3]

    # Set PYTHONHASHSEED for reproducibility
    set_pythonhashseed: true
    pythonhashseed_value: 0

    # Disable garbage collection
    disable_gc: true

  maximum:
    # Docker settings
    use_docker: false
    docker_image: "python:3.11-slim"
    docker_cpus: 2.0
    docker_memory: "4g"
    docker_memory_swap: "4g"

    # cgroups settings (Linux only)
    use_cgroups: false
    cgroup_cpu_quota: 200000  # 2 CPUs (200000/100000)
    cgroup_memory_limit: 4294967296  # 4GB in bytes

    # System tuning (requires root)
    disable_turbo_boost: false
    set_cpu_governor: false
    cpu_governor: "performance"
    disable_aslr: false

# Storage settings
storage:
  # Database backend: sqlite (future: postgresql, influxdb)
  backend: sqlite

  # SQLite database path
  database_path: "./benchmarks.db"

  # SQLite performance settings
  sqlite:
    journal_mode: WAL
    synchronous: NORMAL
    cache_size: -64000  # 64MB
    temp_store: MEMORY

  # Store raw measurements (can be large)
  store_raw_measurements: true

  # Store aggregated statistics
  store_statistics: true

  # Auto-vacuum database
  auto_vacuum: INCREMENTAL

# Git integration
git:
  # Automatically capture git metadata
  enabled: true

  # Fail if working directory is dirty
  require_clean: false

  # Store git diff with results (for dirty repos)
  store_diff: false

# Metrics configuration
metrics:
  timing:
    # Timing metrics are always enabled
    enabled: true

  memory:
    # Enable memory profiling
    enabled: true

    # Use tracemalloc for Python heap
    use_tracemalloc: true

    # Use psutil for total process memory
    use_psutil: true

  cpu:
    # Enable CPU metrics
    enabled: true

    # Sample interval for CPU percent (seconds)
    sample_interval: 0.1

  io:
    # Enable I/O metrics (platform-dependent)
    enabled: true

    # Warn if I/O metrics unavailable
    warn_if_unavailable: true

# Shell command benchmarking
shell:
  # Default shell to use
  shell: /bin/bash

  # Capture stdout/stderr by default
  capture_output: false

  # Monitoring mode: snapshot or continuous
  monitoring_mode: continuous

  # Sampling interval for continuous monitoring (seconds)
  monitoring_interval: 0.1

  # Default timeout for shell commands (seconds)
  timeout: 60

# Statistical analysis
statistics:
  # Confidence level for significance testing
  confidence_level: 0.95

  # Alpha for hypothesis testing
  alpha: 0.05

  # Use robust statistics (median, MAD)
  use_robust_stats: true

  # Outlier detection method: iqr, zscore, none
  outlier_detection: iqr

  # Outlier threshold (for IQR: 1.5, for z-score: 3.0)
  outlier_threshold: 1.5

  # Remove outliers before computing statistics
  remove_outliers: false

# Comparison settings
comparison:
  # Performance regression threshold (fraction, e.g., 0.05 = 5%)
  regression_threshold: 0.05

  # Memory regression threshold (fraction)
  memory_regression_threshold: 0.10

  # Require statistical significance for regressions
  require_significance: true

  # Comparison method: ttest, mannwhitneyu, ks
  method: ttest

# Output and reporting
output:
  # Verbosity level: quiet, normal, verbose, debug
  verbosity: normal

  # Show progress bar
  show_progress: true

  # Color output
  use_color: true

  # Output format for CLI: table, json, yaml, csv
  format: table

  # Precision for floating point numbers
  precision: 3

  # Show statistical details
  show_statistics: true

  # Show environment metadata
  show_environment: false

# Export settings
export:
  # Default export format: json, csv, html, markdown
  default_format: json

  # Include raw measurements in export
  include_raw: false

  # Include metadata in export
  include_metadata: true

  # Pretty-print JSON
  json_indent: 2

  # CSV delimiter
  csv_delimiter: ","

  # HTML template (path to custom template)
  html_template: null

# Logging
logging:
  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  level: INFO

  # Log file path (null for no file logging)
  log_file: null

  # Log format
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

  # Log to console
  console: true

# Platform-specific overrides
platform_overrides:
  linux:
    # Linux-specific settings
    isolation:
      maximum:
        use_cgroups: true

  darwin:
    # macOS-specific settings
    metrics:
      io:
        enabled: false
        warn_if_unavailable: false

  windows:
    # Windows-specific settings
    shell:
      shell: cmd.exe
    metrics:
      io:
        enabled: false

# Custom metric collectors
custom_metrics:
  # Example custom metric
  # network_io:
  #   enabled: true
  #   module: my_metrics.network
  #   class: NetworkIOCollector
  #   config:
  #     interfaces: [eth0, wlan0]

# Plugins
plugins:
  # Plugin directory
  plugin_dir: ./plugins

  # Auto-load plugins
  auto_load: true

  # Enabled plugins
  enabled:
    # - my_custom_plugin
```

### TOML Format (Alternative)

**File:** `plainbench.toml`

```toml
# PlainBench Configuration

[general]
project_name = "My Project"
default_isolation = "moderate"
default_metrics = ["wall_time", "cpu_time", "python_memory", "process_memory", "disk_io"]

[execution]
warmup_runs = 3
measurement_runs = 10
disable_gc = true
timeout = 300
continue_on_error = true

[isolation.minimal]
enabled = true

[isolation.moderate]
cpu_affinity = [0, 1, 2, 3]
set_pythonhashseed = true
pythonhashseed_value = 0
disable_gc = true

[isolation.maximum]
use_docker = false
docker_image = "python:3.11-slim"
docker_cpus = 2.0
docker_memory = "4g"
docker_memory_swap = "4g"

[storage]
backend = "sqlite"
database_path = "./benchmarks.db"
store_raw_measurements = true
store_statistics = true
auto_vacuum = "INCREMENTAL"

[storage.sqlite]
journal_mode = "WAL"
synchronous = "NORMAL"
cache_size = -64000
temp_store = "MEMORY"

[git]
enabled = true
require_clean = false
store_diff = false

[metrics.timing]
enabled = true

[metrics.memory]
enabled = true
use_tracemalloc = true
use_psutil = true

[metrics.cpu]
enabled = true
sample_interval = 0.1

[metrics.io]
enabled = true
warn_if_unavailable = true

[shell]
shell = "/bin/bash"
capture_output = false
monitoring_mode = "continuous"
monitoring_interval = 0.1
timeout = 60

[statistics]
confidence_level = 0.95
alpha = 0.05
use_robust_stats = true
outlier_detection = "iqr"
outlier_threshold = 1.5
remove_outliers = false

[comparison]
regression_threshold = 0.05
memory_regression_threshold = 0.10
require_significance = true
method = "ttest"

[output]
verbosity = "normal"
show_progress = true
use_color = true
format = "table"
precision = 3
show_statistics = true
show_environment = false

[export]
default_format = "json"
include_raw = false
include_metadata = true
json_indent = 2
csv_delimiter = ","

[logging]
level = "INFO"
console = true
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

[platform_overrides.linux.isolation.maximum]
use_cgroups = true

[platform_overrides.darwin.metrics.io]
enabled = false
warn_if_unavailable = false

[platform_overrides.windows]
"shell.shell" = "cmd.exe"

[plugins]
plugin_dir = "./plugins"
auto_load = true
```

---

## Configuration Sections

### General Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `project_name` | string | null | Project name for reports |
| `default_isolation` | string | "minimal" | Default isolation level |
| `default_metrics` | list[string] | ["wall_time", "cpu_time", "python_memory"] | Metrics to collect |

### Execution Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `warmup_runs` | int | 3 | Number of warmup iterations |
| `measurement_runs` | int | 10 | Number of measurement iterations |
| `disable_gc` | bool | true | Disable GC during measurements |
| `timeout` | int | null | Timeout per benchmark (seconds) |
| `continue_on_error` | bool | true | Continue on benchmark failure |

### Isolation Settings

#### Minimal Isolation
No configuration needed. Uses standard subprocess isolation.

#### Moderate Isolation
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `cpu_affinity` | list[int] | null | CPU cores to pin to |
| `set_pythonhashseed` | bool | true | Set PYTHONHASHSEED |
| `pythonhashseed_value` | int | 0 | Value for PYTHONHASHSEED |
| `disable_gc` | bool | true | Disable garbage collection |

#### Maximum Isolation
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `use_docker` | bool | false | Use Docker containers |
| `docker_image` | string | "python:3.11-slim" | Docker image |
| `docker_cpus` | float | 2.0 | CPU limit |
| `docker_memory` | string | "4g" | Memory limit |
| `use_cgroups` | bool | false | Use cgroups (Linux) |
| `disable_turbo_boost` | bool | false | Disable Turbo Boost |
| `set_cpu_governor` | bool | false | Set CPU governor |

### Storage Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `backend` | string | "sqlite" | Storage backend |
| `database_path` | string | "./benchmarks.db" | Database file path |
| `store_raw_measurements` | bool | true | Store raw measurements |
| `store_statistics` | bool | true | Store aggregated statistics |

#### SQLite Specific
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `journal_mode` | string | "WAL" | Journal mode |
| `synchronous` | string | "NORMAL" | Synchronous mode |
| `cache_size` | int | -64000 | Cache size (negative = KB) |
| `temp_store` | string | "MEMORY" | Temp storage location |

### Git Integration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable git integration |
| `require_clean` | bool | false | Require clean working directory |
| `store_diff` | bool | false | Store git diff with results |

### Metrics Configuration

#### Timing
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable timing metrics |

#### Memory
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable memory metrics |
| `use_tracemalloc` | bool | true | Use tracemalloc |
| `use_psutil` | bool | true | Use psutil |

#### CPU
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable CPU metrics |
| `sample_interval` | float | 0.1 | Sample interval (seconds) |

#### I/O
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable I/O metrics |
| `warn_if_unavailable` | bool | true | Warn if unavailable |

### Statistics Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `confidence_level` | float | 0.95 | Confidence level |
| `alpha` | float | 0.05 | Alpha for hypothesis tests |
| `use_robust_stats` | bool | true | Use median/MAD vs mean/std |
| `outlier_detection` | string | "iqr" | Method: iqr, zscore, none |
| `outlier_threshold` | float | 1.5 | Threshold for outlier detection |
| `remove_outliers` | bool | false | Remove outliers |

### Comparison Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `regression_threshold` | float | 0.05 | Regression threshold (5%) |
| `memory_regression_threshold` | float | 0.10 | Memory regression (10%) |
| `require_significance` | bool | true | Require statistical significance |
| `method` | string | "ttest" | Comparison method |

### Output Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `verbosity` | string | "normal" | quiet, normal, verbose, debug |
| `show_progress` | bool | true | Show progress bar |
| `use_color` | bool | true | Color output |
| `format` | string | "table" | Output format |
| `precision` | int | 3 | Float precision |
| `show_statistics` | bool | true | Show statistics |
| `show_environment` | bool | false | Show environment metadata |

---

## Environment Variables

Environment variables override configuration file settings:

| Variable | Maps to | Example |
|----------|---------|---------|
| `PLAINBENCH_DATABASE` | `storage.database_path` | `export PLAINBENCH_DATABASE=/tmp/bench.db` |
| `PLAINBENCH_ISOLATION` | `general.default_isolation` | `export PLAINBENCH_ISOLATION=maximum` |
| `PLAINBENCH_WARMUP` | `execution.warmup_runs` | `export PLAINBENCH_WARMUP=5` |
| `PLAINBENCH_RUNS` | `execution.measurement_runs` | `export PLAINBENCH_RUNS=20` |
| `PLAINBENCH_VERBOSE` | `output.verbosity` | `export PLAINBENCH_VERBOSE=debug` |
| `PLAINBENCH_CONFIG` | Config file path | `export PLAINBENCH_CONFIG=./custom.yaml` |

---

## Configuration Precedence

Configuration is merged in the following order (later overrides earlier):

1. **Built-in defaults** (hardcoded in `config/defaults.py`)
2. **User-level config** (`~/.config/plainbench/config.yaml`)
3. **Project-level config** (`./plainbench.yaml`)
4. **Environment variables** (`PLAINBENCH_*`)
5. **CLI arguments** (`--warmup=5`)
6. **Decorator/function arguments** (`@benchmark(warmup=5)`)

### Example Precedence

```yaml
# ~/.config/plainbench/config.yaml
execution:
  warmup_runs: 5
```

```yaml
# ./plainbench.yaml
execution:
  warmup_runs: 10
```

```bash
# Environment variable
export PLAINBENCH_WARMUP=15

# CLI argument
plainbench run --warmup=20
```

**Result:** `warmup_runs = 20` (CLI argument wins)

---

## Examples

### Minimal Configuration

For quick local development:

```yaml
# plainbench.yaml
general:
  default_isolation: minimal

execution:
  warmup_runs: 1
  measurement_runs: 5

output:
  verbosity: quiet
```

### CI/CD Configuration

For reproducible CI/CD benchmarks:

```yaml
# plainbench.yaml
general:
  default_isolation: maximum

execution:
  warmup_runs: 3
  measurement_runs: 20
  continue_on_error: false

isolation:
  maximum:
    use_docker: true
    docker_cpus: 2.0
    docker_memory: "4g"

git:
  require_clean: true

comparison:
  regression_threshold: 0.03
  require_significance: true

output:
  verbosity: normal
  format: json
```

### Performance Testing Configuration

For detailed performance analysis:

```yaml
# plainbench.yaml
general:
  default_metrics:
    - wall_time
    - cpu_time
    - python_memory
    - process_memory
    - disk_io

execution:
  warmup_runs: 5
  measurement_runs: 50

statistics:
  use_robust_stats: true
  outlier_detection: iqr
  outlier_threshold: 1.5

output:
  show_statistics: true
  show_environment: true
  precision: 6
```

### Lightweight Configuration

Minimal overhead for fast feedback:

```yaml
# plainbench.yaml
general:
  default_metrics:
    - wall_time

execution:
  warmup_runs: 1
  measurement_runs: 3
  disable_gc: false

metrics:
  memory:
    enabled: false
  cpu:
    enabled: false
  io:
    enabled: false

storage:
  store_raw_measurements: false

output:
  show_progress: false
```

### Platform-Specific Configuration

Configuration with platform overrides:

```yaml
# plainbench.yaml
general:
  default_isolation: moderate

# Default settings
execution:
  warmup_runs: 3
  measurement_runs: 10

# Platform-specific overrides
platform_overrides:
  linux:
    # Use cgroups on Linux
    isolation:
      maximum:
        use_cgroups: true

    # Full I/O metrics
    metrics:
      io:
        enabled: true

  darwin:
    # macOS: disable I/O metrics
    metrics:
      io:
        enabled: false

    # Use Docker for maximum isolation
    isolation:
      maximum:
        use_docker: true

  windows:
    # Windows: use WSL shell
    shell:
      shell: wsl bash

    # Limited metrics
    metrics:
      io:
        enabled: false
```

---

## Configuration Validation

PlainBench validates configuration on load:

```python
from plainbench.config import BenchmarkConfig, ConfigValidationError

try:
    config = BenchmarkConfig.from_file('plainbench.yaml')
except ConfigValidationError as e:
    print(f"Configuration error: {e}")
    # Invalid values, missing required fields, etc.
```

### Validation Rules

1. **Type checking**: All values match expected types
2. **Range checking**: Numeric values within valid ranges
   - `warmup_runs >= 0`
   - `measurement_runs >= 1`
   - `0 < confidence_level < 1`
3. **Enum validation**: String values from allowed set
   - `isolation in ['minimal', 'moderate', 'maximum']`
   - `verbosity in ['quiet', 'normal', 'verbose', 'debug']`
4. **Path validation**: File paths exist and are accessible
5. **Platform compatibility**: Platform-specific settings are valid

---

## Schema Version

Configuration files can specify schema version for compatibility:

```yaml
# plainbench.yaml
schema_version: "1.0"

# ... rest of configuration
```

PlainBench will warn about version mismatches and provide migration guidance.

---

**End of Configuration Schema Document**
