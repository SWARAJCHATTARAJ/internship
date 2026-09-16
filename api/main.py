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
from data.db import save_report, get_report, save_upload
from data.db import list_agent_outputs, list_audit_events, list_uploads, get_upload_content
from fastapi.responses import StreamingResponse, JSONResponse
from tools.preprocessing import mask_phi, normalize_clinical_text

app = FastAPI(title="Clinical Report Understanding API")

cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5174").split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.responses import HTMLResponse
from api.dashboard import DASHBOARD_HTML


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the interactive multi-agent clinical dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)


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
    # persist the raw uploaded file (best-effort)
    try:
        save_upload(document_id, file.filename, payload, getattr(file, 'content_type', None))
    except Exception:
        # do not fail the request if upload persistence is unavailable
        pass
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
async def list_reports_endpoint(limit: int = 20):
    """List recent reports (document_id, summary, replan_count, created_at)."""
    from data.db import list_reports
    return list_reports(limit=limit)


@app.get('/agents/outputs')
async def api_list_agent_outputs(document_id: str, page: int = 1, page_size: int = 20, agent_name: str | None = None):
    """List agent outputs for a document with pagination and optional agent_name filter."""
    return JSONResponse(list_agent_outputs(document_id, page=page, page_size=page_size, agent_name=agent_name))


@app.get('/agents/audit')
async def api_list_audit_events(document_id: str, page: int = 1, page_size: int = 20):
    """List audit events for a document with pagination."""
    return JSONResponse(list_audit_events(document_id, page=page, page_size=page_size))


@app.get('/files')
async def api_list_uploads(document_id: str):
    """List uploaded files for a document."""
    return JSONResponse(list_uploads(document_id))


@app.get('/files/{upload_id}')
async def api_get_upload(upload_id: int):
    """Download an uploaded file by upload id (Postgres only)."""
    data = get_upload_content(upload_id)
    if not data:
        raise HTTPException(status_code=404, detail='Upload not found')
    return StreamingResponse(iter([data['content']]), media_type=data.get('content_type') or 'application/octet-stream', headers={"Content-Disposition": f"attachment; filename=\"{data['filename']}\""})


class RerunRequest(BaseModel):
    document_id: str


@app.post('/process/rerun')
async def api_rerun_report(req: RerunRequest):
    """Trigger a re-run of the agent graph for an existing report.
    This re-invokes the graph with the stored state and saves the updated report.
    """
    existing = get_report(req.document_id)
    if not existing:
        raise HTTPException(status_code=404, detail='Report not found')
    # Reconstruct state and re-invoke the graph (best-effort)
    try:
        # existing is a dict-like pydantic object; convert to standard dict
        state = ReportState(**existing).model_dump()
    except Exception:
        state = existing
    # invoke graph with current state as starting point
    final = graph.invoke(state)
    try:
        save_report(ReportState(**final))
    except Exception:
        # best-effort save
        pass
    return JSONResponse({'status': 'accepted', 'document_id': req.document_id}, status_code=202)

