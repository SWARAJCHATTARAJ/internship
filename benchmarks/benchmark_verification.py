"""Evaluate observable verifier flags against explicitly labeled test cases."""

from __future__ import annotations

import time

from benchmarks.common import documents_for
from benchmarks.config import BenchmarkConfig, BenchmarkResult
from benchmarks.metrics import latency_summary
from benchmarks.resource_monitor import ResourceMonitor
from benchmarks.runtime import benchmark_runtime
from schemas.core import ReportState


FLAG_TYPES = {
    "DRUG_PLAUSIBILITY", "LAB_RANGE", "DIAGNOSIS_ENTAILMENT", "FHIR_SCHEMA",
    "OCR_UNCERTAINTY", "DOSAGE_CONTRADICTION", "UNSUPPORTED_CLAIM",
}


def _expected_types(value: Any) -> set[str]:
    if not isinstance(value, list):
        raise ValueError("expected_flags must be a list")
    output = set()
    for item in value:
        flag = item.get("check_type") if isinstance(item, dict) else item
        if isinstance(flag, str) and flag in FLAG_TYPES:
            output.add(flag)
    return output


def _state_from_document(document: Any) -> ReportState:
    metadata = document.metadata
    raw_input = metadata.get("input") if isinstance(metadata.get("input"), dict) else metadata
    payload: dict[str, Any] = {
        "document_id": document.document_id,
        "original_text": document.text,
        "extracted_entities": raw_input.get("input_entities", raw_input.get("extracted_entities", [])),
        "medications": raw_input.get("input_medications", raw_input.get("medications", [])),
        "fhir_draft": raw_input.get("fhir_draft"),
    }
    if raw_input.get("ocr_result") is not None:
        payload["ocr_result"] = raw_input["ocr_result"]
    elif raw_input.get("ocr_confidence") is not None:
        payload["ocr_result"] = {
            "success": True,
            "overall_confidence": raw_input["ocr_confidence"],
        }
    return ReportState(
        **{
            key: value for key, value in payload.items()
            if value is not None
        }
    )


def run(config: BenchmarkConfig) -> BenchmarkResult:
    documents, source = documents_for(config, default_fixture=False)
    result = BenchmarkResult("verification")
    latencies: list[float] = []
    tp = fp = fn = tn = exact_docs = annotated_docs = 0
    flag_tp = {flag: 0 for flag in FLAG_TYPES}
    flag_fp = {flag: 0 for flag in FLAG_TYPES}
    flag_fn = {flag: 0 for flag in FLAG_TYPES}
    unsupported_expected = 0

    with benchmark_runtime(config.mode, config.timeout), ResourceMonitor() as monitor:
        from agents.verifier import verifier_agent

        for document in documents:
            started = time.perf_counter()
            try:
                state = _state_from_document(document)
                output = verifier_agent(state)
                found = {flag.check_type for flag in output["verifier_flags"]}
                expected_value = document.ground_truth.get("expected_flags")
                if expected_value is not None:
                    expected = _expected_types(expected_value)
                    annotated_docs += 1
                    tp += len(expected & found)
                    fp += len(found - expected)
                    fn += len(expected - found)
                    tn += len(FLAG_TYPES - (expected | found))
                    exact_docs += int(expected == found)
                    for flag in FLAG_TYPES:
                        flag_tp[flag] += int(flag in expected and flag in found)
                        flag_fp[flag] += int(flag not in expected and flag in found)
                        flag_fn[flag] += int(flag in expected and flag not in found)
                    unsupported_expected += int("UNSUPPORTED_CLAIM" in expected)
                elapsed = time.perf_counter() - started
                latencies.append(elapsed)
                result.details.append({
                    "document_id": document.document_id,
                    "flags_predicted": sorted(found),
                    "latency_seconds": elapsed,
                    "ground_truth_available": expected_value is not None,
                })
            except Exception as exc:
                latencies.append(time.perf_counter() - started)
                result.errors.append({"document_id": document.document_id, "error": str(exc)})

    result.resource_metrics.append({"suite": "verification", **monitor.snapshot().as_dict()})
    result.metrics = {
        "flag_precision": tp / (tp + fp) if tp + fp else (0.0 if annotated_docs else None),
        "flag_recall": tp / (tp + fn) if tp + fn else (0.0 if annotated_docs else None),
        "flag_f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else (0.0 if annotated_docs else None),
        "false_positive_rate": fp / (fp + tn) if fp + tn else None,
        "false_negative_rate": fn / (fn + tp) if fn + tp else None,
        "verification_accuracy": exact_docs / annotated_docs if annotated_docs else None,
        "per_flag": {
            flag: {
                "precision": flag_tp[flag] / (flag_tp[flag] + flag_fp[flag]) if flag_tp[flag] + flag_fp[flag] else None,
                "recall": flag_tp[flag] / (flag_tp[flag] + flag_fn[flag]) if flag_tp[flag] + flag_fn[flag] else None,
            }
            for flag in sorted(FLAG_TYPES)
        },
        "unsupported_claim_detection_precision": (
            flag_tp["UNSUPPORTED_CLAIM"] /
            (flag_tp["UNSUPPORTED_CLAIM"] + flag_fp["UNSUPPORTED_CLAIM"])
            if flag_tp["UNSUPPORTED_CLAIM"] + flag_fp["UNSUPPORTED_CLAIM"] else None
        ),
        "unsupported_claim_detection_recall": (
            flag_tp["UNSUPPORTED_CLAIM"] / unsupported_expected if unsupported_expected else None
        ),
        "citation_source_support_rate": None,
        "documents": len(documents), "annotated_documents": annotated_docs,
        "accuracy_metrics_available": annotated_docs > 0,
        "latency": latency_summary(latencies),
        "dataset_source": source,
    }
    if not annotated_docs:
        result.warnings.append("No expected verifier flags found; verification accuracy metrics are unavailable.")
    result.warnings.append(
        "The current verifier implements selected rule-based checks; general unsupported-claim detection and citation support are not implemented."
    )
    return result
