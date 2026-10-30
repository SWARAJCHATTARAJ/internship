"""Command-line entry point for reproducible benchmark suites."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Callable

from benchmarks.config import BenchmarkConfig, BenchmarkResult
from benchmarks.report_generator import generate_reports


SUITES: dict[str, tuple[str, str]] = {
    "ocr": ("benchmarks.benchmark_ocr", "run"),
    "ner": ("benchmarks.benchmark_ner", "run"),
    "medication": ("benchmarks.benchmark_medication", "run"),
    "relation": ("benchmarks.benchmark_relation", "run"),
    "grounding": ("benchmarks.benchmark_grounding", "run"),
    "verification": ("benchmarks.benchmark_verification", "run"),
    "pipeline": ("benchmarks.benchmark_pipeline", "run"),
    "api": ("benchmarks.benchmark_api", "run"),
    "database": ("benchmarks.benchmark_database", "run"),
    "load": ("benchmarks.benchmark_load", "run"),
}


def _load_suite(module_name: str, function_name: str) -> Callable[[BenchmarkConfig], BenchmarkResult]:
    from importlib import import_module

    return getattr(import_module(module_name), function_name)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark the clinical multi-agent application.")
    parser.add_argument("--all", action="store_true", help="Run all benchmark suites.")
    for suite in SUITES:
        parser.add_argument(f"--{suite}", action="store_true", help=f"Run the {suite} suite.")
    parser.add_argument("--dataset", type=Path, help="CSV/JSON/JSONL manifest or dataset directory.")
    parser.add_argument("--documents", type=int, default=10, help="Maximum documents or workload size.")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent clients/workers where safe.")
    parser.add_argument("--mode", choices=("mock", "real"), default="mock", help="Mock/offline or real model mode.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-request/API timeout in seconds.")
    parser.add_argument("--seed", type=int, default=42, help="Reproducible workload sampling seed.")
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark_results"))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    selected = list(SUITES) if args.all else [name for name in SUITES if getattr(args, name)]
    if not selected:
        parser.error("Select at least one suite or use --all.")
    try:
        config = BenchmarkConfig(
            mode=args.mode,
            dataset=args.dataset,
            documents=args.documents,
            workers=args.workers,
            timeout=args.timeout,
            output_dir=args.output_dir,
            seed=args.seed,
        )
    except ValueError as exc:
        parser.error(str(exc))
    random.seed(config.seed)
    if config.mode == "real":
        print("Real mode may download model weights or call external APIs; these operations may be slow or billable.", file=sys.stderr)

    results: list[BenchmarkResult] = []
    dataset_source = str(config.dataset) if config.dataset else "default synthetic text fixture or suite-specific input"
    suite_errors = 0
    for name in selected:
        module_name, function_name = SUITES[name]
        print(f"Running {name} benchmark ({config.mode})...")
        try:
            results.append(_load_suite(module_name, function_name)(config))
        except Exception as exc:
            suite_errors += 1
            results.append(BenchmarkResult(name, errors=[{"error": f"{type(exc).__name__}: {exc}"}]))
            print(f"{name} benchmark failed: {exc}", file=sys.stderr)

    try:
        output = generate_reports(results, config, dataset_source=dataset_source)
    except Exception as exc:
        print(f"Report generation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Benchmark reports written to: {output.resolve()}")
    for result in results:
        print(f"- {result.suite}: {result.metrics}")
    return 1 if suite_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
