"""Document characterization agent. It decides whether OCR is needed, not clinical meaning."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from schemas.core import DocumentAnalysis


class DocumentAgent:
    def analyze_text(self, text: str) -> DocumentAnalysis:
        return DocumentAnalysis(
            document_type=self._document_type(text), format="text", pages=1,
            requires_ocr=False, machine_readable_pages=[1], source_text_kind="user_text",
        )

    def analyze_file(self, data: bytes, filename: str | None = None) -> tuple[DocumentAnalysis, str]:
        source_type = self._file_type(data, filename)
        if source_type == "image":
            return DocumentAnalysis(
                document_type="unknown", format="image", pages=1, requires_ocr=True,
                scanned_pages=[1], source_text_kind="ocr",
            ), ""
        if source_type != "pdf":
            return DocumentAnalysis(format="unknown", pages=0, requires_ocr=False), ""

        try:
            import fitz
            pdf = fitz.open(stream=data, filetype="pdf")
            page_text = [page.get_text("text").strip() for page in pdf]
            pdf.close()
        except Exception:
            return DocumentAnalysis(format="pdf", pages=0, requires_ocr=True, source_text_kind="ocr"), ""

        readable = [i + 1 for i, value in enumerate(page_text) if len(value) >= 20]
        scanned = [i + 1 for i, value in enumerate(page_text) if len(value) < 20]
        text = "\n\n".join(f"Page {i + 1}:\n{value}" for i, value in enumerate(page_text) if value)
        source_kind = "native_text" if not scanned else ("mixed" if readable else "ocr")
        return DocumentAnalysis(
            document_type=self._document_type(text), format="pdf", pages=len(page_text),
            requires_ocr=bool(scanned), machine_readable_pages=readable, scanned_pages=scanned,
            has_tables=any("\t" in value or "table" in value.lower() for value in page_text),
            source_text_kind=source_kind,
        ), text

    @staticmethod
    def _file_type(data: bytes, filename: str | None) -> str:
        if data.startswith(b"%PDF-"):
            return "pdf"
        if data.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")):
            return "image"
        suffix = Path(filename or "").suffix.lower()
        return "pdf" if suffix == ".pdf" else "unknown"

    @staticmethod
    def _document_type(text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ("prescription", "rx", "medicine", "dose", "dosage")):
            return "prescription"
        return "clinical_report" if text.strip() else "unknown"
