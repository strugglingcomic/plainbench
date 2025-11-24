"""Configuration settings for PlainBench."""

import os
from typing import List, Optional

try:
    from pydantic import BaseModel, Field, field_validator
    PYDANTIC_V2 = True
except ImportError:
    try:
        from pydantic import BaseModel, Field
        from pydantic import validator as field_validator
        PYDANTIC_V2 = False
    except ImportError:
        # Fallback to dataclass if pydantic is not available
        from dataclasses import dataclass
        BaseModel = None


if BaseModel:

    class BenchmarkConfig(BaseModel):
        """Configuration for benchmark execution."""

        default_warmup: int = Field(
            default=3, description="Default number of warmup iterations", ge=0
        )
        default_runs: int = Field(
            default=10, description="Default number of measurement runs", gt=0
        )
        default_isolation: str = Field(
            default="minimal",
            description="Default isolation level (minimal, moderate, maximum)",
        )
        default_metrics: List[str] = Field(
            default_factory=lambda: ["wall_time", "cpu_time", "python_memory"],
            description="Default metrics to collect",
        )
        database_path: str = Field(
            default="./benchmarks.db", description="Path to SQLite database"
        )
        cpu_affinity: Optional[List[int]] = Field(
            default=None, description="CPU cores for pinning (moderate/maximum isolation)"
        )
        disable_gc: bool = Field(
            default=True, description="Disable garbage collection during measurement"
        )
        regression_threshold: float = Field(
            default=0.05,
            description="Threshold for detecting performance regressions (5%)",
            gt=0,
            lt=1,
        )

        if PYDANTIC_V2:

            @field_validator("default_isolation")
            @classmethod
            def validate_isolation(cls, v):
                """Validate isolation level."""
                allowed = ["minimal", "moderate", "maximum"]
                if v not in allowed:
                    raise ValueError(f"Isolation must be one of {allowed}, got {v}")
                return v

        else:

            @field_validator("default_isolation")
            @classmethod
            def validate_isolation(cls, v):
                """Validate isolation level."""
                allowed = ["minimal", "moderate", "maximum"]
                if v not in allowed:
                    raise ValueError(f"Isolation must be one of {allowed}, got {v}")
                return v

        @staticmethod
        def get_default_database() -> str:
            """Get default database path."""
            return os.environ.get("PLAINBENCH_DATABASE", "./benchmarks.db")

        @staticmethod
        def from_env() -> "BenchmarkConfig":
            """Create config from environment variables."""
            config = BenchmarkConfig()

            # Override with environment variables
            if "PLAINBENCH_WARMUP" in os.environ:
                config = BenchmarkConfig(
                    **{**config.dict(), "default_warmup": int(os.environ["PLAINBENCH_WARMUP"])}
                )

            if "PLAINBENCH_RUNS" in os.environ:
                config = BenchmarkConfig(
                    **{**config.dict(), "default_runs": int(os.environ["PLAINBENCH_RUNS"])}
                )

            if "PLAINBENCH_ISOLATION" in os.environ:
                config = BenchmarkConfig(
                    **{
                        **config.dict(),
                        "default_isolation": os.environ["PLAINBENCH_ISOLATION"],
                    }
                )

            if "PLAINBENCH_DATABASE" in os.environ:
                config = BenchmarkConfig(
                    **{**config.dict(), "database_path": os.environ["PLAINBENCH_DATABASE"]}
                )

            return config

    class MockConfig(BaseModel):
        """Base configuration for mock data stores."""

        enabled: bool = Field(default=True, description="Enable mock data store")
        database: str = Field(
            default=":memory:", description="SQLite database path for mock"
        )
        shared_database: bool = Field(
            default=False,
            description="Share database across test runs (persistence)",
        )

    class PostgresMockConfig(MockConfig):
        """Configuration for mock Postgres."""

        sql_dialect_translation: bool = Field(
            default=True, description="Translate Postgres SQL to SQLite"
        )
        autocommit: bool = Field(default=False, description="Enable autocommit mode")

    class KafkaMockConfig(MockConfig):
        """Configuration for mock Kafka."""

        default_partitions: int = Field(
            default=1, description="Default number of partitions per topic", gt=0
        )
        enable_transactions: bool = Field(
            default=False, description="Enable Kafka transactions (not yet implemented)"
        )
        auto_offset_reset: str = Field(
            default="earliest",
            description="Where to start consuming ('earliest' or 'latest')",
        )

    class RedisMockConfig(MockConfig):
        """Configuration for mock Redis."""

        enable_ttl: bool = Field(
            default=True, description="Enable TTL/expiration support"
        )
        decode_responses: bool = Field(
            default=False, description="Decode byte responses to strings"
        )

else:
    # Fallback dataclass implementation
    from dataclasses import dataclass

    @dataclass
    class BenchmarkConfig:
        """Configuration for benchmark execution."""

        default_warmup: int = 3
        default_runs: int = 10
        default_isolation: str = "minimal"
        default_metrics: List[str] = None
        database_path: str = "./benchmarks.db"
        cpu_affinity: Optional[List[int]] = None
        disable_gc: bool = True
        regression_threshold: float = 0.05

        def __post_init__(self):
            if self.default_metrics is None:
                self.default_metrics = ["wall_time", "cpu_time", "python_memory"]

        @staticmethod
        def get_default_database() -> str:
            """Get default database path."""
            return os.environ.get("PLAINBENCH_DATABASE", "./benchmarks.db")

        @staticmethod
        def from_env() -> "BenchmarkConfig":
            """Create config from environment variables."""
            return BenchmarkConfig(
                default_warmup=int(os.environ.get("PLAINBENCH_WARMUP", 3)),
                default_runs=int(os.environ.get("PLAINBENCH_RUNS", 10)),
                default_isolation=os.environ.get("PLAINBENCH_ISOLATION", "minimal"),
                database_path=os.environ.get("PLAINBENCH_DATABASE", "./benchmarks.db"),
            )

    @dataclass
    class MockConfig:
        """Base configuration for mock data stores."""

        enabled: bool = True
        database: str = ":memory:"
        shared_database: bool = False

    @dataclass
    class PostgresMockConfig(MockConfig):
        """Configuration for mock Postgres."""

        sql_dialect_translation: bool = True
        autocommit: bool = False

    @dataclass
    class KafkaMockConfig(MockConfig):
        """Configuration for mock Kafka."""

        default_partitions: int = 1
        enable_transactions: bool = False
        auto_offset_reset: str = "earliest"

    @dataclass
    class RedisMockConfig(MockConfig):
        """Configuration for mock Redis."""

        enable_ttl: bool = True
        decode_responses: bool = False
