import pytest
from fastapi.testclient import TestClient
from api.main import app
from schemas.core import ReportState

client = TestClient(app)

def test_process_report_simple():
    """
    Test that the API endpoint successfully processes a simple report.
    """
    payload = {
        "document_id": "API_TEST_1",
        "text": "Patient has abdominal pain."
    }
    
    response = client.post("/process", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that the basic structure is returned
    assert data["document_id"] == "API_TEST_1"
    assert data["original_text"] == "Patient has abdominal pain."
    
    # Check that the execution plan triggered NER (simple)
    assert "ner_agent" in data["execution_plan"]
    
def test_process_report_complex():
    """
    Test that the API endpoint successfully processes a complex report.
    """
    payload = {
        "document_id": "API_TEST_2",
        "text": "Patient admitted with abdominal pain history. Diagnosed with Diabetes Mellitus. Prescribed medication Metformin."
    }
    
    response = client.post("/process", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that it triggered the full suite including grounding and relation
    assert "relation_agent" in data["execution_plan"]
    
    # Check that entities were extracted and grounded
    assert len(data["extracted_entities"]) > 0
    assert "Metformin" in [e["text"] for e in data["extracted_entities"]]
    
    # Check that relations were mapped
    assert len(data["relations"]) > 0
    
    # Check that a summary was generated
    assert data["summary"] is not None
    assert "Clinical Summary" in data["summary"]


def test_preserved_reporting_and_file_endpoints(monkeypatch):
    import api.main as api_main

    monkeypatch.setattr(api_main, "list_reports", lambda limit: [{"document_id": "DOC-1"}])
    monkeypatch.setattr(
        api_main,
        "list_agent_outputs",
        lambda document_id, page, page_size, agent_name: [{"agent_name": "ner"}],
    )
    monkeypatch.setattr(
        api_main,
        "list_audit_events",
        lambda document_id, page, page_size: [{"event": {"action_type": "TEST"}}],
    )
    monkeypatch.setattr(api_main, "list_uploads", lambda document_id: [{"id": 7}])
    monkeypatch.setattr(
        api_main,
        "get_upload_content",
        lambda upload_id: {
            "filename": "report.pdf",
            "content": b"pdf bytes",
            "content_type": "application/pdf",
        },
    )

    assert client.get("/reports").json() == [{"document_id": "DOC-1"}]
    assert client.get("/agents/outputs?document_id=DOC-1").json() == [{"agent_name": "ner"}]
    assert client.get("/agents/audit?document_id=DOC-1").json() == [
        {"event": {"action_type": "TEST"}}
    ]
    assert client.get("/files?document_id=DOC-1").json() == [{"id": 7}]
    download = client.get("/files/7")
    assert download.status_code == 200
    assert download.content == b"pdf bytes"
    assert 'filename="report.pdf"' in download.headers["content-disposition"]


def test_rerun_endpoint_uses_stored_report(monkeypatch):
    import api.main as api_main

    state = ReportState(document_id="DOC-RERUN", original_text="Patient follow-up.")
    saved = []

    class FakeGraph:
        def invoke(self, existing):
            assert existing.document_id == state.document_id
            return existing.model_dump()

    monkeypatch.setattr(api_main, "get_report", lambda document_id: state)
    monkeypatch.setattr(api_main, "graph", FakeGraph())
    monkeypatch.setattr(api_main, "save_report", saved.append)

    response = client.post("/process/rerun", json={"document_id": state.document_id})
    assert response.status_code == 202
    assert response.json() == {"status": "accepted", "document_id": state.document_id}
    assert len(saved) == 1
    assert saved[0].document_id == state.document_id
