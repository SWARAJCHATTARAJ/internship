"""End-to-end graph timing with isolated SQLite persistence and stage timings."""

from __future__ import annotations

import tempfile
import time
import mimetypes
from pathlib import Path
from typing import Any, Callable

from benchmarks.common import documents_for
from benchmarks.config import BenchmarkConfig, BenchmarkResult
from benchmarks.metrics import latency_summary, success_rate, throughput
from benchmarks.resource_monitor import ResourceMonitor
from benchmarks.runtime import benchmark_runtime


def _source_state(document: Any, timings: list[dict[str, Any]], db_path: str) -> Any:
    from agents.document import DocumentAgent
    from schemas.core import AuditEvent, ReportState

    is_text_file = document.source_path is not None and document.source_path.suffix.lower() == ".txt"
    if document.source_path is None or is_text_file:
        ingestion_started = time.perf_counter()
        analysis = DocumentAgent().analyze_text(document.text)
        text = document.text
        source_text = text
        source_type = None
        ocr_result = None
        source_file = None
        ingestion_seconds = time.perf_counter() - ingestion_started
    else:
        ingestion_started = time.perf_counter()
        payload = document.source_path.read_bytes()
        read_seconds = time.perf_counter() - ingestion_started
        upload_started = time.perf_counter()
        from data.db import save_upload

        save_upload(
            document.document_id,
            document.source_path.name,
            payload,
            mimetypes.guess_type(document.source_path.name)[0],
            db_path=db_path,
        )
        timings.append({
            "document_id": document.document_id, "stage": "upload_persistence",
            "elapsed_seconds": time.perf_counter() - upload_started,
        })
        analysis_started = time.perf_counter()
        analysis, native_text = DocumentAgent().analyze_file(payload, document.source_path.name)
        ingestion_seconds = read_seconds + time.perf_counter() - analysis_started
        source_text = native_text
        source_file = document.source_path.name
        ocr_result = None
        source_type = "pdf" if analysis.format == "pdf" else "image"
    timings.append({
        "document_id": document.document_id, "stage": "document_ingestion",
        "elapsed_seconds": ingestion_seconds,
    })

    if document.source_path is not None and not is_text_file:
        if analysis.requires_ocr:
            from agents.ocr import OCRAgent

            ocr_started = time.perf_counter()
            ocr_result = OCRAgent().process(payload, document.source_path.name)
            timings.append({
                "document_id": document.document_id, "stage": "ocr",
                "elapsed_seconds": time.perf_counter() - ocr_started,
            })
            if not ocr_result.success:
                raise RuntimeError("OCR did not return usable text")
            source_text = ocr_result.text
        elif not source_text:
            raise RuntimeError("Document has no readable text")
        else:
            timings.append({
                "document_id": document.document_id, "stage": "ocr",
                "elapsed_seconds": 0.0, "status": "native_text_no_ocr_required",
            })

    if document.source_path is None or is_text_file:
        text = document.text
        timings.append({
            "document_id": document.document_id, "stage": "ocr",
            "elapsed_seconds": 0.0, "status": "not_applicable_for_text_input",
        })
        timings.append({
            "document_id": document.document_id, "stage": "preprocessing",
            "elapsed_seconds": 0.0, "status": "not_applicable_for_text_endpoint",
        })
    else:
        preprocess_started = time.perf_counter()
        from tools.preprocessing import mask_phi, normalize_clinical_text

        masked, _ = mask_phi(source_text)
        text = normalize_clinical_text(masked)
        timings.append({
            "document_id": document.document_id, "stage": "preprocessing",
            "elapsed_seconds": time.perf_counter() - preprocess_started,
        })
    audit = []
    if ocr_result is not None:
        audit.append(AuditEvent(
            agent_name="ocr_agent",
            action_type="OCR_EXTRACTION",
            details={
                "source_type": source_type,
                "pages_processed": ocr_result.pages_processed,
                "pages_failed": ocr_result.pages_failed,
                "overall_confidence": ocr_result.overall_confidence,
                "warnings": ocr_result.warnings,
            },
        ))
    audit.append(AuditEvent(agent_name="document_agent", action_type="DOCUMENT_ANALYSIS", details=analysis.model_dump()))
    return ReportState(
        document_id=document.document_id,
        original_text=text,
        source_text=source_text or text,
        source_type=source_type,
        source_file=source_file,
        ocr_result=ocr_result,
        document_analysis=analysis,
        audit_trail=audit,
    )


def _timed(function: Callable[..., Any], stage: str, document_id: str, timings: list[dict[str, Any]]) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            timings.append({
                "document_id": document_id, "stage": stage,
                "elapsed_seconds": time.perf_counter() - started,
            })
    return wrapper


