"""Persistence for clinical reports, inputs, agent outputs, and audit events."""

from __future__ import annotations
from contextlib import closing
import json
import os
import sqlite3
from typing import Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from schemas.core import ReportState
DB_PATH = os.path.join(os.path.dirname(__file__), "reports.db")
DATABASE_URL = os.getenv("DATABASE_URL")

def _json(value: Any) -> str:
    return json.dumps(value, default=str)

def _state_payload(state: ReportState) -> dict[str, Any]:
    return state.model_dump(mode="json")

def _init_sqlite(db_path: str) -> None:
    with closing(sqlite3.connect(db_path)) as conn, conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                document_id TEXT PRIMARY KEY, original_text TEXT, summary TEXT,
                execution_plan TEXT, extracted_entities TEXT, relations TEXT,
                verifier_flags TEXT, audit_trail TEXT, replan_count INTEGER,
                source_text TEXT, source_type TEXT, source_file TEXT, ocr_result TEXT,
                document_analysis TEXT, medications TEXT, clinical_context TEXT,
                final_result TEXT, agent_outputs TEXT, execution_trace TEXT,
                replans TEXT, timeline TEXT, fhir_draft TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing_columns = {row[1] for row in cursor.execute("PRAGMA table_info(reports)")}
        for name, definition in {
            "source_text": "TEXT",
            "source_type": "TEXT",
            "source_file": "TEXT",
            "ocr_result": "TEXT",
            "document_analysis": "TEXT",
            "medications": "TEXT",
            "clinical_context": "TEXT",
            "final_result": "TEXT",
            "agent_outputs": "TEXT",
            "execution_trace": "TEXT",
            "replans": "TEXT",
            "timeline": "TEXT",
            "fhir_draft": "TEXT",
            "created_at": "TEXT",
        }.items():
            if name not in existing_columns:
                cursor.execute(f"ALTER TABLE reports ADD COLUMN {name} {definition}")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                content BLOB NOT NULL,
                content_type TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("UPDATE reports SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

def _init_postgres() -> None:
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS agents")
        conn.execute("CREATE SCHEMA IF NOT EXISTS files")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agents.agent_outputs (
                id BIGSERIAL PRIMARY KEY,
                document_id TEXT,
                agent_name TEXT,
                payload JSONB,
                created_at TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agents.audit_events (
                id BIGSERIAL PRIMARY KEY,
                document_id TEXT,
                event JSONB,
                created_at TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS files.uploads (
                id BIGSERIAL PRIMARY KEY,
                document_id TEXT,
                filename TEXT,
                content BYTEA,
                content_type TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute("CREATE SCHEMA IF NOT EXISTS clinical")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clinical.reports (
                document_id TEXT PRIMARY KEY,
                state JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clinical.report_inputs (
                document_id TEXT PRIMARY KEY REFERENCES clinical.reports(document_id) ON DELETE CASCADE,
                original_text TEXT NOT NULL,
                source_text TEXT,
                source_type TEXT,
                source_file TEXT,
                ocr_result JSONB,
                document_analysis JSONB,
                received_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clinical.report_outputs (
                document_id TEXT PRIMARY KEY REFERENCES clinical.reports(document_id) ON DELETE CASCADE,
                summary TEXT,
                final_result JSONB,
                execution_plan JSONB NOT NULL DEFAULT '[]'::jsonb,
                execution_trace JSONB NOT NULL DEFAULT '[]'::jsonb,
                replan_count INTEGER NOT NULL DEFAULT 0,
                replans JSONB NOT NULL DEFAULT '[]'::jsonb,
                state JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clinical_reports_updated ON clinical.reports(updated_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_document ON agents.audit_events(document_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_outputs_document ON agents.agent_outputs(document_id)")
        conn.commit()

def init_db(db_path: Optional[str] = None) -> None:
    """Initialize Postgres when configured, otherwise initialize the local test store."""
    if db_path or not DATABASE_URL:
        _init_sqlite(db_path or DB_PATH)
    else:
        _init_postgres()

def _save_sqlite(state: ReportState, db_path: str) -> None:
    payload = _state_payload(state)
    values = {
        key: _json(payload[key])
        for key in (
            "execution_plan", "extracted_entities", "relations", "verifier_flags",
            "audit_trail", "ocr_result", "document_analysis", "medications",
            "clinical_context", "final_result", "agent_outputs", "execution_trace",
            "replans", "timeline", "fhir_draft",
        )
    }
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT OR REPLACE INTO reports (
            document_id, original_text, summary, execution_plan, extracted_entities,
            relations, verifier_flags, audit_trail, replan_count, source_text,
            source_type, source_file, ocr_result, document_analysis, medications,
            clinical_context, final_result, agent_outputs, execution_trace, replans,
            timeline, fhir_draft, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            state.document_id, state.original_text, state.summary, values["execution_plan"],
            values["extracted_entities"], values["relations"], values["verifier_flags"],
            values["audit_trail"], state.replan_count, state.source_text, state.source_type,
            state.source_file, values["ocr_result"], values["document_analysis"],
            values["medications"], values["clinical_context"], values["final_result"],
            values["agent_outputs"], values["execution_trace"], values["replans"],
            values["timeline"], values["fhir_draft"],
        ),
    )
    conn.commit()
    conn.close()

def _save_postgres(state: ReportState) -> None:
    import psycopg

    payload = _state_payload(state)
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            """
            INSERT INTO clinical.reports (document_id, state, updated_at)
            VALUES (%s, %s::jsonb, now())
            ON CONFLICT (document_id) DO UPDATE SET state = EXCLUDED.state, updated_at = now()
            """,
            (state.document_id, _json(payload)),
        )
        conn.execute(
            """
            INSERT INTO clinical.report_inputs
                (document_id, original_text, source_text, source_type, source_file, ocr_result, document_analysis)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
            ON CONFLICT (document_id) DO UPDATE SET
                original_text = EXCLUDED.original_text, source_text = EXCLUDED.source_text,
                source_type = EXCLUDED.source_type, source_file = EXCLUDED.source_file,
                ocr_result = EXCLUDED.ocr_result, document_analysis = EXCLUDED.document_analysis
            """,
            (state.document_id, state.original_text, state.source_text, state.source_type,
             state.source_file, _json(payload["ocr_result"]), _json(payload["document_analysis"])),
        )
        conn.execute(
            """
            INSERT INTO clinical.report_outputs
                (document_id, summary, final_result, execution_plan, execution_trace,
                 replan_count, replans, state)
            VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s::jsonb)
            ON CONFLICT (document_id) DO UPDATE SET
                summary = EXCLUDED.summary, final_result = EXCLUDED.final_result,
                execution_plan = EXCLUDED.execution_plan, execution_trace = EXCLUDED.execution_trace,
                replan_count = EXCLUDED.replan_count, replans = EXCLUDED.replans, state = EXCLUDED.state
            """,
            (state.document_id, state.summary, _json(payload["final_result"]),
             _json(state.execution_plan), _json(state.execution_trace), state.replan_count,
             _json(state.replans), _json(payload)),
        )
        conn.execute("DELETE FROM agents.agent_outputs WHERE document_id = %s", (state.document_id,))
        for agent_name, output in state.agent_outputs.items():
            conn.execute(
                "INSERT INTO agents.agent_outputs (document_id, agent_name, payload) VALUES (%s, %s, %s::jsonb)",
                (state.document_id, agent_name, _json(output)),
            )
        conn.execute("DELETE FROM agents.audit_events WHERE document_id = %s", (state.document_id,))
        for event in state.audit_trail:
            conn.execute(
                "INSERT INTO agents.audit_events (document_id, event) VALUES (%s, %s::jsonb)",
                (state.document_id, _json(event.model_dump(mode="json"))),
            )
        conn.commit()

def save_report(state: ReportState, db_path: Optional[str] = None) -> None:
    """Persist the complete input/output state and normalized agent telemetry."""
    if db_path or not DATABASE_URL:
        _save_sqlite(state, db_path or DB_PATH)
    else:
        _save_postgres(state)

def _load_sqlite(document_id: str, db_path: str) -> Optional[ReportState]:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT * FROM reports WHERE document_id = ?", (document_id,)).fetchone()
    columns = [column[1] for column in conn.execute("PRAGMA table_info(reports)")]
    conn.close()
    if row is None:
        return None
    raw = dict(zip(columns, row))
    json_fields = {
        "execution_plan", "extracted_entities", "relations", "verifier_flags", "audit_trail",
        "ocr_result", "document_analysis", "medications", "clinical_context", "final_result",
        "agent_outputs", "execution_trace", "replans", "timeline", "fhir_draft",
    }
    for key in json_fields:
        if raw.get(key):
            raw[key] = json.loads(raw[key])
        elif key == "agent_outputs":
            raw[key] = {}
        elif key in {"final_result", "ocr_result", "document_analysis", "fhir_draft"}:
            raw[key] = None
        else:
            raw[key] = []
    return ReportState(**raw)

def _load_postgres(document_id: str) -> Optional[ReportState]:
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute("SELECT state FROM clinical.reports WHERE document_id = %s", (document_id,)).fetchone()
        if row:
            return ReportState.model_validate(row[0])

        legacy_table = conn.execute("SELECT to_regclass('public.reports')").fetchone()
        if not legacy_table or legacy_table[0] is None:
            return None
        legacy_row = conn.execute(
            "SELECT to_jsonb(report) FROM public.reports AS report WHERE document_id = %s",
            (document_id,),
        ).fetchone()

    if not legacy_row:
        return None
    legacy_state = legacy_row[0]
    for key in (
        "execution_plan", "extracted_entities", "relations", "verifier_flags",
        "audit_trail", "ocr_result", "document_analysis", "medications",
        "clinical_context", "final_result", "agent_outputs", "execution_trace",
        "replans", "timeline", "fhir_draft",
    ):
        value = legacy_state.get(key)
        if isinstance(value, str):
            legacy_state[key] = json.loads(value)
    return ReportState.model_validate(legacy_state)

def get_report(document_id: str, db_path: Optional[str] = None) -> Optional[ReportState]:
    """Retrieve the complete report state by document ID."""
    if db_path or not DATABASE_URL:
        return _load_sqlite(document_id, db_path or DB_PATH)
    return _load_postgres(document_id)

def save_upload(
    document_id: str, filename: str, content: bytes, content_type: Optional[str],
    db_path: Optional[str] = None,
) -> None:
    """Store the latest uploaded file for a document."""
    if db_path or not DATABASE_URL:
        with closing(sqlite3.connect(db_path or DB_PATH)) as conn, conn:
            conn.execute("DELETE FROM uploads WHERE document_id = ?", (document_id,))
            conn.execute(
                "INSERT INTO uploads (document_id, filename, content, content_type) VALUES (?, ?, ?, ?)",
                (document_id, filename, content, content_type),
            )
            conn.commit()
        return
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("DELETE FROM files.uploads WHERE document_id = %s", (document_id,))
        conn.execute(
            "INSERT INTO files.uploads (document_id, filename, content, content_type) VALUES (%s, %s, %s, %s)",
            (document_id, filename, content, content_type),
        )
        conn.commit()


def _page_window(page: int, page_size: int) -> tuple[int, int]:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    return page_size, (page - 1) * page_size


def _isoformat(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def list_reports(limit: int = 20, db_path: Optional[str] = None) -> list[dict[str, Any]]:
    """Return recent reports with the established summary metadata."""
    limit = min(100, max(1, limit))
    if db_path or not DATABASE_URL:
        with closing(sqlite3.connect(db_path or DB_PATH)) as conn, conn:
            rows = conn.execute(
                "SELECT document_id, summary, replan_count, created_at "
                "FROM reports ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    else:
        import psycopg

        with psycopg.connect(DATABASE_URL) as conn:
            rows = conn.execute(
                """
                SELECT r.document_id, o.summary, o.replan_count, r.created_at
                FROM clinical.reports AS r
                LEFT JOIN clinical.report_outputs AS o USING (document_id)
                ORDER BY r.updated_at DESC LIMIT %s
                """,
                (limit,),
            ).fetchall()
            legacy_exists = conn.execute(
                "SELECT to_regclass('public.reports')"
            ).fetchone()
            if legacy_exists and legacy_exists[0] is not None:
                legacy_rows = conn.execute(
                    """
                    SELECT document_id, summary, replan_count, created_at
                    FROM public.reports ORDER BY created_at DESC LIMIT %s
                    """,
                    (limit,),
                ).fetchall()
                known_ids = {row[0] for row in rows}
                rows.extend(row for row in legacy_rows if row[0] not in known_ids)
                rows.sort(key=lambda row: _isoformat(row[3]) or "", reverse=True)
                rows = rows[:limit]
    return [
        {
            "document_id": row[0],
            "summary": row[1],
            "replan_count": row[2],
            "created_at": _isoformat(row[3]),
        }
        for row in rows
    ]


def list_agent_outputs(
    document_id: str, page: int = 1, page_size: int = 20, agent_name: Optional[str] = None,
    db_path: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Return stored agent outputs for a report with pagination and optional filtering."""
    page_size, offset = _page_window(page, page_size)
    if db_path or not DATABASE_URL:
        with closing(sqlite3.connect(db_path or DB_PATH)) as conn, conn:
            row = conn.execute(
                "SELECT agent_outputs, created_at FROM reports WHERE document_id = ?",
                (document_id,),
            ).fetchone()
        if not row:
            return []
        outputs = json.loads(row[0]) if row[0] else {}
        entries = [
            {"id": index + 1, "agent_name": name, "payload": payload, "created_at": row[1]}
            for index, (name, payload) in reversed(list(enumerate(outputs.items())))
            if agent_name is None or name == agent_name
        ]
    else:
        import psycopg

        with psycopg.connect(DATABASE_URL) as conn:
            if agent_name:
                rows = conn.execute(
                    """
                    SELECT id, agent_name, payload, created_at FROM agents.agent_outputs
                    WHERE document_id = %s AND agent_name = %s
                    ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s
                    """,
                    (document_id, agent_name, page_size, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, agent_name, payload, created_at FROM agents.agent_outputs
                    WHERE document_id = %s ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s
                    """,
                    (document_id, page_size, offset),
                ).fetchall()
        entries = [
            {"id": row[0], "agent_name": row[1], "payload": row[2], "created_at": _isoformat(row[3])}
            for row in rows
        ]
    return entries[offset:offset + page_size] if db_path or not DATABASE_URL else entries


def list_audit_events(
    document_id: str, page: int = 1, page_size: int = 20, db_path: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Return a report's audit events in reverse chronological order."""
    page_size, offset = _page_window(page, page_size)
    if db_path or not DATABASE_URL:
        with closing(sqlite3.connect(db_path or DB_PATH)) as conn, conn:
            row = conn.execute(
                "SELECT audit_trail FROM reports WHERE document_id = ?", (document_id,)
            ).fetchone()
        if not row:
            return []
        events = json.loads(row[0]) if row[0] else []
        entries = [
            {
                "id": index + 1,
                "event": event,
                "created_at": event.get("timestamp"),
            }
            for index, event in reversed(list(enumerate(events)))
        ]
    else:
        import psycopg

        with psycopg.connect(DATABASE_URL) as conn:
            rows = conn.execute(
                """
                SELECT id, event, created_at FROM agents.audit_events
                WHERE document_id = %s ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s
                """,
                (document_id, page_size, offset),
            ).fetchall()
        entries = [
            {"id": row[0], "event": row[1], "created_at": _isoformat(row[2])}
            for row in rows
        ]
    return entries[offset:offset + page_size] if db_path or not DATABASE_URL else entries


def list_uploads(document_id: str, db_path: Optional[str] = None) -> list[dict[str, Any]]:
    """Return uploaded-file metadata without exposing stored contents."""
    if db_path or not DATABASE_URL:
        with closing(sqlite3.connect(db_path or DB_PATH)) as conn, conn:
            rows = conn.execute(
                "SELECT id, filename, content_type, created_at FROM uploads "
                "WHERE document_id = ? ORDER BY created_at DESC",
                (document_id,),
            ).fetchall()
    else:
        import psycopg

        with psycopg.connect(DATABASE_URL) as conn:
            rows = conn.execute(
                """
                SELECT id, filename, content_type, created_at FROM files.uploads
                WHERE document_id = %s ORDER BY created_at DESC
                """,
                (document_id,),
            ).fetchall()
    return [
        {
            "id": row[0],
            "filename": row[1],
            "content_type": row[2],
            "created_at": _isoformat(row[3]),
        }
        for row in rows
    ]


def get_upload_content(upload_id: int, db_path: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Retrieve stored bytes for an uploaded file."""
    if db_path or not DATABASE_URL:
        with closing(sqlite3.connect(db_path or DB_PATH)) as conn, conn:
            row = conn.execute(
                "SELECT filename, content, content_type FROM uploads WHERE id = ?",
                (upload_id,),
            ).fetchone()
    else:
        import psycopg

        with psycopg.connect(DATABASE_URL) as conn:
            row = conn.execute(
                "SELECT filename, content, content_type FROM files.uploads WHERE id = %s",
                (upload_id,),
            ).fetchone()
    if not row:
        return None
    return {"filename": row[0], "content": bytes(row[1]), "content_type": row[2]}
