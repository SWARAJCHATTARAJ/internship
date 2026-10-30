"""Evaluation against explicitly curated ontology reference mappings."""

from __future__ import annotations

import time
from typing import Any

from benchmarks.common import as_state, documents_for, normalized, parse_ground_truth_list
from benchmarks.config import BenchmarkConfig, BenchmarkResult
from benchmarks.metrics import mean_reciprocal_rank, percentile, recall_at_k, throughput
from benchmarks.resource_monitor import ResourceMonitor
from benchmarks.runtime import benchmark_runtime


def _expected_mappings(document: Any) -> list[dict[str, Any]]:
    value = document.ground_truth.get("expected_grounding", document.ground_truth.get("grounding"))
    if value is None:
        return []
    return [item for item in parse_ground_truth_list(
        value, field_name="grounding", document_id=document.document_id
    ) if isinstance(item, dict)]


def _reference_code(item: dict[str, Any]) -> str | None:
    concept = item.get("concept") if isinstance(item.get("concept"), dict) else item
    return normalized(concept.get("code") or concept.get("id"))


def _rank_candidates(texts: list[str]) -> tuple[list[list[dict[str, Any]]] | None, str | None]:
    """Reproduce the production cosine-ranking path to expose ranks for evaluation."""
    try:
        from tools.ontology_index import _load_seed_entries
        from tools.hf_models import get_embedding_model

        entries = _load_seed_entries()
        if not entries:
            return None, "ontology seed dataset is empty"
        model = get_embedding_model()
        documents = [f"{entry.get('name', '')} {entry.get('description', '')}" for entry in entries]
        document_vectors = model.encode(documents, normalize_embeddings=True, show_progress_bar=False)
        query_vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        ranked = []
        for vector in query_vectors:
            scores = document_vectors @ vector
            order = scores.argsort()[::-1]
            ranked.append([entries[int(index)] for index in order])
        return ranked, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def run(config: BenchmarkConfig) -> BenchmarkResult:
    documents, source = documents_for(config)
    result = BenchmarkResult("grounding")
    latencies: list[float] = []
    top1_hits = exact_hits = semantic_hits = mapped = total_entities = 0
    rank_lists: list[list[str]] = []
    relevant_codes: list[str] = []
    annotated = 0
    reference_texts: list[str] = []
    reference_codes: list[str] = []
    with benchmark_runtime(config.mode, config.timeout), ResourceMonitor() as monitor:
        from agents.grounding import grounding_agent
        from agents.ner import ner_agent

        for document in documents:
            started = time.perf_counter()
            try:
                extraction = ner_agent(as_state(document))
                state = as_state(document).model_copy(update={"extracted_entities": extraction["extracted_entities"]})
                grounded = grounding_agent(state)
                output_entities = grounded["extracted_entities"]
                total_entities += len(output_entities)
                mapped += sum(entity.grounding is not None for entity in output_entities)
                expected = _expected_mappings(document)
                if expected:
                    entity_by_text = {normalized(entity.text): entity for entity in output_entities}
                    for reference in expected:
                        entity_text = normalized(reference.get("entity") or reference.get("text") or reference.get("query"))
                        wanted = _reference_code(reference)
                        if not wanted or not entity_text:
                            result.warnings.append(f"{document.document_id}: ignored incomplete grounding annotation.")
                            continue
                        annotated += 1
                        reference_texts.append(str(reference.get("entity") or reference.get("text") or reference.get("query")))
                        reference_codes.append(wanted)
                        entity = entity_by_text.get(entity_text)
                        predicted_code = normalized(entity.grounding.code) if entity and entity.grounding else None
                        top1_hits += int(predicted_code == wanted)
                        exact_hits += int(predicted_code == wanted)
                        reference_name = normalized(
                            reference.get("name")
                            or (reference.get("concept", {}).get("name") if isinstance(reference.get("concept"), dict) else None)
                        )
                        semantic_hits += int(predicted_code == wanted or (
                            reference_name is not None and entity is not None and entity.grounding is not None
                            and normalized(entity.grounding.name) == reference_name
                        ))
                latency = time.perf_counter() - started
                latencies.append(latency)
                result.details.append({
                    "document_id": document.document_id,
                    "entities": len(output_entities),
                    "mapped_entities": sum(entity.grounding is not None for entity in output_entities),
                    "latency_seconds": latency,
                    "ground_truth_available": bool(expected),
                })
            except Exception as exc:
                latencies.append(time.perf_counter() - started)
                result.errors.append({"document_id": document.document_id, "error": str(exc)})

    exact_references = annotated
    if config.mode == "real" and annotated:
        candidate_lists, ranking_error = _rank_candidates(reference_texts)
        if candidate_lists is not None:
            rank_lists = [[str(item.get("code", "")) for item in candidates] for candidates in candidate_lists]
            relevant_codes = reference_codes
        else:
            result.warnings.append(
                f"Recall@5/10 and MRR are unavailable because candidate ranking could not be loaded: {ranking_error}"
            )
    elapsed = sum(latencies)
    result.resource_metrics.append({"suite": "grounding", **monitor.snapshot().as_dict()})
    result.metrics = {
        "top1_accuracy": top1_hits / exact_references if exact_references else None,
        "fallback_top1_accuracy": top1_hits / exact_references if exact_references and config.mode == "mock" else None,
        "exact_match_accuracy": exact_hits / exact_references if exact_references else None,
        "semantic_match_accuracy": semantic_hits / exact_references if exact_references else None,
        "semantic_match_definition": "Reference code match or exact normalized concept-name match; no semantic equivalence is inferred.",
        "recall_at_5": recall_at_k(rank_lists, relevant_codes, 5) if rank_lists else None,
        "recall_at_10": recall_at_k(rank_lists, relevant_codes, 10) if rank_lists else None,
        "mean_reciprocal_rank": mean_reciprocal_rank(rank_lists, relevant_codes) if rank_lists else None,
        "top_k_accuracy": {
            "top_1": top1_hits / exact_references if exact_references else None,
            "top_5": recall_at_k(rank_lists, relevant_codes, 5) if rank_lists else None,
            "top_10": recall_at_k(rank_lists, relevant_codes, 10) if rank_lists else None,
        },
        "grounding_latency_seconds": sum(latencies) / len(latencies) if latencies else None,
        "grounding_latency_p95_seconds": percentile(latencies, 95),
        "unmapped_entity_percentage": (total_entities - mapped) / total_entities * 100 if total_entities else None,
        "mapped_entities": mapped, "entities": total_entities,
        "annotated_mappings": annotated, "accuracy_metrics_available": annotated > 0,
        "grounding_mode": "deterministic fallback" if config.mode == "mock" else "configured retrieval path",
        "documents": len(documents), "groundings_per_second": throughput(total_entities, elapsed),
        "dataset_source": source,
    }
    if config.mode == "mock":
        result.warnings.append("Mock mode bypasses embedding retrieval; top-1 scores describe only deterministic fallback mappings and rank metrics are unavailable.")
        result.metrics.update({
            "recall_at_5": None,
            "recall_at_10": None,
            "mean_reciprocal_rank": None,
            "top_k_accuracy": {
                "top_1": top1_hits / exact_references if exact_references else None,
                "top_5": None,
                "top_10": None,
            },
        })
    elif not annotated:
        result.warnings.append("No manually verified reference mappings found; grounding accuracy metrics are unavailable.")
    return result
