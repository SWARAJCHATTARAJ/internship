import pytest

from benchmarks.metrics import (
    accuracy,
    character_error_rate,
    classification_metrics,
    entity_metrics,
    error_rate,
    latency_summary,
    mean_reciprocal_rank,
    percentile,
    precision_recall_f1,
    recall_at_k,
    success_rate,
    throughput,
    word_error_rate,
)


def test_classification_metrics_precision_recall_and_f1():
    scores = precision_recall_f1([1, 1, 0, 0], [1, 0, 1, 0], positive_label=1)
    assert scores == {"precision": 0.5, "recall": 0.5, "f1": 0.5, "tp": 1, "fp": 1, "fn": 1}
    summary = classification_metrics(["a", "b"], ["a", "a"], labels=["a", "b"])
    assert summary["accuracy"] == 0.5
    assert summary["micro_f1"] == 0.5
    assert summary["per_label"]["b"]["recall"] == 0.0


def test_metrics_handle_empty_or_invalid_inputs():
    assert accuracy([], []) is None
    assert precision_recall_f1([], [])["f1"] is None
    assert entity_metrics([], [])["f1"] is None
    assert success_rate(0, 0) is None
    assert error_rate(0, 0) is None
    assert throughput(3, 0) is None
    with pytest.raises(ValueError):
        classification_metrics(["a"], [])


def test_entity_exact_span_and_text_formats_and_duplicate_predictions():
    scores = entity_metrics(
        [{"text": "fever", "label": "SYMPTOM"}],
        [
            {"start": 12, "end": 17, "label": "SYMPTOM"},
            {"start_char": 12, "end_char": 17, "label": "SYMPTOM"},
        ],
        source_text="Patient has fever",
    )
    assert scores["precision"] == 1
    assert scores["recall"] == 1
    assert entity_metrics([{"text": "Fever", "label": "SYMPTOM"}],
                         [{"text": "fever", "label": "SYMPTOM"}])["f1"] == 1


def test_text_retrieval_latency_and_rates():
    assert character_error_rate("kitten", "sitting") == pytest.approx(3 / 6)
    assert word_error_rate("one two", "one three") == 0.5
    assert recall_at_k([["a", "b"]], ["b"], 2) == 1
    assert mean_reciprocal_rank([["a", "b"]], ["b"]) == 0.5
    assert percentile([4, 1, 3, 2], 50) == 2.5
    assert latency_summary([0.1, 0.2])["p95_seconds"] == pytest.approx(0.195)
    with pytest.raises(ValueError):
        percentile([1], 101)