def _run_graph(state: Any, timings: list[dict[str, Any]]) -> dict[str, Any]:
    import agents.orchestrator as orchestrator

    graph = orchestrator.graph
    previous_node_map = graph.node_map
    previous_orchestrator = orchestrator.orchestrator_node
    previous_finalizer = orchestrator.finalizer_agent
    stage_by_agent = {
        "ner_agent": "ner", "medication_agent": "medication", "drug_agent": "medication",
        "clinical_context_agent": "clinical_processing", "relation_agent": "relation",
        "timeline_agent": "clinical_processing", "grounding_agent": "grounding",
        "summary_agent": "clinical_synthesis", "verifier_agent": "verification",
    }
    graph.node_map = {
        name: _timed(function, stage_by_agent.get(name, name), state.document_id, timings)
        for name, function in previous_node_map.items()
    }
    orchestrator.orchestrator_node = _timed(previous_orchestrator, "orchestration", state.document_id, timings)
    orchestrator.finalizer_agent = _timed(previous_finalizer, "final_response_generation", state.document_id, timings)
    try:
        return graph.invoke(state)
    finally:
        graph.node_map = previous_node_map
        orchestrator.orchestrator_node = previous_orchestrator
        orchestrator.finalizer_agent = previous_finalizer


def run(config: BenchmarkConfig) -> BenchmarkResult:
    from schemas.core import ReportState
    from data.db import init_db, save_report

    documents, source = documents_for(config)
    result = BenchmarkResult("pipeline")
    if config.workers > 1:
        result.warnings.append("Pipeline stage instrumentation is sequential; use --load for concurrent workloads.")
    durations: list[float] = []
    successes = entities = relations = 0
    with tempfile.TemporaryDirectory(prefix="clinical-benchmark-db-") as directory:
        db_path = str(Path(directory) / "reports.sqlite3")
        init_started = time.perf_counter()
        init_db(db_path=db_path)
        result.stage_timings.append({
            "document_id": None, "stage": "database_initialization",
            "elapsed_seconds": time.perf_counter() - init_started,
        })
        with benchmark_runtime(config.mode, config.timeout), ResourceMonitor() as monitor:
            for document in documents:
                started = time.perf_counter()
                try:
                    state = _source_state(document, result.stage_timings, db_path)
                    output = _run_graph(state, result.stage_timings)
                    final_state = ReportState(**output)
                    persistence_started = time.perf_counter()
                    save_report(final_state, db_path=db_path)
                    result.stage_timings.append({
                        "document_id": document.document_id, "stage": "database_persistence",
                        "elapsed_seconds": time.perf_counter() - persistence_started,
                    })
                    successes += 1
                    entities += len(final_state.extracted_entities)
                    relations += len(final_state.relations)
                    result.details.append({
                        "document_id": document.document_id, "success": True,
                        "entities": len(final_state.extracted_entities),
                        "relations": len(final_state.relations),
                        "verification_status": (final_state.final_result or {}).get("verification", {}).get("status"),
                    })
                except Exception as exc:
                    result.errors.append({"document_id": document.document_id, "error": str(exc)})
                    result.details.append({"document_id": document.document_id, "success": False, "error": str(exc)})
                finally:
                    elapsed = time.perf_counter() - started
                    durations.append(elapsed)
                    result.stage_timings.append({
                        "document_id": document.document_id, "stage": "total",
                        "elapsed_seconds": elapsed,
                    })
        result.resource_metrics.append({"suite": "pipeline", **monitor.snapshot().as_dict()})

    result.metrics = {
        "documents": len(documents),
        "successful_documents": successes,
        "failed_documents": len(documents) - successes,
        "success_rate": success_rate(successes, len(documents)),
        "failure_rate": success_rate(len(documents) - successes, len(documents)),
        **latency_summary(durations),
        "total_execution_seconds": sum(durations),
        "documents_per_second": throughput(successes, sum(durations)),
        "average_entities_per_document": entities / successes if successes else None,
        "average_relationships_per_document": relations / successes if successes else None,
        "dataset_source": source,
        "database": "temporary SQLite database; removed after suite",
    }
    if not documents:
        result.warnings.append("No pipeline input documents found.")
    if config.mode == "mock":
        result.warnings.append("Mock mode disables pretrained/external inference and exercises local deterministic fallbacks.")
    result.warnings.append(
        "Stage timings are exclusive wall-clock calls; total latency is measured separately and is not the sum of nested stages."
    )
    result.warnings.append("Text inputs follow the existing /process route; file inputs follow document/OCR/preprocessing behavior from /process/upload.")
    return result
