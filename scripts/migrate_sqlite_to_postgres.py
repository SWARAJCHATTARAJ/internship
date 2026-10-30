import os
import sys
import json
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set DATABASE_URL for migration
DATABASE_URL = "postgresql://neondb_owner:npg_hCpk8bBxJV3l@ep-dawn-recipe-b5a6gotn-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
os.environ['DATABASE_URL'] = DATABASE_URL

import sqlite3
from data import db as data_db
from schemas.core import ReportState

SQLITE_PATH = os.path.join(PROJECT_ROOT, 'data', 'reports.db')

if not os.path.exists(SQLITE_PATH):
    print(f"No SQLite DB found at {SQLITE_PATH}. Nothing to migrate.")
    sys.exit(0)

conn = sqlite3.connect(SQLITE_PATH)
cursor = conn.cursor()

cursor.execute('SELECT * FROM reports')
rows = cursor.fetchall()
cols = [desc[0] for desc in cursor.description]
print(f"Found {len(rows)} rows to migrate.")

migrated = 0
for row in rows:
    row_dict = dict(zip(cols, row))
    state_dict = {
        'document_id': row_dict.get('document_id'),
        'original_text': row_dict.get('original_text') or "",
        'summary': row_dict.get('summary'),
        'execution_plan': json.loads(row_dict.get('execution_plan')) if row_dict.get('execution_plan') else [],
        'extracted_entities': json.loads(row_dict.get('extracted_entities')) if row_dict.get('extracted_entities') else [],
        'relations': json.loads(row_dict.get('relations')) if row_dict.get('relations') else [],
        'verifier_flags': json.loads(row_dict.get('verifier_flags')) if row_dict.get('verifier_flags') else [],
        'audit_trail': json.loads(row_dict.get('audit_trail')) if row_dict.get('audit_trail') else [],
        'replan_count': row_dict.get('replan_count') or 0,
        'source_text': row_dict.get('source_text'),
        'source_type': row_dict.get('source_type'),
        'source_file': row_dict.get('source_file'),
        'ocr_result': json.loads(row_dict.get('ocr_result')) if row_dict.get('ocr_result') else None,
        'document_analysis': json.loads(row_dict.get('document_analysis')) if row_dict.get('document_analysis') else None,
        'medications': json.loads(row_dict.get('medications')) if row_dict.get('medications') else [],
        'clinical_context': json.loads(row_dict.get('clinical_context')) if row_dict.get('clinical_context') else [],
        'final_result': json.loads(row_dict.get('final_result')) if row_dict.get('final_result') else None,
        'agent_outputs': json.loads(row_dict.get('agent_outputs')) if row_dict.get('agent_outputs') else {},
        'execution_trace': json.loads(row_dict.get('execution_trace')) if row_dict.get('execution_trace') else [],
        'replans': json.loads(row_dict.get('replans')) if row_dict.get('replans') else [],
    }
    try:
        state = ReportState(**state_dict)
        try:
            data_db.save_report(state)
            migrated += 1
        except Exception as inner_e:
            print(f"Failed to save {state.document_id}: {inner_e}")
            # Diagnose problematic payload types
            from data import db as diagnose_db
            payload = {
                "document_id": state.document_id,
                "original_text": state.original_text,
                "summary": state.summary,
                "execution_plan": state.execution_plan,
                "extracted_entities": [e.model_dump() for e in state.extracted_entities],
                "relations": [r.model_dump() for r in state.relations],
                "verifier_flags": [f.model_dump() for f in state.verifier_flags],
                "audit_trail": [a.model_dump() for a in state.audit_trail],
                "replan_count": state.replan_count,
                "source_text": state.source_text,
                "source_type": state.source_type,
                "source_file": state.source_file,
                "ocr_result": state.ocr_result.model_dump() if state.ocr_result else None,
                "document_analysis": state.document_analysis.model_dump() if state.document_analysis else None,
                "medications": [m.model_dump() for m in state.medications],
                "clinical_context": state.clinical_context,
                "final_result": state.final_result,
                "agent_outputs": state.agent_outputs,
                "execution_trace": state.execution_trace,
                "replans": state.replans,
            }
            for k, v in payload.items():
                print(f"  Field {k}: type={type(v)}")
            print("Skipping this record.")
    except Exception as e:
        print(f"Failed to migrate {state_dict.get('document_id')}: {e}")

print(f"Migration complete. Migrated {migrated}/{len(rows)} rows.")

cursor.close()
conn.close()
