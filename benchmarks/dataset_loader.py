"""Load benchmark inputs and explicit annotations from common local formats."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class DatasetError(ValueError):
    """Raised when a configured evaluation dataset is malformed."""


@dataclass
class BenchmarkDocument:
    document_id: str
    text: str = ""
    source_path: Path | None = None
    ground_truth: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_ground_truth(self) -> bool:
        return bool(self.ground_truth)


_GROUND_TRUTH_FIELDS = {
    "entities", "medications", "relations", "grounding", "expected_grounding",
    "expected_flags", "unsupported_claims", "transcription", "reference_text",
    "expected_text", "supported_claims",
}
_FILE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def _decode_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def _record_from_mapping(raw: dict[str, Any], index: int, root: Path) -> BenchmarkDocument:
    row = {str(key).strip().lower(): _decode_value(value) for key, value in raw.items()}
    ground_truth = row.get("ground_truth") or row.get("annotations") or {}
    if not isinstance(ground_truth, dict):
        raise DatasetError(f"record {index}: ground_truth/annotations must be an object")
    ground_truth = dict(ground_truth)
    for key in _GROUND_TRUTH_FIELDS:
        if key in row and key not in ground_truth:
            ground_truth[key] = row[key]

    candidate = row.get("file") or row.get("file_path") or row.get("path")
    source_path: Path | None = None
    if candidate:
        source_path = Path(str(candidate))
        if not source_path.is_absolute():
            source_path = root / source_path
        source_path = source_path.resolve()
        if not source_path.is_file():
            raise DatasetError(f"record {index}: input file does not exist: {source_path}")

    text_value = row.get("text") or row.get("document_text") or ""
    if not isinstance(text_value, str):
        raise DatasetError(f"record {index}: text must be a string")
    if not text_value and source_path is None:
        raise DatasetError(f"record {index}: expected text or a file path")
    document_id = str(row.get("document_id") or row.get("id") or f"record-{index:06d}")
    metadata = {key: value for key, value in row.items()
                if key not in {"text", "document_text", "ground_truth", "annotations"} | _GROUND_TRUTH_FIELDS}
    return BenchmarkDocument(document_id, text_value, source_path, ground_truth, metadata)


def _read_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    if suffix == ".jsonl":
        rows = []
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line.strip():
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise DatasetError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
                    if not isinstance(value, dict):
                        raise DatasetError(f"{path}:{line_number}: each JSONL row must be an object")
                    rows.append(value)
        return rows
    if suffix == ".json":
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
        if isinstance(value, dict):
            value = value.get("documents", value.get("records", [value]))
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise DatasetError(f"{path}: JSON must contain a list of record objects")
        return value
    raise DatasetError(f"Unsupported dataset format: {path.suffix or path.name}")


def load_dataset(path: str | Path, *, limit: int | None = None) -> list[BenchmarkDocument]:
    """Load CSV/JSON/JSONL manifests, text files, PDFs, or image files."""
    source = Path(path).expanduser().resolve()
    if not source.exists():
        raise DatasetError(f"dataset path does not exist: {source}")
    if source.is_dir():
        files = sorted(file for file in source.rglob("*")
                       if file.is_file() and (file.suffix.lower() in _FILE_EXTENSIONS or file.suffix.lower() == ".txt"))
        documents = [
            BenchmarkDocument(
                document_id=file.relative_to(source).as_posix(),
                text=file.read_text(encoding="utf-8") if file.suffix.lower() == ".txt" else "",
                source_path=file,
            )
            for file in files
        ]
    elif source.suffix.lower() in {".csv", ".json", ".jsonl"}:
        documents = [_record_from_mapping(row, index, source.parent)
                     for index, row in enumerate(_read_rows(source), start=1)]
    elif source.suffix.lower() == ".txt":
        documents = [BenchmarkDocument(source.stem, source.read_text(encoding="utf-8"), source)]
    elif source.suffix.lower() in _FILE_EXTENSIONS:
        documents = [BenchmarkDocument(source.name, source_path=source)]
    else:
        raise DatasetError(f"Unsupported dataset format: {source.suffix}")
    return documents[:limit] if limit is not None else documents


def has_annotations(documents: list[BenchmarkDocument], field_name: str) -> bool:
    return any(field_name in document.ground_truth for document in documents)
