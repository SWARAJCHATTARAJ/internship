import sqlite3
import json
import os
from typing import Optional
from schemas.core import ReportState

# Local SQLite path (fallback)
DB_PATH = os.path.join(os.path.dirname(__file__), "reports.db")

# If a DATABASE_URL env var is set, use Postgres instead of SQLite
DATABASE_URL = os.getenv("DATABASE_URL")


def _pg_connect(url: str):
    import psycopg2
    from psycopg2.extras import Json
    conn = psycopg2.connect(url)
    return conn


def init_db(db_path: str = DB_PATH):
    """Initializes the database. Uses Postgres when DATABASE_URL set, otherwise SQLite."""
    if DATABASE_URL:
        conn = _pg_connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS reports (
                document_id TEXT PRIMARY KEY,
                original_text TEXT,
                summary TEXT,
                execution_plan JSONB,
                extracted_entities JSONB,
                relations JSONB,
                verifier_flags JSONB,
                audit_trail JSONB,
                replan_count INTEGER,
                source_text TEXT,
                source_type TEXT,
                source_file TEXT,
                ocr_result JSONB,
                document_analysis JSONB,
                medications JSONB,
                clinical_context JSONB,
                final_result JSONB,
                agent_outputs JSONB,
                execution_trace JSONB,
                replans JSONB
            )
            '''
        )
        # Ensure created_at column exists
        try:
            cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now()")
        except Exception:
            # Some Postgres versions may not support IF NOT EXISTS; ignore if fails
            pass
        # Create dedicated schemas for agent outputs and uploaded files
        try:
            cur.execute('CREATE SCHEMA IF NOT EXISTS agents')
            cur.execute('CREATE SCHEMA IF NOT EXISTS files')
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS agents.agent_outputs (
                    id SERIAL PRIMARY KEY,
                    document_id TEXT,
                    agent_name TEXT,
                    payload JSONB,
                    created_at TIMESTAMP DEFAULT now()
                )
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS agents.audit_events (
                    id SERIAL PRIMARY KEY,
                    document_id TEXT,
                    event JSONB,
                    created_at TIMESTAMP DEFAULT now()
                )
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS files.uploads (
                    id SERIAL PRIMARY KEY,
                    document_id TEXT,
                    filename TEXT,
                    content BYTEA,
                    content_type TEXT,
                    created_at TIMESTAMP DEFAULT now()
                )
                '''
            )
            # create helpful indexes
            cur.execute('CREATE INDEX IF NOT EXISTS idx_agents_outputs_doc ON agents.agent_outputs (document_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_agents_outputs_agent ON agents.agent_outputs (agent_name)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_agents_audit_doc ON agents.audit_events (document_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_files_uploads_doc ON files.uploads (document_id)')
        except Exception:
            # Ignore schema/table creation errors to preserve backward compatibility
            pass
        conn.commit()
        cur.close()
        conn.close()
        return

    # SQLite fallback
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
            ocr_result TEXT,
            document_analysis TEXT,
            medications TEXT,
            clinical_context TEXT,
            final_result TEXT
            ,agent_outputs TEXT
            ,execution_trace TEXT
            ,replans TEXT
        )
    ''')
    existing_columns = {row[1] for row in cursor.execute("PRAGMA table_info(reports)")}
    for name, definition in {
        "source_text": "TEXT", "source_type": "TEXT", "source_file": "TEXT", "ocr_result": "TEXT",
        "document_analysis": "TEXT", "medications": "TEXT", "clinical_context": "TEXT", "final_result": "TEXT",
        "agent_outputs": "TEXT", "execution_trace": "TEXT", "replans": "TEXT"
    }.items():
        if name not in existing_columns:
            cursor.execute(f"ALTER TABLE reports ADD COLUMN {name} {definition}")
    # Add created_at for SQLite if missing. SQLite restricts non-constant DEFAULTs
    # in ALTER TABLE on some versions, so add the column without a default and
    # backfill existing rows with the current timestamp.
    if 'created_at' not in existing_columns:
        cursor.execute("ALTER TABLE reports ADD COLUMN created_at TEXT")
        try:
            cursor.execute("UPDATE reports SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        except Exception:
            # Some SQLite builds may not support CURRENT_TIMESTAMP in UPDATE; ignore if fails
            pass
    conn.commit()
    conn.close()


def save_report(state: ReportState, db_path: str = DB_PATH):
    """Saves a ReportState to Postgres (if configured) or SQLite."""
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

    if DATABASE_URL:
        conn = _pg_connect(DATABASE_URL)
        from psycopg2.extras import Json
        cur = conn.cursor()
        cur.execute(
            '''
            INSERT INTO reports (
                document_id, original_text, summary, execution_plan,
                extracted_entities, relations, verifier_flags, audit_trail, replan_count,
                source_text, source_type, source_file, ocr_result, document_analysis, medications, clinical_context, final_result,
                agent_outputs, execution_trace, replans
            ) VALUES (%(document_id)s, %(original_text)s, %(summary)s, %(execution_plan)s,
                      %(extracted_entities)s, %(relations)s, %(verifier_flags)s, %(audit_trail)s, %(replan_count)s,
                      %(source_text)s, %(source_type)s, %(source_file)s, %(ocr_result)s, %(document_analysis)s, %(medications)s, %(clinical_context)s, %(final_result)s,
                      %(agent_outputs)s, %(execution_trace)s, %(replans)s)
            ON CONFLICT (document_id) DO UPDATE SET
              original_text = EXCLUDED.original_text,
              summary = EXCLUDED.summary,
              execution_plan = EXCLUDED.execution_plan,
              extracted_entities = EXCLUDED.extracted_entities,
              relations = EXCLUDED.relations,
              verifier_flags = EXCLUDED.verifier_flags,
              audit_trail = EXCLUDED.audit_trail,
              replan_count = EXCLUDED.replan_count,
              source_text = EXCLUDED.source_text,
              source_type = EXCLUDED.source_type,
              source_file = EXCLUDED.source_file,
              ocr_result = EXCLUDED.ocr_result,
              document_analysis = EXCLUDED.document_analysis,
              medications = EXCLUDED.medications,
              clinical_context = EXCLUDED.clinical_context,
              final_result = EXCLUDED.final_result,
              agent_outputs = EXCLUDED.agent_outputs,
              execution_trace = EXCLUDED.execution_trace,
              replans = EXCLUDED.replans
            ''', {
                    **{k: Json(v) if k in ("execution_plan", "extracted_entities", "relations", "verifier_flags", "audit_trail", "ocr_result", "document_analysis", "medications", "clinical_context", "final_result", "agent_outputs", "execution_trace", "replans") else v for k, v in payload.items()}
            }
        )
        conn.commit()
        # store individual agent outputs and audit events in dedicated tables for querying
        try:
            # agent outputs: expect a dict of {agent_name: payload}
            if isinstance(state.agent_outputs, dict):
                for agent_name, payload_obj in state.agent_outputs.items():
                    try:
                        cur.execute(
                            'INSERT INTO agents.agent_outputs (document_id, agent_name, payload) VALUES (%s, %s, %s)',
                            (state.document_id, agent_name, Json(payload_obj))
                        )
                    except Exception:
                        conn.rollback()
                        pass

            # audit events: each event should be JSON-serializable
            for ev in state.audit_trail:
                try:
                    # if Pydantic model, convert
                    ev_obj = ev.model_dump() if hasattr(ev, 'model_dump') else ev
                    cur.execute(
                        'INSERT INTO agents.audit_events (document_id, event) VALUES (%s, %s)',
                        (state.document_id, Json(ev_obj))
                    )
                except Exception:
                    conn.rollback()
                    pass
        except Exception:
            # best-effort: do not fail saving the main report
            pass
        # commit any agent/audit inserts (best-effort)
        try:
            conn.commit()
        except Exception:
            pass
        cur.close()
        conn.close()
        return

    # SQLite fallback
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO reports (
            document_id, original_text, summary, execution_plan,
            extracted_entities, relations, verifier_flags, audit_trail, replan_count,
            source_text, source_type, source_file, ocr_result, document_analysis, medications, clinical_context, final_result,
            agent_outputs, execution_trace, replans
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        payload["document_id"],
        payload["original_text"],
        payload["summary"],
        json.dumps(payload["execution_plan"]),
        json.dumps(payload["extracted_entities"]),
        json.dumps(payload["relations"]),
        json.dumps(payload["verifier_flags"]),
        json.dumps(payload["audit_trail"]),
        payload["replan_count"],
        payload["source_text"], payload["source_type"], payload["source_file"],
        json.dumps(payload["ocr_result"]) if payload["ocr_result"] else None,
        json.dumps(payload["document_analysis"]) if payload["document_analysis"] else None,
        json.dumps(payload["medications"]), json.dumps(payload["clinical_context"]),
        json.dumps(payload["final_result"]) if payload["final_result"] else None,
        json.dumps(payload["agent_outputs"]), json.dumps(payload["execution_trace"]), json.dumps(payload["replans"]),
    ))
    conn.commit()
    conn.close()


def get_report(document_id: str, db_path: str = DB_PATH) -> Optional[ReportState]:
    """Retrieves a ReportState from Postgres (if configured) or SQLite by its document_id."""
    if DATABASE_URL:
        conn = _pg_connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            'SELECT document_id, original_text, summary, execution_plan, extracted_entities, relations, verifier_flags, '
            'audit_trail, replan_count, source_text, source_type, source_file, ocr_result, document_analysis, '
            'medications, clinical_context, final_result, agent_outputs, execution_trace, replans '
            'FROM reports WHERE document_id = %s', (document_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row is None:
            return None
        # Map columns by index as created above
        (document_id, original_text, summary, execution_plan, extracted_entities, relations, verifier_flags,
         audit_trail, replan_count, source_text, source_type, source_file, ocr_result, document_analysis,
         medications, clinical_context, final_result, agent_outputs, execution_trace, replans) = row

        state_dict = {
            "document_id": document_id,
            "original_text": original_text,
            "summary": summary,
            "execution_plan": execution_plan or [],
            "extracted_entities": extracted_entities or [],
            "relations": relations or [],
            "verifier_flags": verifier_flags or [],
            "audit_trail": audit_trail or [],
            "replan_count": replan_count or 0,
            "source_text": source_text,
            "source_type": source_type,
            "source_file": source_file,
            "ocr_result": ocr_result,
            "document_analysis": document_analysis,
            "medications": medications or [],
            "clinical_context": clinical_context or [],
            "final_result": final_result,
            "agent_outputs": agent_outputs or {},
            "execution_trace": execution_trace or [],
            "replans": replans or [],
        }
        return ReportState(**state_dict)

    # SQLite fallback
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
        "document_analysis": json.loads(row[13]) if len(row) > 13 and row[13] else None,
        "medications": json.loads(row[14]) if len(row) > 14 and row[14] else [],
        "clinical_context": json.loads(row[15]) if len(row) > 15 and row[15] else [],
        "final_result": json.loads(row[16]) if len(row) > 16 and row[16] else None,
        "agent_outputs": json.loads(row[17]) if len(row) > 17 and row[17] else {},
        "execution_trace": json.loads(row[18]) if len(row) > 18 and row[18] else [],
        "replans": json.loads(row[19]) if len(row) > 19 and row[19] else [],
    }

    return ReportState(**state_dict)


def save_upload(document_id: str, filename: str, content: bytes, content_type: str | None = None, db_path: str = DB_PATH):
    """Store an uploaded file into Postgres `files.uploads` (best-effort)."""
    if not DATABASE_URL:
        # fallback: store file to a local uploads directory
        uploads_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        safe_name = f"{document_id}_{os.path.basename(filename)}"
        path = os.path.join(uploads_dir, safe_name)
        with open(path, 'wb') as f:
            f.write(content)
        return path

    import psycopg2
    conn = _pg_connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        cur.execute(
            'INSERT INTO files.uploads (document_id, filename, content, content_type) VALUES (%s, %s, %s, %s)',
            (document_id, filename, psycopg2.Binary(content), content_type)
        )
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def list_reports(limit: int = 20, db_path: str = DB_PATH):
    """Return a list of recent reports with minimal metadata."""
    results = []
    if DATABASE_URL:
        conn = _pg_connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute('SELECT document_id, summary, replan_count, created_at FROM reports ORDER BY created_at DESC LIMIT %s', (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for r in rows:
            results.append({
                'document_id': r[0],
                'summary': r[1],
                'replan_count': r[2],
                'created_at': r[3].isoformat() if hasattr(r[3], 'isoformat') else r[3]
            })
        return results

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT document_id, summary, replan_count, created_at FROM reports ORDER BY rowid DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    for r in rows:
        results.append({
            'document_id': r[0],
            'summary': r[1],
            'replan_count': r[2],
            'created_at': r[3]
        })
    return results


def list_agent_outputs(document_id: str, page: int = 1, page_size: int = 20, agent_name: str | None = None):
    """Return agent outputs for a document with pagination and optional agent_name filter."""
    results = []
    if DATABASE_URL:
        conn = _pg_connect(DATABASE_URL)
        cur = conn.cursor()
        offset = (max(page, 1) - 1) * max(page_size, 1)
        if agent_name:
            cur.execute('SELECT id, agent_name, payload, created_at FROM agents.agent_outputs WHERE document_id = %s AND agent_name = %s ORDER BY created_at DESC LIMIT %s OFFSET %s', (document_id, agent_name, page_size, offset))
        else:
            cur.execute('SELECT id, agent_name, payload, created_at FROM agents.agent_outputs WHERE document_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s', (document_id, page_size, offset))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for r in rows:
            results.append({'id': r[0], 'agent_name': r[1], 'payload': r[2], 'created_at': r[3].isoformat() if hasattr(r[3], 'isoformat') else r[3]})
        return results
    return results


def list_audit_events(document_id: str, page: int = 1, page_size: int = 20):
    """Return audit events for a document with pagination (most recent first)."""
    results = []
    if DATABASE_URL:
        conn = _pg_connect(DATABASE_URL)
        cur = conn.cursor()
        offset = (max(page, 1) - 1) * max(page_size, 1)
        cur.execute('SELECT id, event, created_at FROM agents.audit_events WHERE document_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s', (document_id, page_size, offset))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for r in rows:
            results.append({'id': r[0], 'event': r[1], 'created_at': r[2].isoformat() if hasattr(r[2], 'isoformat') else r[2]})
        return results
    return results


def list_uploads(document_id: str):
    """List uploaded files for a document.

    Returns metadata rows with `id`, `filename`, `content_type`, `created_at`.
    """
    results = []
    if DATABASE_URL:
        conn = _pg_connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute('SELECT id, filename, content_type, created_at FROM files.uploads WHERE document_id = %s ORDER BY created_at DESC', (document_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for r in rows:
            results.append({'id': r[0], 'filename': r[1], 'content_type': r[2], 'created_at': r[3].isoformat() if hasattr(r[3], 'isoformat') else r[3]})
        return results

    # fallback: list files saved to uploads/ directory
    uploads_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    if not os.path.isdir(uploads_dir):
        return results
    for fname in os.listdir(uploads_dir):
        if fname.startswith(f"{document_id}_"):
            path = os.path.join(uploads_dir, fname)
            stat = os.stat(path)
            results.append({'id': None, 'filename': fname.split('_', 1)[1], 'content_type': None, 'created_at': None})
    return results


def get_upload_content(upload_id: int):
    """Return raw bytes and content_type for a given upload id (Postgres only)."""
    if not DATABASE_URL:
        return None
    import psycopg2
    conn = _pg_connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('SELECT filename, content, content_type FROM files.uploads WHERE id = %s', (upload_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    filename, content, content_type = row
    return {'filename': filename, 'content': bytes(content), 'content_type': content_type}


init_db()
