from schemas.core import OCRPage, OCRResult
from agents.ocr import OCRAgent
from agents.orchestrator import graph


def test_file_type_detection():
    agent = OCRAgent()
    assert agent.detect_file_type(b"%PDF-1.7\n") == "pdf"
    assert agent.detect_file_type(b"\x89PNG\r\n\x1a\ncontents") == "png"
    assert agent.detect_file_type(b"\xff\xd8\xff\xe0contents") == "jpeg"
    assert agent.process(b"not a document").success is False


def test_corrupt_image_is_reported():
    result = OCRAgent().process(b"\x89PNG\r\n\x1a\ntruncated")
    assert result.success is False
    assert result.errors


def test_multipage_ocr_combines_pages_without_discarding_them(monkeypatch):
    agent = OCRAgent()
    monkeypatch.setattr(agent, "_to_images", lambda data, source_type: ["one", "two"])
    monkeypatch.setattr(agent, "_recognize_page", lambda image, page: OCRPage(
        page_number=page, text=f"Metformin page {page}", confidence=0.9
    ))
    result = agent.process(b"%PDF-1.7\nmock")
    assert result.success is True
    assert result.pages_processed == 2
    assert "Page 1:" in result.text and "Page 2:" in result.text
    assert result.overall_confidence == 0.9


def test_failed_page_and_empty_result_are_observable(monkeypatch):
    agent = OCRAgent()
    monkeypatch.setattr(agent, "_to_images", lambda data, source_type: ["bad"])
    monkeypatch.setattr(agent, "_recognize_page", lambda image, page: OCRPage(page_number=page, error="engine unavailable"))
    result = agent.process(b"\xff\xd8\xffmock")
    assert result.success is False
    assert result.pages_failed == 1
    assert "OCR returned no readable text" in result.warnings


def test_ocr_text_reaches_existing_ner_pipeline():
    final = graph.invoke({
        "document_id": "OCR_INTEGRATION",
        "original_text": "Page 1: Patient treated with Metformin.",
        "source_text": "Page 1: Patient treated with Metformin.",
        "source_type": "pdf",
        "ocr_result": OCRResult(success=True, text="Page 1: Patient treated with Metformin.", source_type="pdf", pages_processed=1),
    })
    assert any(entity.text.lower().startswith("metformin") for entity in final["extracted_entities"])
