import sqlite3
import json
import os
from typing import Optional
from schemas.core import ReportState

DB_PATH = os.path.join(os.path.dirname(__file__), "reports.db")

def init_db(db_path=DB_PATH):
    """Initializes the SQLite database and creates the reports table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            document_id TEXT PRIMARY KEY,
            original_text TEXT,
            summary TEXT,
            execution_plan TEXT,
            extracted_entities TEXT,
            relations TEXT,
            verifier_flags TEXT,
            audit_trail TEXT,
            replan_count INTEGER,
            source_text TEXT,
            source_type TEXT,
            source_file TEXT,
            ocr_result TEXT
        )
    ''')
    existing_columns = {row[1] for row in cursor.execute("PRAGMA table_info(reports)")}
    for name, definition in {
        "source_text": "TEXT", "source_type": "TEXT", "source_file": "TEXT", "ocr_result": "TEXT"
    }.items():
        if name not in existing_columns:
            cursor.execute(f"ALTER TABLE reports ADD COLUMN {name} {definition}")
    conn.commit()
    conn.close()

def save_report(state: ReportState, db_path=DB_PATH):
    """Saves a ReportState to the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO reports (
            document_id, original_text, summary, execution_plan,
            extracted_entities, relations, verifier_flags, audit_trail, replan_count,
            source_text, source_type, source_file, ocr_result
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        state.document_id,
        state.original_text,
        state.summary,
        json.dumps(state.execution_plan),
        json.dumps([e.model_dump() for e in state.extracted_entities]),
        json.dumps([r.model_dump() for r in state.relations]),
        json.dumps([f.model_dump() for f in state.verifier_flags]),
        json.dumps([a.model_dump() for a in state.audit_trail]),
        state.replan_count,
        state.source_text, state.source_type, state.source_file,
        json.dumps(state.ocr_result.model_dump()) if state.ocr_result else None,
    ))
    
    conn.commit()
    conn.close()

def get_report(document_id: str, db_path=DB_PATH) -> Optional[ReportState]:
    """Retrieves a ReportState from the database by its document_id."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM reports WHERE document_id = ?', (document_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None
        
    state_dict = {
        "document_id": row[0],
        "original_text": row[1],
        "summary": row[2],
        "execution_plan": json.loads(row[3]) if row[3] else [],
        "extracted_entities": json.loads(row[4]) if row[4] else [],
        "relations": json.loads(row[5]) if row[5] else [],
        "verifier_flags": json.loads(row[6]) if row[6] else [],
        "audit_trail": json.loads(row[7]) if row[7] else [],
        "replan_count": row[8] if row[8] is not None else 0,
        "source_text": row[9] if len(row) > 9 else None,
        "source_type": row[10] if len(row) > 10 else None,
        "source_file": row[11] if len(row) > 11 else None,
        "ocr_result": json.loads(row[12]) if len(row) > 12 and row[12] else None,
    }
    
    return ReportState(**state_dict)

init_db()
