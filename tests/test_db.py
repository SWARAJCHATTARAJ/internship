import os
import pytest
import sqlite3
from schemas.core import ReportState, ExtractedEntity, AuditEvent
from data.db import save_report, get_report, init_db

# Use a test DB
TEST_DB = os.path.join(os.path.dirname(__file__), "test_reports.db")

@pytest.fixture(autouse=True)
def setup_teardown():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_db_persistence():
    """
    Test that a ReportState can be successfully saved and perfectly retrieved from the database.
    """
    state = ReportState(
        document_id="TEST_DB_1",
        original_text="Test db text",
        summary="A summary",
        execution_plan=["ner_agent", "verifier_agent"],
        extracted_entities=[
            ExtractedEntity(id="E1", text="TestEntity", label="SYMPTOM", start_char=0, end_char=10)
        ],
        audit_trail=[
            AuditEvent(agent_name="ner_agent", action_type="TEST", details={"key": "value"})
        ],
        replan_count=1
    )
    
    # Save it
    save_report(state, db_path=TEST_DB)
    
    # Retrieve it
    retrieved = get_report("TEST_DB_1", db_path=TEST_DB)
    
    assert retrieved is not None
    assert retrieved.document_id == "TEST_DB_1"
    assert retrieved.original_text == "Test db text"
    assert retrieved.summary == "A summary"
    assert retrieved.execution_plan == ["ner_agent", "verifier_agent"]
    assert retrieved.replan_count == 1
    
    # Check complex nested Pydantic models
    assert len(retrieved.extracted_entities) == 1
    assert retrieved.extracted_entities[0].text == "TestEntity"
    assert retrieved.extracted_entities[0].label == "SYMPTOM"
    
    assert len(retrieved.audit_trail) == 1
    assert retrieved.audit_trail[0].agent_name == "ner_agent"
    assert retrieved.audit_trail[0].action_type == "TEST"
    assert retrieved.audit_trail[0].details["key"] == "value"

def test_db_not_found():
    """
    Test that retrieving a non-existent report returns None.
    """
    assert get_report("DOES_NOT_EXIST", db_path=TEST_DB) is None
