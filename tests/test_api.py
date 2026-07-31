import pytest
from fastapi.testclient import TestClient
from api.main import app

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
