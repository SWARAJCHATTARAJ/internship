"""Exact-match entity evaluation for the clinical NER agent."""

from __future__ import annotations

import time
from collections import Counter
from typing import Any

from benchmarks.common import as_state, documents_for, parse_ground_truth_list
from benchmarks.config import BenchmarkConfig, BenchmarkResult
from benchmarks.metrics import entity_metrics, latency_summary, throughput
from benchmarks.resource_monitor import ResourceMonitor
from benchmarks.runtime import benchmark_runtime


ENTITY_LABELS = {
    "MEDICATION", "DIAGNOSIS", "PROCEDURE", "LAB_RESULT", "SYMPTOM",
    "ANATOMY", "DOSAGE", "FREQUENCY", "ROUTE", "DURATION",
}


def _scores(counts: Counter[str]) -> dict[str, float | int | None]:
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else (0.0 if precision == 0 or recall == 0 else None)
    )
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def run(config: BenchmarkConfig) -> BenchmarkResult:
    documents, source = documents_for(config)
    result = BenchmarkResult("ner")
    latencies: list[float] = []
    micro_counts: Counter[str] = Counter()
    per_label_counts: dict[str, Counter[str]] = {
        label: Counter() for label in ENTITY_LABELS
    }
    annotated_docs = extracted = word_count = 0

    with benchmark_runtime(config.mode, config.timeout), ResourceMonitor() as monitor:
        from agents.ner import ner_agent

        for document in documents:
            started = time.perf_counter()
            try:
                output = ner_agent(as_state(document))
                predictions = [entity.model_dump() for entity in output["extracted_entities"]]
                extracted += len(predictions)
                word_count += len(document.text.split())
                expected = parse_ground_truth_list(
                    document.ground_truth.get("entities"), field_name="entities",
                    document_id=document.document_id,
                ) if "entities" in document.ground_truth else None
                if expected is not None:
                    invalid = [item for item in expected if not isinstance(item, dict)
                               or str(item.get("label", item.get("type", ""))).upper() not in ENTITY_LABELS]
                    if invalid:
                        result.warnings.append(
                            f"{document.document_id}: ignored {len(invalid)} annotations with missing/unsupported labels."
                        )
                    expected = [
                        {**item, "label": str(item.get("label", item.get("type", ""))).upper()}
                        for item in expected if isinstance(item, dict)
                        and str(item.get("label", item.get("type", ""))).upper() in ENTITY_LABELS
                    ]
                    predicted_valid = [item for item in predictions
                                       if item.get("label") in ENTITY_LABELS]
                    annotated_docs += 1
                    document_counts = entity_metrics(expected, predicted_valid, document.text)
                    for key in ("tp", "fp", "fn"):
                        micro_counts[key] += document_counts[key]
                    for label in ENTITY_LABELS:
                        label_gold = [item for item in expected if item["label"] == label]
                        label_predicted = [item for item in predicted_valid if item["label"] == label]
                        label_counts = entity_metrics(label_gold, label_predicted, document.text)
                        for key in ("tp", "fp", "fn"):
                            per_label_counts[label][key] += label_counts[key]
                latency = time.perf_counter() - started
                latencies.append(latency)
                result.details.append({
                    "document_id": document.document_id, "entities_predicted": len(predictions),
                    "latency_seconds": latency, "ground_truth_available": expected is not None,
                })
            except Exception as exc:
                latencies.append(time.perf_counter() - started)
                result.errors.append({"document_id": document.document_id, "error": str(exc)})

    result.resource_metrics.append({"suite": "ner", **monitor.snapshot().as_dict()})
    aggregate = _scores(micro_counts) if annotated_docs else {
        "precision": None, "recall": None, "f1": None, "tp": None, "fp": None, "fn": None,
    }
    per_entity = {
        label: _scores(per_label_counts[label])
        for label in sorted(ENTITY_LABELS)
        if sum(per_label_counts[label].values()) > 0
    } if annotated_docs else {}
    macro_scores = {
        key: [value[key] for value in per_entity.values() if value[key] is not None]
        for key in ("precision", "recall", "f1")
    }
    total_time = sum(latencies)
    result.metrics = {
        **aggregate,
        "micro_precision": aggregate["precision"],
        "micro_recall": aggregate["recall"],
        "micro_f1": aggregate["f1"],
        "macro_precision": sum(macro_scores["precision"]) / len(macro_scores["precision"]) if macro_scores["precision"] else None,
        "macro_recall": sum(macro_scores["recall"]) / len(macro_scores["recall"]) if macro_scores["recall"] else None,
        "macro_f1": sum(macro_scores["f1"]) / len(macro_scores["f1"]) if macro_scores["f1"] else None,
        "per_entity": per_entity,
        "documents": len(documents),
        "annotated_documents": annotated_docs,
        "accuracy_metrics_available": annotated_docs > 0,
        "average_extraction_seconds": total_time / len(latencies) if latencies else None,
        "entities_per_second": throughput(extracted, total_time),
        "latency": latency_summary(latencies),
        "entities_predicted": extracted,
        "words_processed": word_count,
        "dataset_source": source,
        "matching": "Exact labeled span when offsets are supplied; otherwise exact case-insensitive entity text.",
    }
    if not annotated_docs:
        result.warnings.append("No entity ground truth found; precision, recall, and F1 are unavailable.")
    return result
