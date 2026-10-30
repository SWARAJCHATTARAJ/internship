"""Annotated relation extraction and direction/classification evaluation."""

from __future__ import annotations

import time
from typing import Any

from benchmarks.common import as_state, documents_for, normalized, parse_ground_truth_list
from benchmarks.config import BenchmarkConfig, BenchmarkResult
from benchmarks.metrics import latency_summary, throughput
from benchmarks.resource_monitor import ResourceMonitor
from benchmarks.runtime import benchmark_runtime
from schemas.core import Relation


RELATION_TYPES = {
    "CAUSES", "TREATS", "INDICATES", "TEMPORAL_BEFORE", "TEMPORAL_AFTER",
    "HAS_DOSE", "HAS_FREQUENCY", "HAS_ROUTE", "HAS_DURATION",
}


def _text_for(reference: Any, entity_text: dict[str, str]) -> str | None:
    if reference is None:
        return None
    return normalized(entity_text.get(str(reference), reference))


def _gold_relation(item: Any, entity_text: dict[str, str]) -> tuple[str, str, str] | None:
    if not isinstance(item, dict):
        return None
    source = item.get("source") or item.get("subject") or item.get("source_text") or item.get("subject_text")
    target = item.get("target") or item.get("object") or item.get("target_text") or item.get("object_text")
    relation_type = str(item.get("relation_type") or item.get("type") or "").upper()
    if relation_type not in RELATION_TYPES or source is None or target is None:
        return None
    return (_text_for(source, entity_text) or "", relation_type, _text_for(target, entity_text) or "")


def run(config: BenchmarkConfig) -> BenchmarkResult:
    documents, source = documents_for(config)
    result = BenchmarkResult("relation")
    latencies: list[float] = []
    relation_tp = relation_fp = relation_fn = 0
    direction_correct = direction_total = type_correct = type_total = invalid_count = predicted_count = 0
    annotated_documents = 0

    with benchmark_runtime(config.mode, config.timeout), ResourceMonitor() as monitor:
        from agents.ner import ner_agent
        from agents.relation import relation_agent

        for document in documents:
            started = time.perf_counter()
            try:
                state = as_state(document)
                ner_result = ner_agent(state)
                state = state.model_copy(update={
                    "extracted_entities": ner_result["extracted_entities"],
                    "execution_plan": ["relation_agent"],
                })
                relation_result = relation_agent(state)
                entities = {entity.id: entity.text for entity in state.extracted_entities}
                predictions = relation_result["relations"]
                predicted_count += len(predictions)
                valid: list[tuple[str, str, str]] = []
                for relation in predictions:
                    if not isinstance(relation, Relation) or relation.relation_type not in RELATION_TYPES:
                        invalid_count += 1
                        continue
                    if relation.source_entity_id not in entities or relation.target_entity_id not in entities:
                        invalid_count += 1
                        continue
                    valid.append((
                        normalized(entities[relation.source_entity_id]) or "",
                        relation.relation_type,
                        normalized(entities[relation.target_entity_id]) or "",
                    ))
                if "relations" in document.ground_truth:
                    expected = parse_ground_truth_list(
                        document.ground_truth["relations"], field_name="relations",
                        document_id=document.document_id,
                    )
                    gold = [_gold_relation(item, entities) for item in expected]
                    gold = [item for item in gold if item is not None]
                    if len(gold) != len(expected):
                        result.warnings.append(
                            f"{document.document_id}: some relation annotations lack source/target text or a supported type."
                        )
                    annotated_documents += 1
                    gold_set, predicted_set = set(gold), set(valid)
                    relation_tp += len(gold_set & predicted_set)
                    relation_fp += len(predicted_set - gold_set)
                    relation_fn += len(gold_set - predicted_set)
                    gold_pairs = {(item[0], item[2]): item[1] for item in gold}
                    predicted_pairs = {(item[0], item[2]): item[1] for item in valid}
                    direction_correct += len(set(gold_pairs) & set(predicted_pairs))
                    direction_total += len(gold_pairs)
                    for pair in set(gold_pairs) & set(predicted_pairs):
                        type_total += 1
                        type_correct += int(gold_pairs[pair] == predicted_pairs[pair])
                latency = time.perf_counter() - started
                latencies.append(latency)
                result.details.append({
                    "document_id": document.document_id, "relations_predicted": len(predictions),
                    "latency_seconds": latency,
                    "ground_truth_available": "relations" in document.ground_truth,
                })
            except Exception as exc:
                latencies.append(time.perf_counter() - started)
                result.errors.append({"document_id": document.document_id, "error": str(exc)})

    if config.mode == "mock":
        result.warnings.append("Mock mode uses deterministic relation fallback rules, which can assert broad medication-condition links.")
    if not annotated_documents:
        relation_precision = relation_recall = relation_f1 = None
    else:
        relation_precision = relation_tp / (relation_tp + relation_fp) if relation_tp + relation_fp else 0.0
        relation_recall = relation_tp / (relation_tp + relation_fn) if relation_tp + relation_fn else 0.0
        relation_f1 = 2 * relation_precision * relation_recall / (relation_precision + relation_recall) if relation_precision + relation_recall else 0.0
    elapsed = sum(latencies)
    result.resource_metrics.append({"suite": "relation", **monitor.snapshot().as_dict()})
    result.metrics = {
        "precision": relation_precision, "recall": relation_recall, "f1": relation_f1,
        "subject_object_direction_accuracy": direction_correct / direction_total if direction_total else None,
        "relation_classification_accuracy": type_correct / type_total if type_total else None,
        "invalid_relation_rate": invalid_count / predicted_count if predicted_count else 0.0,
        "invalid_relations": invalid_count, "relations_predicted": predicted_count,
        "documents": len(documents), "annotated_documents": annotated_documents,
        "accuracy_metrics_available": annotated_documents > 0,
        "average_seconds_per_document": elapsed / len(latencies) if latencies else None,
        "latency": latency_summary(latencies),
        "relations_per_second": throughput(predicted_count, elapsed),
        "dataset_source": source,
    }
    if not annotated_documents:
        result.warnings.append("No annotated relations found; relation accuracy metrics are unavailable.")
    return result
