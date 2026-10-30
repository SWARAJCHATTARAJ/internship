import sys
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse, StreamingResponse

from schemas.core import AuditEvent, ReportState
from agents.ocr import OCRAgent
from agents.document import DocumentAgent
from agents.orchestrator import graph
from data.db import (
    get_report,
    get_upload_content,
    init_db,
    list_agent_outputs,
    list_audit_events,
    list_reports,
    list_uploads,
    save_report,
    save_upload,
)
from tools.preprocessing import mask_phi, normalize_clinical_text


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(title="Clinical Report Understanding API", lifespan=lifespan)

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
    save_upload(document_id, file.filename or "upload", payload, file.content_type)
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


@app.get("/reports", response_model=list)
async def list_reports_endpoint(limit: int = Query(default=20, ge=1, le=100)):
    """List recent reports with their summary and replan metadata."""
    return list_reports(limit=limit)


@app.get("/agents/outputs")
async def api_list_agent_outputs(
    document_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    agent_name: str | None = None,
):
    """List a report's stored agent outputs."""
    return JSONResponse(
        list_agent_outputs(
            document_id, page=page, page_size=page_size, agent_name=agent_name
        )
    )


@app.get("/agents/audit")
async def api_list_audit_events(
    document_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """List a report's audit events."""
    return JSONResponse(
        list_audit_events(document_id, page=page, page_size=page_size)
    )


@app.get("/files")
async def api_list_uploads(document_id: str):
    """List uploaded files for a report."""
    return JSONResponse(list_uploads(document_id))


@app.get("/files/{upload_id}")
async def api_get_upload(upload_id: int):
    """Download an uploaded source document."""
    upload = get_upload_content(upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    filename = os.path.basename(upload["filename"]).replace('"', "_")
    filename = filename.replace("\r", "").replace("\n", "")
    return StreamingResponse(
        iter([upload["content"]]),
        media_type=upload.get("content_type") or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class RerunRequest(BaseModel):
    document_id: str


@app.post("/process/rerun", status_code=202)
async def api_rerun_report(request: RerunRequest):
    """Re-run the agent graph using a previously stored report."""
    existing = get_report(request.document_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Report not found")
    result = graph.invoke(existing)
    save_report(ReportState(**result))
    return {"status": "accepted", "document_id": request.document_id}
