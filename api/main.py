import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from schemas.core import ReportState
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

@app.post("/process", response_model=ReportState)
async def process_report(request: ProcessRequest):
    """
    Endpoint to process a clinical report through the multi-agent graph.
    """
    masked_text, _ = mask_phi(request.text)
    normalized_text = normalize_clinical_text(masked_text)
    initial_state = ReportState(
        document_id=request.document_id,
        original_text=request.text,
        source_text=request.text,
    )

    try:
        final_state = graph.invoke(initial_state)
        state_obj = ReportState(**final_state)
        save_report(state_obj)
        return final_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/{document_id}", response_model=ReportState)
async def get_report_endpoint(document_id: str):
    """
    Endpoint to fetch a processed report from the database.
    """
    report = get_report(document_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

