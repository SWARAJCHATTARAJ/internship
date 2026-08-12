import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from schemas.core import AuditEvent, ReportState
from agents.ocr import OCRAgent
from agents.orchestrator import graph
from data.db import save_report, get_report
from tools.preprocessing import mask_phi, normalize_clinical_text

app = FastAPI(title="Clinical Report Understanding API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessRequest(BaseModel):
    document_id: str
    text: str


def _run_text_pipeline(document_id: str, text: str, *, source_text: str | None = None,
                       source_type: str | None = None, source_file: str | None = None,
                       ocr_result=None):
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
    initial_state = ReportState(
        document_id=document_id,
        original_text=text,
        source_text=source_text or text,
        source_type=source_type,
        source_file=source_file,
        ocr_result=ocr_result,
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
        return _run_text_pipeline(request.document_id, request.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/upload", response_model=ReportState)
async def process_upload(document_id: str = Form(...), file: UploadFile = File(...)):
    """OCR a supported document, then send its validated text through the normal graph."""
    payload = await file.read()
    result = OCRAgent().process(payload, file.filename)
    if not result.success:
        raise HTTPException(status_code=422, detail=result.model_dump())

    masked_text, _ = mask_phi(result.text)
    normalized_text = normalize_clinical_text(masked_text)
    try:
        return _run_text_pipeline(
            document_id, normalized_text, source_text=result.text,
            source_type=result.source_type, source_file=file.filename, ocr_result=result,
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

