"""Performance and annotated accuracy evaluation for the repository OCR path."""

from __future__ import annotations

import time
from statistics import median
from typing import Any

from benchmarks.common import documents_for
from benchmarks.config import BenchmarkConfig, BenchmarkResult
from benchmarks.metrics import character_error_rate, percentile, throughput, word_error_rate
from benchmarks.resource_monitor import ResourceMonitor
from benchmarks.runtime import benchmark_runtime


def _reference(document: Any) -> str | None:
    for key in ("transcription", "reference_text", "expected_text"):
        value = document.ground_truth.get(key)
        if isinstance(value, str):
            return value
    return None


def run(config: BenchmarkConfig) -> BenchmarkResult:
    from agents.document import DocumentAgent
    from agents.ocr import OCRAgent

    documents, source = documents_for(config, default_fixture=False)
    result = BenchmarkResult("ocr")
    if not documents:
        result.warnings.append("No OCR documents configured; accuracy and performance metrics are unavailable.")
        result.metrics = {
            "accuracy_metrics_available": False, "documents": 0, "cer": None, "wer": None,
            "text_extraction_accuracy": None, "average_seconds_per_document": None,
            "pages_per_second": None, "failure_rate": None, "confidence_distribution": None,
            "dataset_source": source,
        }
        return result

    latencies: list[float] = []
    cer_values: list[float] = []
    wer_values: list[float] = []
    exact_values: list[float] = []
    confidence_values: list[float] = []
    pages = failures = annotated = 0
    with benchmark_runtime(config.mode, config.timeout), ResourceMonitor() as monitor:
        for document in documents:
            started = time.perf_counter()
            document_confidence = None
            try:
                if document.source_path is None:
                    raise ValueError("OCR requires a PDF or image file path")
                payload = document.source_path.read_bytes()
                analysis, native_text = DocumentAgent().analyze_file(payload, document.source_path.name)
                if analysis.requires_ocr:
                    ocr_result = OCRAgent().process(payload, document.source_path.name)
                    prediction = ocr_result.text
                    page_count = ocr_result.pages_processed + ocr_result.pages_failed
                    document_confidence = ocr_result.overall_confidence
                    confidence_values.extend(
                        page.confidence for page in ocr_result.pages if page.confidence is not None
                    )
                    if not ocr_result.success:
                        failures += 1
                else:
                    prediction = native_text
                    page_count = analysis.pages
                pages += page_count
                reference = _reference(document)
                if reference is not None:
                    annotated += 1
                    cer = character_error_rate(reference, prediction)
                    wer = word_error_rate(reference, prediction)
                    if cer is not None:
                        cer_values.append(cer)
                    if wer is not None:
                        wer_values.append(wer)
                    exact_values.append(float(" ".join(reference.casefold().split()) ==
                                           " ".join(prediction.casefold().split())))
                result.details.append({
                    "document_id": document.document_id,
                    "pages": page_count,
                    "latency_seconds": time.perf_counter() - started,
                    "success": bool(prediction),
                    "ground_truth_available": reference is not None,
                    "confidence": document_confidence,
                    "document_quality": document.metadata.get("quality"),
                })
            except Exception as exc:
                failures += 1
                result.errors.append({"document_id": document.document_id, "error": str(exc)})
                result.details.append({"document_id": document.document_id, "success": False, "error": str(exc)})
            finally:
                latencies.append(time.perf_counter() - started)
    resource = monitor.snapshot()
    result.resource_metrics.append({"suite": "ocr", **resource.as_dict()})

    confidence = {
        "count": len(confidence_values),
        "mean": sum(confidence_values) / len(confidence_values) if confidence_values else None,
        "median": median(confidence_values) if confidence_values else None,
        "p95": percentile(confidence_values, 95),
        "note": "Engine confidence is reported separately and is not an accuracy measure.",
    }
    result.metrics = {
        "documents": len(documents),
        "annotated_documents": annotated,
        "accuracy_metrics_available": annotated > 0,
        "cer": sum(cer_values) / len(cer_values) if cer_values else None,
        "wer": sum(wer_values) / len(wer_values) if wer_values else None,
        "text_extraction_accuracy": sum(exact_values) / len(exact_values) if exact_values else None,
        "average_seconds_per_document": sum(latencies) / len(latencies) if latencies else None,
        "pages_processed": pages,
        "pages_per_second": throughput(pages, sum(latencies)),
        "ocr_failures": failures,
        "failure_rate": failures / len(documents) if documents else None,
        "confidence_distribution": confidence,
        "dataset_source": source,
    }
    if annotated == 0:
        result.warnings.append("No ground-truth transcription found; OCR accuracy metrics are unavailable.")
    if not confidence_values:
        result.warnings.append("No OCR engine confidence scores were returned.")
    return result
