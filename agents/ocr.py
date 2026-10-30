"""Document-to-text gateway for scanned clinical documents."""
from __future__ import annotations

from io import BytesIO
from typing import Optional

from schemas.core import OCRPage, OCRRegion, OCRResult


class OCRAgent:
    """Runs type validation, PDF page conversion, OCR, and result validation."""

    def __init__(self, minimum_confidence: float = 0.0, max_bytes: int = 25 * 1024 * 1024):
        self.minimum_confidence = minimum_confidence
        self.max_bytes = max_bytes

    @staticmethod
    def detect_file_type(data: bytes) -> Optional[str]:
        if data.startswith(b"%PDF-"):
            return "pdf"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if data.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        return None

    def process(self, data: bytes, filename: Optional[str] = None) -> OCRResult:
        if not data:
            return self._error("Input file is empty")
        if len(data) > self.max_bytes:
            return self._error(f"Input file exceeds the {self.max_bytes // (1024 * 1024)} MB limit")
        source_type = self.detect_file_type(data)
        if source_type is None:
            return self._error("Unsupported file type. Supported types are PDF, PNG, JPG, and JPEG.")
        try:
            images = self._to_images(data, source_type)
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            return self._error(f"Unable to read {source_type} document: {exc}", source_type)

        pages = []
        for number, image in enumerate(images, start=1):
            try:
                pages.append(self._recognize_page(image, number))
            except (ImportError, OSError, RuntimeError, ValueError) as exc:
                pages.append(OCRPage(page_number=number, error=f"OCR failed: {exc}"))

        successful = [page for page in pages if page.error is None]
        failed = [page for page in pages if page.error is not None]
        text = "\n\n".join(f"Page {page.page_number}:\n{page.text}" for page in successful if page.text).strip()
        warnings = []
        if failed:
            warnings.append(f"{len(failed)} page(s) could not be processed")
        if not text:
            warnings.append("OCR returned no readable text")
        confidences = [p.confidence for p in successful if p.confidence is not None]
        overall = sum(confidences) / len(confidences) if confidences else None
        if overall is not None and overall < self.minimum_confidence:
            warnings.append("OCR confidence is below the configured threshold")
        return OCRResult(
            success=bool(successful) and bool(text), text=text, pages=pages,
            overall_confidence=overall, source_type=source_type,
            pages_processed=len(successful), pages_failed=len(failed), warnings=warnings,
            errors=[page.error for page in failed if page.error],
        )

    def _to_images(self, data: bytes, source_type: str):
        if source_type != "pdf":
            from PIL import Image
            image = Image.open(BytesIO(data))
            image.verify()
            return [Image.open(BytesIO(data)).copy()]
        import fitz
        from PIL import Image
        document = fitz.open(stream=data, filetype="pdf")
        try:
            if document.page_count == 0:
                raise ValueError("PDF contains no pages")
            images = []
            for page in document:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                images.append(Image.open(BytesIO(pixmap.tobytes("png"))).copy())
            return images
        finally:
            document.close()

    def _recognize_page(self, image, page_number: int) -> OCRPage:
        import sys
        from PIL import Image, ImageEnhance, ImageOps

        # Ensure image has clean RGB format without alpha channel issues
        if image.mode != "RGB":
            bg = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                bg.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[-1])
            else:
                bg.paste(image.convert("RGB"))
            image = bg

        # 1. Native Windows OCR Engine (zero disk footprint, native line-breaks & bboxes)
        regions, line_texts = [], []
        winocr_text = ""
        if sys.platform == "win32":
            try:
                import winocr
                import concurrent.futures
                prepared = ImageOps.grayscale(image)
                prepared = ImageEnhance.Contrast(prepared).enhance(1.3)
                # Safely execute in worker thread to prevent collision with FastAPI's running event loop
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    ocr_res = pool.submit(winocr.recognize_pil_sync, prepared).result()
                lines = ocr_res.get("lines", [])
                for line in lines:
                    line_words = []
                    for word in line.get("words", []):
                        w_text = word.get("text", "").strip()
                        if not w_text:
                            continue
                        rect = word.get("bounding_rect", {})
                        x = int(rect.get("x", 0))
                        y = int(rect.get("y", 0))
                        w = int(rect.get("width", 0))
                        h = int(rect.get("height", 0))
                        bbox = [x, y, x + w, y + h]
                        regions.append(OCRRegion(text=w_text, confidence=0.92, bbox=bbox))
                        line_words.append(w_text)
                    if line_words:
                        line_texts.append(" ".join(line_words))
                winocr_text = "\n".join(line_texts).strip()
            except Exception as exc:
                print(f"[OCRAgent] winocr error on page {page_number}: {exc}")

        # 2. Multimodal Vision OCR (Gemini Vision) for clinical documents & prescriptions
        try:
            from tools.llm_client import transcribe_clinical_image, get_api_key
            if get_api_key():
                from io import BytesIO
                buf = BytesIO()
                image.save(buf, format="PNG")
                multimodal_text = transcribe_clinical_image(buf.getvalue(), mime_type="image/png")
                if multimodal_text and len(multimodal_text.strip()) > 15:
                    return OCRPage(
                        page_number=page_number,
                        text=multimodal_text.strip(),
                        confidence=0.98,
                        regions=regions,
                    )
        except Exception as exc:
            print(f"[OCRAgent] Multimodal transcription fallback on page {page_number}: {exc}")

        if winocr_text:
            return OCRPage(
                page_number=page_number,
                text=winocr_text,
                confidence=0.92 if regions else None,
                regions=regions,
            )

        # 3. Tesseract OCR Engine (Cross-platform / fallback)
        import pytesseract  # pyright: ignore[reportMissingImports]
        import os
        from PIL import ImageFilter

        if sys.platform == "win32":
            possible_paths = [
                r"D:\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break

        prepared = ImageOps.grayscale(image)
        prepared = ImageEnhance.Contrast(prepared).enhance(1.4)
        if min(prepared.size) < 1200:
            prepared = prepared.resize((prepared.width * 2, prepared.height * 2))
        prepared = prepared.filter(ImageFilter.MedianFilter(size=3))
        try:
            data = pytesseract.image_to_data(prepared, output_type=pytesseract.Output.DICT, config="--psm 6")
        except pytesseract.TesseractNotFoundError:
            return OCRPage(
                page_number=page_number,
                error="Unable to extract text: Windows OCR returned no text and Tesseract is not installed.",
            )
        regions, words, confidences = [], [], []
        lines_map = {}
        for index, raw_text in enumerate(data["text"]):
            word = raw_text.strip()
            try:
                confidence = float(data["conf"][index]) / 100
            except (TypeError, ValueError):
                confidence = None
            if not word or confidence is None or confidence < 0:
                continue
            left, top, width, height = (int(data[key][index]) for key in ("left", "top", "width", "height"))
            bbox = [left, top, left + width, top + height]
            regions.append(OCRRegion(text=word, confidence=min(confidence, 1.0), bbox=bbox))
            line_idx = (data.get("block_num", [0])[index], data.get("line_num", [0])[index])
            lines_map.setdefault(line_idx, []).append(word)
            confidences.append(min(confidence, 1.0))

        page_text = "\n".join(" ".join(line_words) for line_words in lines_map.values()) if lines_map else " ".join(words)
        return OCRPage(
            page_number=page_number, text=page_text,
            confidence=(sum(confidences) / len(confidences)) if confidences else None,
            regions=regions,
        )

    @staticmethod
    def _error(message: str, source_type: Optional[str] = None) -> OCRResult:
        return OCRResult(success=False, source_type=source_type, errors=[message])
