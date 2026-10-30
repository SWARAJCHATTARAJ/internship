"""Configurable concurrent graph workload using isolated in-memory report states."""

from __future__ import annotations

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from benchmarks.common import documents_for
from benchmarks.config import BenchmarkConfig, BenchmarkResult
from benchmarks.metrics import latency_summary, success_rate, throughput
from benchmarks.resource_monitor import ResourceMonitor
from benchmarks.runtime import benchmark_runtime
from schemas.core import ReportState


def run(config: BenchmarkConfig) -> BenchmarkResult:
    result = BenchmarkResult("load")
    source_documents, source = documents_for(config)
    if not source_documents:
        result.warnings.append("No workload documents found.")
        return result
    workers = config.workers
    if config.mode == "real" and workers > 1:
        workers = 1
        result.warnings.append("Real model/API load is constrained to one worker to avoid concurrent external costs.")
    rng = random.Random(config.seed)
    documents = [
        source_documents[rng.randrange(len(source_documents))]
        for _ in range(config.documents)
    ]
    states = [
        ReportState(
            document_id=f"BENCH-LOAD-{index:06d}",
            original_text=document.text,
        )
        for index, document in enumerate(documents)
    ]
    latencies: list[float] = []
    successes = failures = 0

    started = time.perf_counter()
    with benchmark_runtime(config.mode, config.timeout), ResourceMonitor() as monitor:
        from agents.orchestrator import graph

        def process(state: ReportState) -> tuple[float, Exception | None, int, int]:
            started = time.perf_counter()
            try:
                output = graph.invoke(state)
                return time.perf_counter() - started, None, len(output["extracted_entities"]), len(output["relations"])
            except Exception as exc:
                return time.perf_counter() - started, exc, 0, 0

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(process, state) for state in states]
            entity_count = relation_count = 0
            for index, future in enumerate(as_completed(futures)):
                latency, error, found_entities, found_relations = future.result()
                latencies.append(latency)
                if error is None:
                    successes += 1
                    entity_count += found_entities
                    relation_count += found_relations
                else:
                    failures += 1
                    result.errors.append({"document_index": str(index), "error": str(error)})
    elapsed = time.perf_counter() - started
    result.resource_metrics.append({"suite": "load", **monitor.snapshot().as_dict()})
    result.metrics = {
        "documents_requested": config.documents,
        "workers": workers,
        "elapsed_seconds": elapsed,
        "throughput_documents_per_second": throughput(successes, elapsed),
        "average_latency_seconds": sum(latencies) / len(latencies) if latencies else None,
        **latency_summary(latencies),
        "successful_documents": successes,
        "failed_documents": failures,
        "failure_rate": 1 - success_rate(successes, len(states)) if states else None,
        "cpu_usage_percent": monitor.snapshot().process_cpu_percent,
        "ram_usage_percent": monitor.snapshot().system_ram_percent,
        "peak_process_memory_mb": monitor.snapshot().peak_process_memory_mb,
        "entities_per_document": entity_count / successes if successes else None,
        "relations_per_document": relation_count / successes if successes else None,
        "dataset_source": source,
        "seed": config.seed,
    }
    if config.mode == "mock":
        result.warnings.append("Mock workload disables pretrained/external models and does not persist reports.")
    else:
        result.warnings.append("Real models may download weights or invoke paid external services; use a small workload first.")
    return result
