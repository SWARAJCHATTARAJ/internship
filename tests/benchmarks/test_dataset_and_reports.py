import csv
import json
from datetime import datetime, timezone

from benchmarks.config import BenchmarkConfig, BenchmarkResult
from benchmarks.dataset_loader import load_dataset
from benchmarks.report_generator import generate_reports


def test_dataset_loader_reads_json_csv_jsonl_and_image_paths(tmp_path):
    source_image = tmp_path / "scan.png"
    source_image.write_bytes(b"\x89PNG\r\n\x1a\n")
    manifest = tmp_path / "cases.json"
    manifest.write_text(json.dumps([{
        "id": "case-1", "text": "Patient report",
        "ground_truth": {"entities": [{"text": "report", "label": "SYMPTOM"}]},
    }, {
        "id": "scan-1", "file": "scan.png", "ground_truth": {"transcription": "scan"},
    }]), encoding="utf-8")
    docs = load_dataset(manifest)
    assert docs[0].text == "Patient report"
    assert docs[0].has_ground_truth
    assert docs[1].source_path == source_image.resolve()
    assert docs[1].text == ""

    csv_path = tmp_path / "cases.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "text", "entities"])
        writer.writeheader()
        writer.writerow({"id": "csv-1", "text": "fever", "entities": '[{"text":"fever","label":"SYMPTOM"}]'})
    assert load_dataset(csv_path)[0].ground_truth["entities"][0]["text"] == "fever"

    jsonl_path = tmp_path / "cases.jsonl"
    jsonl_path.write_text('{"id":"line-1","text":"cough"}\n', encoding="utf-8")
    assert load_dataset(jsonl_path)[0].document_id == "line-1"
    assert not load_dataset(jsonl_path)[0].has_ground_truth


def test_report_generation_has_required_outputs_and_n_a_metrics(tmp_path):
    result = BenchmarkResult(
        suite="ner",
        metrics={"f1": None, "accuracy_metrics_available": False},
        warnings=["No reference annotations."],
    )
    config = BenchmarkConfig(output_dir=tmp_path)
    output = generate_reports(
        [result], config, dataset_source="not configured",
        executed_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
    )
    assert output.name == "20260102_030405"
    for filename in (
        "summary.json", "summary.csv", "detailed_metrics.csv", "resource_metrics.csv",
        "stage_timings.csv", "benchmark_report.md", "benchmark_report.xlsx",
    ):
        assert (output / filename).is_file()
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["suite_summaries"]["ner"]["f1"] is None
    assert "N/A" in (output / "summary.csv").read_text(encoding="utf-8")
    assert "not configured" in (output / "benchmark_report.md").read_text(encoding="utf-8")
    second = generate_reports(
        [result], config, executed_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
    )
    assert second.name == "20260102_030405_01"
