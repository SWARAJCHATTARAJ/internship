"""Shared dataset selection and small helpers for benchmark suites."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from benchmarks.config import BenchmarkConfig
from benchmarks.dataset_loader import BenchmarkDocument, load_dataset
from schemas.core import ReportState


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_TEXT_DATASET = ROOT / "data" / "synthetic" / "reports.json"


def documents_for(config: BenchmarkConfig, *, default_fixture: bool = True) -> tuple[list[BenchmarkDocument], str]:
    path = config.dataset
    if path is None and default_fixture and SYNTHETIC_TEXT_DATASET.exists():
        path = SYNTHETIC_TEXT_DATASET
    if path is None:
        return [], "not configured"
    return load_dataset(path, limit=config.documents), str(path)


def as_state(document: BenchmarkDocument) -> ReportState:
    return ReportState(document_id=document.document_id, original_text=document.text)


def normalized(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip().casefold()
    return cleaned or None


def parse_ground_truth_list(value: Any, *, field_name: str, document_id: str) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise ValueError(f"{document_id}: ground-truth '{field_name}' must be a list")
