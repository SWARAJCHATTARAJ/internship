"""SQLite persistence benchmarks against a temporary, isolated database."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from benchmarks.config import BenchmarkConfig, BenchmarkResult
from benchmarks.metrics import latency_summary, throughput
from benchmarks.resource_monitor import ResourceMonitor
from schemas.core import ReportState


def run(config: BenchmarkConfig) -> BenchmarkResult:
    from data.db import get_report, init_db, save_report

    result = BenchmarkResult("database")
    with tempfile.TemporaryDirectory(prefix="clinical-benchmark-db-") as directory:
        db_path = str(Path(directory) / "reports.sqlite3")
        started = time.perf_counter()
        init_db(db_path=db_path)
        initialization_seconds = time.perf_counter() - started
        insert_times: list[float] = []
        update_times: list[float] = []
        select_times: list[float] = []
        failures = 0
        states = [
            ReportState(
                document_id=f"BENCH-DB-{index:06d}",
                original_text=f"Isolated benchmark record {index}",
                summary="benchmark seed",
            )
            for index in range(config.documents)
        ]
        with ResourceMonitor() as monitor:
            for state in states:
                started = time.perf_counter()
                try:
                    save_report(state, db_path=db_path)
                except Exception as exc:
                    failures += 1
                    result.errors.append({"document_id": state.document_id, "operation": "insert", "error": str(exc)})
                insert_times.append(time.perf_counter() - started)

            for state in states:
                started = time.perf_counter()
                try:
                    save_report(state.model_copy(update={"summary": "updated benchmark record"}), db_path=db_path)
                except Exception as exc:
                    failures += 1
                    result.errors.append({"document_id": state.document_id, "operation": "update", "error": str(exc)})
                update_times.append(time.perf_counter() - started)

            for state in states:
                started = time.perf_counter()
                try:
                    found = get_report(state.document_id, db_path=db_path)
                    if found is None:
                        raise LookupError("record not found after write")
                except Exception as exc:
                    failures += 1
                    result.errors.append({"document_id": state.document_id, "operation": "select", "error": str(exc)})
                select_times.append(time.perf_counter() - started)

            bulk_started = time.perf_counter()
            bulk_failures = 0
            for index, state in enumerate(states):
                try:
                    save_report(state.model_copy(update={"document_id": f"BENCH-DB-BULK-{index:06d}"}), db_path=db_path)
                except Exception as exc:
                    bulk_failures += 1
                    result.errors.append({"document_id": state.document_id, "operation": "bulk_insert", "error": str(exc)})
            bulk_seconds = time.perf_counter() - bulk_started
            failures += bulk_failures
        result.resource_metrics.append({"suite": "database", **monitor.snapshot().as_dict()})

    operation_count = config.documents * 3 + config.documents
    result.metrics = {
        "backend": "SQLite",
        "database_scope": "temporary file; removed when the suite completes",
        "records": config.documents,
        "connection_initialization_seconds": initialization_seconds,
        "insert": latency_summary(insert_times),
        "update": latency_summary(update_times),
        "select": latency_summary(select_times),
        "sequential_bulk_insert_seconds": bulk_seconds,
        "sequential_bulk_insert_records_per_second": throughput(config.documents - bulk_failures, bulk_seconds),
        "bulk_insert_note": "Measured repeated application save_report calls; this is not a native SQL batch insert.",
        "operation_throughput": throughput(operation_count - failures, sum(insert_times + update_times + select_times) + bulk_seconds),
        "operation_failures": failures,
        "operation_failure_rate": failures / operation_count if operation_count else None,
    }
    result.warnings.append("PostgreSQL was not benchmarked; this suite intentionally uses the application's isolated SQLite path.")
    return result
