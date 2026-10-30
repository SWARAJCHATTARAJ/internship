"""Medication name, attribute, and complete-record evaluation."""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from typing import Any

from benchmarks.common import as_state, documents_for, normalized, parse_ground_truth_list
from benchmarks.config import BenchmarkConfig, BenchmarkResult
from benchmarks.metrics import latency_summary, throughput
from benchmarks.resource_monitor import ResourceMonitor
from benchmarks.runtime import benchmark_runtime
from schemas.core import ReportState


_ATTRIBUTES = ("dose", "frequency", "route", "duration")


def _record_key(record: dict[str, Any]) -> str | None:
    return normalized(record.get("drug") or record.get("name") or record.get("medication"))


def _matched_records(expected: list[Any], predicted: list[Any]) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    queues: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in predicted:
        if isinstance(record, dict) and _record_key(record):
            queues[_record_key(record)].append(record)
    pairs = []
    for gold in expected:
        if not isinstance(gold, dict):
            continue
        key = _record_key(gold)
        pairs.append((gold, queues[key].pop(0) if key and queues[key] else None))
    return pairs


def run(config: BenchmarkConfig) -> BenchmarkResult:
    documents, source = documents_for(config)
    result = BenchmarkResult("medication")
    latencies: list[float] = []
    name_tp = name_fp = name_fn = 0
    attribute_matches = Counter()
    attribute_total = Counter()
    complete_matches = complete_total = normalized_matches = normalized_total = 0
    annotated_documents = count = 0

    with benchmark_runtime(config.mode, config.timeout), ResourceMonitor() as monitor:
        from agents.medication import medication_agent
        from agents.ner import ner_agent

        for document in documents:
            started = time.perf_counter()
            try:
                state = as_state(document)
                extraction = ner_agent(state)
                state = state.model_copy(update={"extracted_entities": extraction["extracted_entities"]})
                output = medication_agent(state)
                predicted = [record.model_dump() for record in output["medications"]]
                count += len(predicted)
                if "medications" in document.ground_truth:
                    expected = parse_ground_truth_list(
                        document.ground_truth["medications"], field_name="medications",
                        document_id=document.document_id,
                    )
                    expected = [record for record in expected if isinstance(record, dict) and _record_key(record)]
                    annotated_documents += 1
                    gold_names = Counter(_record_key(record) for record in expected)
                    found_names = Counter(_record_key(record) for record in predicted)
                    name_tp += sum((gold_names & found_names).values())
                    name_fp += sum((found_names - gold_names).values())
                    name_fn += sum((gold_names - found_names).values())
                    pairs = _matched_records(expected, predicted)
                    for gold, found in pairs:
                        normalized_total += 1
                        normalized_matches += int(found is not None)
                        complete_total += 1
                        is_complete = found is not None
                        for attribute in _ATTRIBUTES:
                            if attribute not in gold:
                                continue
                            attribute_total[attribute] += 1
                            match = found is not None and normalized(found.get(attribute)) == normalized(gold.get(attribute))
                            attribute_matches[attribute] += int(match)
                            is_complete = is_complete and match
                        complete_matches += int(is_complete)
                elapsed = time.perf_counter() - started
                latencies.append(elapsed)
                result.details.append({
                    "document_id": document.document_id, "medications_predicted": len(predicted),
                    "latency_seconds": elapsed,
                    "ground_truth_available": "medications" in document.ground_truth,
                })
            except Exception as exc:
                latencies.append(time.perf_counter() - started)
                result.errors.append({"document_id": document.document_id, "error": str(exc)})

    precision = name_tp / (name_tp + name_fp) if name_tp + name_fp else (0.0 if annotated_documents else None)
    recall = name_tp / (name_tp + name_fn) if name_tp + name_fn else (0.0 if annotated_documents else None)
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else (0.0 if precision == 0 or recall == 0 else None)
    total_time = sum(latencies)
    result.resource_metrics.append({"suite": "medication", **monitor.snapshot().as_dict()})
    result.metrics = {
        "medication_name_precision": precision,
        "medication_name_recall": recall,
        "medication_name_f1": f1,
        "attribute_accuracy": {
            attribute: attribute_matches[attribute] / attribute_total[attribute] if attribute_total[attribute] else None
            for attribute in _ATTRIBUTES
        },
        "normalization_accuracy": normalized_matches / normalized_total if normalized_total else None,
        "complete_record_accuracy": complete_matches / complete_total if complete_total else None,
        "documents": len(documents), "annotated_documents": annotated_documents,
        "accuracy_metrics_available": annotated_documents > 0,
        "medication_records_predicted": count,
        "average_latency_seconds": total_time / len(latencies) if latencies else None,
        "latency": latency_summary(latencies),
        "records_per_second": throughput(count, total_time),
        "dataset_source": source,
    }
    if not annotated_documents:
        result.warnings.append("No medication ground truth found; accuracy metrics are unavailable.")
    if any(attribute_total[field] == 0 for field in _ATTRIBUTES):
        result.warnings.append("Dosage/frequency/route/duration accuracy is N/A where annotations omit that attribute.")
    return result
