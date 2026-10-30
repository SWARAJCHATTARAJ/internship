"""Dependency-light metrics with explicit handling of empty or missing data."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Any


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def accuracy(y_true: Sequence[Any], y_pred: Sequence[Any]) -> float | None:
    if len(y_true) == 0 or len(y_true) != len(y_pred):
        return None
    return sum(actual == predicted for actual, predicted in zip(y_true, y_pred)) / len(y_true)


def precision_recall_f1(
    y_true: Iterable[Any], y_pred: Iterable[Any], *, positive_label: Any = True
) -> dict[str, float | int | None]:
    actual = list(y_true)
    predicted = list(y_pred)
    if len(actual) != len(predicted):
        raise ValueError("y_true and y_pred must have equal lengths")
    tp = sum(a == positive_label and p == positive_label for a, p in zip(actual, predicted))
    fp = sum(a != positive_label and p == positive_label for a, p in zip(actual, predicted))
    fn = sum(a == positive_label and p != positive_label for a, p in zip(actual, predicted))
    p_value = _ratio(tp, tp + fp)
    r_value = _ratio(tp, tp + fn)
    f_value = (
        2 * p_value * r_value / (p_value + r_value)
        if p_value is not None and r_value is not None and p_value + r_value
        else (0.0 if p_value == 0 or r_value == 0 else None)
    )
    return {"precision": p_value, "recall": r_value, "f1": f_value, "tp": tp, "fp": fp, "fn": fn}


def classification_metrics(
    y_true: Sequence[Any], y_pred: Sequence[Any], labels: Iterable[Any] | None = None
) -> dict[str, Any]:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have equal lengths")
    if not y_true:
        return {
            "accuracy": None, "micro_precision": None, "micro_recall": None,
            "micro_f1": None, "macro_precision": None, "macro_recall": None,
            "macro_f1": None, "per_label": {},
        }

    label_set = list(labels) if labels is not None else sorted(set(y_true) | set(y_pred), key=str)
    per_label = {
        str(label): precision_recall_f1(y_true, y_pred, positive_label=label)
        for label in label_set
    }
    tp = sum(values["tp"] for values in per_label.values())
    fp = sum(values["fp"] for values in per_label.values())
    fn = sum(values["fn"] for values in per_label.values())
    micro_p = _ratio(tp, tp + fp)
    micro_r = _ratio(tp, tp + fn)
    micro_f = (
        2 * micro_p * micro_r / (micro_p + micro_r)
        if micro_p is not None and micro_r is not None and micro_p + micro_r
        else (0.0 if micro_p == 0 or micro_r == 0 else None)
    )

    def macro(key: str) -> float | None:
        values = [metrics[key] for metrics in per_label.values() if metrics[key] is not None]
        return sum(values) / len(values) if values else None

    return {
        "accuracy": accuracy(y_true, y_pred),
        "micro_precision": micro_p,
        "micro_recall": micro_r,
        "micro_f1": micro_f,
        "macro_precision": macro("precision"),
        "macro_recall": macro("recall"),
        "macro_f1": macro("f1"),
        "per_label": per_label,
    }


def _edit_distance(left: Sequence[Any], right: Sequence[Any]) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for row_index, left_item in enumerate(left, start=1):
        current = [row_index]
        for column_index, right_item in enumerate(right, start=1):
            current.append(min(
                current[-1] + 1,
                previous[column_index] + 1,
                previous[column_index - 1] + (left_item != right_item),
            ))
        previous = current
    return previous[-1]


def character_error_rate(reference: str, hypothesis: str) -> float | None:
    if not reference:
        return 0.0 if not hypothesis else None
    return _edit_distance(list(reference), list(hypothesis)) / len(reference)


def word_error_rate(reference: str, hypothesis: str) -> float | None:
    reference_words = reference.lower().split()
    hypothesis_words = hypothesis.lower().split()
    if not reference_words:
        return 0.0 if not hypothesis_words else None
    return _edit_distance(reference_words, hypothesis_words) / len(reference_words)


def entity_key(entity: Any, source_text: str | None = None) -> tuple[Any, ...] | None:
    """Normalize dicts, schema objects, text spans, and labeled text entities."""
    if isinstance(entity, str):
        get = lambda key, default=None: entity if key in {"text", "entity"} else default
    elif isinstance(entity, dict):
        get = entity.get
    else:
        get = lambda key, default=None: getattr(entity, key, default)
    label = get("label", get("type"))
    start = get("start_char", get("start"))
    end = get("end_char", get("end"))
    span = get("span")
    if (start is None or end is None) and isinstance(span, (list, tuple)) and len(span) == 2:
        start, end = span
    if isinstance(start, int) and isinstance(end, int) and end >= start:
        return ("span", start, end, str(label).upper() if label is not None else None)
    text = get("text", get("entity"))
    if text is None:
        return None
    text = str(text).strip().lower()
    if not text:
        return None
    if source_text is not None:
        start = source_text.lower().find(text)
        if start >= 0:
            return ("span", start, start + len(text), str(label).upper() if label is not None else None)
    return ("text", text, str(label).upper() if label is not None else None)


def entity_metrics(
    expected: Iterable[Any], predicted: Iterable[Any], source_text: str | None = None
) -> dict[str, Any]:
    gold = {key for item in expected if (key := entity_key(item, source_text)) is not None}
    found = {key for item in predicted if (key := entity_key(item, source_text)) is not None}
    common = len(gold & found)
    p_value = _ratio(common, len(found))
    r_value = _ratio(common, len(gold))
    f_value = (
        2 * p_value * r_value / (p_value + r_value)
        if p_value is not None and r_value is not None and p_value + r_value
        else (0.0 if p_value == 0 or r_value == 0 else None)
    )
    return {
        "precision": p_value, "recall": r_value, "f1": f_value,
        "tp": common, "fp": len(found - gold), "fn": len(gold - found),
    }


def recall_at_k(ranked_ids: Sequence[Sequence[Any]], relevant_ids: Sequence[Any], k: int) -> float | None:
    if k < 1:
        raise ValueError("k must be at least 1")
    if len(ranked_ids) != len(relevant_ids) or len(ranked_ids) == 0:
        return None
    hits = [bool(set(ranking[:k]) & set(relevant if isinstance(relevant, (set, list, tuple)) else [relevant]))
            for ranking, relevant in zip(ranked_ids, relevant_ids)]
    return sum(hits) / len(hits)


def mean_reciprocal_rank(ranked_ids: Sequence[Sequence[Any]], relevant_ids: Sequence[Any]) -> float | None:
    if len(ranked_ids) != len(relevant_ids) or len(ranked_ids) == 0:
        return None
    scores = []
    for ranking, relevant in zip(ranked_ids, relevant_ids):
        relevant_set = set(relevant if isinstance(relevant, (set, list, tuple)) else [relevant])
        rank = next((index for index, item in enumerate(ranking, start=1) if item in relevant_set), None)
        scores.append(1 / rank if rank else 0.0)
    return sum(scores) / len(scores)


def percentile(values: Sequence[float], percentile_value: float) -> float | None:
    if not values:
        return None
    if not 0 <= percentile_value <= 100:
        raise ValueError("percentile_value must be between 0 and 100")
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * percentile_value / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def latency_summary(seconds: Sequence[float]) -> dict[str, float | None]:
    p50 = percentile(seconds, 50)
    return {
        "average_seconds": sum(seconds) / len(seconds) if seconds else None,
        "median_seconds": p50,
        "p50_seconds": p50,
        "p90_seconds": percentile(seconds, 90),
        "p95_seconds": percentile(seconds, 95),
        "p99_seconds": percentile(seconds, 99),
    }


def throughput(count: int, elapsed_seconds: float) -> float | None:
    return count / elapsed_seconds if elapsed_seconds > 0 else None


def success_rate(successes: int, total: int) -> float | None:
    return _ratio(successes, total)


def error_rate(errors: int, total: int) -> float | None:
    return _ratio(errors, total)
