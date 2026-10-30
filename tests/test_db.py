import os
import pytest
import sqlite3
from schemas.core import ReportState, ExtractedEntity, AuditEvent
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


def test_report_metadata_and_upload_helpers():
    state = ReportState(
        document_id="TEST_DB_HELPERS",
        original_text="Helper test",
        summary="Persisted summary",
        replan_count=2,
        agent_outputs={"ner": {"entities": 1}, "relation": {"relations": 2}},
        audit_trail=[
            AuditEvent(agent_name="ner_agent", action_type="EXTRACTION"),
            AuditEvent(agent_name="finalizer_agent", action_type="FINAL_OUTPUT"),
        ],
    )
    save_report(state, db_path=TEST_DB)

    reports = list_reports(db_path=TEST_DB)
    assert reports[0]["document_id"] == "TEST_DB_HELPERS"
    assert reports[0]["summary"] == "Persisted summary"
    assert reports[0]["replan_count"] == 2

    assert list_agent_outputs(
        "TEST_DB_HELPERS", page_size=1, db_path=TEST_DB
    ) == [{
        "id": 2,
        "agent_name": "relation",
        "payload": {"relations": 2},
        "created_at": reports[0]["created_at"],
    }]
    assert list_agent_outputs(
        "TEST_DB_HELPERS", agent_name="ner", db_path=TEST_DB
    )[0]["payload"] == {"entities": 1}
    assert list_audit_events(
        "TEST_DB_HELPERS", page_size=1, db_path=TEST_DB
    )[0]["event"]["action_type"] == "FINAL_OUTPUT"

    save_upload(
        "TEST_DB_HELPERS",
        "report.pdf",
        b"pdf bytes",
        "application/pdf",
        db_path=TEST_DB,
    )
    uploads = list_uploads("TEST_DB_HELPERS", db_path=TEST_DB)
    assert len(uploads) == 1
    assert uploads[0]["filename"] == "report.pdf"
    assert get_upload_content(uploads[0]["id"], db_path=TEST_DB) == {
        "filename": "report.pdf",
        "content": b"pdf bytes",
        "content_type": "application/pdf",
    }


def test_existing_sqlite_schema_is_migrated_without_losing_reports():
    legacy_db = os.path.join(os.path.dirname(__file__), "legacy_test_reports.db")
    if os.path.exists(legacy_db):
        os.remove(legacy_db)
    conn = sqlite3.connect(legacy_db)
    try:
        conn.execute(
            """
            CREATE TABLE reports (
                document_id TEXT PRIMARY KEY,
                original_text TEXT,
                summary TEXT,
                execution_plan TEXT,
                extracted_entities TEXT,
                relations TEXT,
                verifier_flags TEXT,
                audit_trail TEXT,
                replan_count INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO reports VALUES (
                'LEGACY_REPORT', 'Preserve this report', 'Legacy summary',
                '[]', '[]', '[]', '[]', '[]', 0
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
    try:
        init_db(legacy_db)
        report = get_report("LEGACY_REPORT", db_path=legacy_db)
        assert report is not None
        assert report.original_text == "Preserve this report"
        assert report.summary == "Legacy summary"
        assert list_reports(db_path=legacy_db)[0]["document_id"] == "LEGACY_REPORT"
    finally:
        if os.path.exists(legacy_db):
            os.remove(legacy_db)
