"""Shared configuration and result types for benchmark suites."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkConfig:
    mode: str = "mock"
    dataset: Path | None = None
    documents: int = 10
    workers: int = 1
    timeout: float = 30.0
    output_dir: Path = Path("benchmark_results")
    seed: int = 42

    def __post_init__(self) -> None:
        if self.mode not in {"mock", "real"}:
            raise ValueError("mode must be 'mock' or 'real'")
        if self.documents < 1:
            raise ValueError("documents must be at least 1")
        if self.workers < 1:
            raise ValueError("workers must be at least 1")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")


@dataclass
class BenchmarkResult:
    suite: str
    metrics: dict[str, Any] = field(default_factory=dict)
    details: list[dict[str, Any]] = field(default_factory=list)
    stage_timings: list[dict[str, Any]] = field(default_factory=list)
    resource_metrics: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "suite": self.suite,
            "metrics": self.metrics,
            "details": self.details,
            "stage_timings": self.stage_timings,
            "resource_metrics": self.resource_metrics,
            "warnings": self.warnings,
            "errors": self.errors,
        }
