import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from schemas.core import AuditEvent, ReportState
from agents.ocr import OCRAgent
from agents.document import DocumentAgent
from agents.orchestrator import graph
from data.db import save_report, get_report
from tools.preprocessing import mask_phi, normalize_clinical_text

app = FastAPI(title="Clinical Report Understanding API")

cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Container health probe; does not access document data."""
    return {"status": "ok"}


class ProcessRequest(BaseModel):
    document_id: str
    text: str


def _run_text_pipeline(document_id: str, text: str, *, source_text: str | None = None,
                       source_type: str | None = None, source_file: str | None = None,
                       ocr_result=None, document_analysis=None):
    audit_trail = []
    if ocr_result is not None:
        audit_trail.append(AuditEvent(
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
    if document_analysis is not None:
        audit_trail.append(AuditEvent(
            agent_name="document_agent", action_type="DOCUMENT_ANALYSIS",
            details=document_analysis.model_dump(),
        ))
    initial_state = ReportState(
        document_id=document_id,
        original_text=text,
        source_text=source_text or text,
        source_type=source_type,
        source_file=source_file,
        ocr_result=ocr_result,
        document_analysis=document_analysis,
        audit_trail=audit_trail,
    )
    final_state = graph.invoke(initial_state)
    state_obj = ReportState(**final_state)
    save_report(state_obj)
    return final_state

@app.post("/process", response_model=ReportState)
async def process_report(request: ProcessRequest):
    """
    Endpoint to process a clinical report through the multi-agent graph.
    """
    try:
        # Preserve the established text endpoint behavior: text is not OCR'd.
        analysis = DocumentAgent().analyze_text(request.text)
        return _run_text_pipeline(request.document_id, request.text, document_analysis=analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/upload", response_model=ReportState)
async def process_upload(document_id: str = Form(...), file: UploadFile = File(...)):
    """Characterize an upload, then use native PDF text or OCR as appropriate."""
    payload = await file.read()
    document_agent = DocumentAgent()
    analysis, native_text = document_agent.analyze_file(payload, file.filename)
    result = None
    if analysis.requires_ocr:
        result = OCRAgent().process(payload, file.filename)
        if not result.success:
            raise HTTPException(status_code=422, detail=result.model_dump())
        source_text = result.text
        # For image uploads, text classification is only possible after OCR.
        if analysis.document_type == "unknown":
            analysis = analysis.model_copy(update={"document_type": document_agent._document_type(source_text)})
    elif native_text:
        source_text = native_text
    else:
        raise HTTPException(status_code=422, detail="Unsupported or unreadable document")

    masked_text, _ = mask_phi(source_text)
    normalized_text = normalize_clinical_text(masked_text)
    try:
        return _run_text_pipeline(
            document_id, normalized_text, source_text=source_text,
            source_type=(result.source_type if result else "pdf"), source_file=file.filename,
            ocr_result=result, document_analysis=analysis,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.get("/reports/{document_id}", response_model=ReportState)
async def get_report_endpoint(document_id: str):
    """
    Endpoint to fetch a processed report from the database.
    """
    report = get_report(document_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

