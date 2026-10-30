import json

from benchmarks.benchmark_api import run as run_api
from benchmarks.benchmark_database import run as run_database
from benchmarks.benchmark_ner import run as run_ner
from benchmarks.benchmark_pipeline import run as run_pipeline
from benchmarks.config import BenchmarkConfig
from benchmarks.resource_monitor import ResourceMonitor


def _dataset(tmp_path):
    path = tmp_path / "records.json"
    path.write_text(json.dumps([{
        "id": "sample-1",
        "text": "Patient diagnosed with diabetes and prescribed metformin 500 mg.",
        "ground_truth": {
            "entities": [
                {"text": "diabetes", "label": "DIAGNOSIS"},
                {"text": "metformin", "label": "MEDICATION"},
            ]
        },
    }]), encoding="utf-8")
    return path


def test_resource_monitor_returns_elapsed_time():
    with ResourceMonitor(interval_seconds=0.01) as monitor:
        pass
    snapshot = monitor.snapshot()
    assert snapshot.elapsed_seconds >= 0
    assert snapshot.as_dict()["gpu_memory_used_mb"] is None or snapshot.as_dict()["gpu_memory_used_mb"] >= 0


def test_mock_ner_pipeline_database_and_api_use_isolated_or_stubbed_persistence(tmp_path):
    dataset = _dataset(tmp_path)
    config = BenchmarkConfig(mode="mock", dataset=dataset, documents=1, output_dir=tmp_path / "results")

    ner = run_ner(config)
    assert ner.metrics["accuracy_metrics_available"] is True
    assert ner.metrics["documents"] == 1

    pipeline = run_pipeline(config)
    assert pipeline.metrics["documents"] == 1
    assert pipeline.metrics["successful_documents"] == 1
    stages = {row["stage"] for row in pipeline.stage_timings}
    assert {"ner", "verification", "final_response_generation", "database_persistence", "total"} <= stages

    database = run_database(config)
    assert database.metrics["backend"] == "SQLite"
    assert database.metrics["records"] == 1
    assert "temporary" in database.metrics["database_scope"]

    api = run_api(config)
    assert api.metrics["requests"] == 1
    assert api.metrics["http_5xx_errors"] == 0
    assert api.metrics["execution_scope"].endswith("persistence methods disabled")


def test_ner_aggregates_identical_spans_across_documents(tmp_path):
    document = {
        "text": "Patient diagnosed with diabetes and prescribed metformin 500 mg.",
        "ground_truth": {
            "entities": [
                {"text": "diabetes", "label": "DIAGNOSIS"},
                {"text": "metformin", "label": "MEDICATION"},
            ]
        },
    }
    dataset = tmp_path / "duplicate-records.json"
    dataset.write_text(json.dumps([
        {"id": "sample-1", **document},
        {"id": "sample-2", **document},
    ]), encoding="utf-8")
    config = BenchmarkConfig(mode="mock", dataset=dataset, documents=2)

    result = run_ner(config)

    assert result.errors == []
    assert result.metrics["tp"] == 4
    assert result.metrics["annotated_documents"] == 2


def test_digital_pdf_is_benchmarked_through_native_text_paths(tmp_path, monkeypatch):

    from benchmarks.benchmark_api import run as run_api
    from benchmarks.benchmark_ocr import run as run_ocr
    from benchmarks.benchmark_pipeline import run as run_pipeline
    from schemas.core import DocumentAnalysis
    from agents.document import DocumentAgent

    pdf_path = tmp_path / "clinical.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\nbenchmark fixture")
    monkeypatch.setattr(
        DocumentAgent,
        "analyze_file",
        lambda self, data, filename: (
            DocumentAnalysis(
                document_type="clinical_report",
                format="pdf",
                pages=1,
                requires_ocr=False,
                machine_readable_pages=[1],
            ),
            "Patient reports fever.",
        ),
    )
    manifest = tmp_path / "pdf.json"
    manifest.write_text(json.dumps([{
        "id": "digital-pdf",
        "file": "clinical.pdf",
        "ground_truth": {"transcription": "Patient reports fever."},
    }]), encoding="utf-8")
    config = BenchmarkConfig(mode="mock", dataset=manifest, documents=1)

    ocr = run_ocr(config)
    assert ocr.metrics["pages_processed"] == 1
    assert ocr.metrics["accuracy_metrics_available"] is True
    assert ocr.metrics["ocr_failures"] == 0

    pipeline = run_pipeline(config)
    assert pipeline.metrics["successful_documents"] == 1
    assert any(row["stage"] == "document_ingestion" for row in pipeline.stage_timings)

    api = run_api(config)
    assert api.metrics["requests"] == 1
    assert api.metrics["success_count"] == 1
