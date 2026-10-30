# Clinical Document Understanding & Decision Support Platform

An agentic clinical document intelligence platform designed to ingest, transcribe, analyze, and verify medical records, doctor prescriptions, and clinical narratives.

Built with an adaptive multi-agent LangGraph architecture, multimodal vision OCR, medical ontology grounding, and clinical safety verification.

The supported deployment path is Docker Compose: a FastAPI backend and a React/Vite
frontend served by Nginx. The backend uses Neon/PostgreSQL when `DATABASE_URL` is set
and a persistent SQLite fallback for local development.

---

## Key Features

* **Dual-Mode Clinical Intake**:
  * **Direct Text Entry**: Ingest arbitrary clinical notes, EHR extracts, discharge summaries, and consultation orders.
  * **Scanned & Image Document OCR**: Upload handwritten doctor prescriptions, clinical scans, and multi-page PDFs (PNG, JPG, JPEG, PDF).
* **Multimodal Vision OCR Engine**:
  * Powered by Gemini Multimodal Vision (`gemini-3.1-flash-lite`, `gemini-2.5-flash`) for doctor handwriting, medication dosage orders, and clinical layouts.
  * Native Windows OCR (`winocr`) integration for word-level bounding box spatial provenance.
  * Cross-platform fallback support for Tesseract OCR.
* **Specialist Multi-Agent Pipeline**:
  * **Document Agent**: Characterizes document types, determines machine-readability, and gates OCR execution.
  * **NER Agent**: Extracts clinical entities (`MEDICATION`, `DIAGNOSIS`, `SYMPTOM`, `LAB_RESULT`, `PROCEDURE`, `ANATOMY`).
  * **Medication Agent**: Parses structured prescription attributes (`drug`, `dose`, `route`, `frequency`, `duration`).
  * **Relation Agent**: Identifies semantic clinical relationships (`TREATS`, `CAUSES`, `INDICATES`, `TEMPORAL_BEFORE`, `TEMPORAL_AFTER`).
  * **Timeline Agent**: Normalizes temporal expressions and maps progression of symptoms and interventions.
  * **Grounding Agent**: Maps extracted terms to standard medical ontologies (RxNorm, ICD-10, SNOMED-CT).
  * **Verification / Safety Agent**: Flags potential drug interactions, dosage contradictions, and safety hazards with optional replanning.
  * **Summary Agent**: Generates structured clinical summaries and decision support overviews.
* **Interactive Web Dashboard**:
  * The primary React single-page application in `frontend/` is served at `http://localhost:5173/` locally or through the frontend container.
  * The legacy dashboard remains available from the FastAPI service at `http://localhost:8000/`.
  * Live multi-agent execution trace inspection, entity cards, relationship maps, and audit trail.

## Models And External Services

Models are loaded lazily on first use and cached in the Docker `hf_cache` volume. The
pipeline continues with deterministic fallbacks when optional model or API access is
unavailable.

| Capability | Model or service | Fallback |
| --- | --- | --- |
| Custom clinical NER | `models/custom_medical_ner` | SciSpaCy, regex, and deterministic extraction |
| SciSpaCy NER | `en_core_sci_sm` | Regex and deterministic extraction |
| Hugging Face NER | `d4data/biomedical-ner-all` | Audit event plus local fallback |
| Hugging Face relation extraction | `wesin/pubmedbert-relation-extraction` | Gemini or deterministic relations |
| Hugging Face embeddings | `NeuML/biomedbert-base-embeddings` | Local ontology index fallback |
| LLM and vision OCR | Gemini `gemini-3.1-flash-lite`, `gemini-2.5-flash`, `gemini-2.0-flash` | Local extraction and Tesseract |
| OCR | Windows `winocr` or Tesseract | Tesseract is installed in the backend image |

Hugging Face models are downloaded on demand rather than during image build. The first
request that uses a model may take longer and requires outbound network access. Set
`HF_TOKEN` for higher Hugging Face Hub limits when required.

---

## System Architecture

```text
 Clinical Document / Scanned Prescription / Note
                     │
                     ▼
          [Document Intake Agent]
          ├─ Native PDF / Text ──► [Direct Text Gating]
          └─ Scanned Image / PDF ─► [Multimodal Vision & OCR Agent]
                                        │ (Word Bounding Boxes + Text)
                                        ▼
                            [PII Masking & Normalization]
                                        │
                                        ▼
                         [Multi-Agent Orchestrator Graph]
               ┌────────────────────────┼────────────────────────┐
               ▼                        ▼                        ▼
       [Clinical NER]           [Medication Parser]       [Relation Extraction]
               │                        │                        │
               ▼                        ▼                        ▼
     [Ontology Grounding]       [Temporal Timeline]      [Safety Verifier / Critic]
     (RxNorm / ICD-10 / SNOMED)                                  │
               │                                                 ▼
               └────────────────► [Summary Agent] ◄──────────────┘
                                        │
                                        ▼
                     [Postgres / SQLite Report Store]
                                        │
                                        ▼
                  [React Clinical Dashboard (Port 5173)]
```

---

## Project Structure

```text
├── agents/                     # Specialist agent implementations
│   ├── context.py              # Clinical context specialist
│   ├── document.py             # Document characterization and format gating
│   ├── finalizer.py            # Result aggregation and validation
│   ├── grounding.py           # Medical ontology mapping (RxNorm, ICD-10)
│   ├── medication.py          # Structured medication and dosage parser
│   ├── ner.py                  # Clinical Named Entity Recognition agent
│   ├── ocr.py                  # Multimodal Vision & Windows OCR gateway
│   ├── orchestrator.py         # LangGraph workflow and dynamic routing
│   ├── relation.py             # Clinical semantic relation detector
│   ├── summary.py              # Clinical summary generation
│   ├── timeline.py             # Temporal event timeline construction
│   └── verifier.py             # Contraindication and dosage verifier
├── api/                        # FastAPI service layer
│   ├── dashboard.py            # Legacy API-served dashboard
│   └── main.py                 # API router, middleware, and upload endpoints
├── data/                       # Local database & ontology indices
│   ├── db.py                   # Postgres/SQLite report, input, output, and audit storage
│   ├── ontology_seed.json      # Curated medical ontology seed dictionary
│   └── reports.db              # SQLite database file
├── dataset/                    # Clinical benchmarks and evaluation datasets
├── frontend/                   # Standalone Vite + React application
├── models/                     # Custom trained clinical NER models
├── schemas/                    # Core Pydantic schemas and state definitions
│   └── core.py                 # ReportState, ExtractedEntity, OCRResult, etc.
├── scripts/                    # Model training and optimization utilities
│   ├── bulk_optimize.py        # Batch optimization script
│   ├── train_and_evaluate.py   # SpaCy NER training and evaluation pipeline
│   └── train_ner.py            # NER model trainer
├── tests/                      # Automated test suite (pytest)
│   ├── test_api.py             # FastAPI endpoint tests
│   ├── test_db.py              # Database persistence tests
│   ├── test_graph.py           # Multi-agent graph execution tests
│   ├── test_ocr.py             # OCR ingestion and error handling tests
│   ├── test_relation.py        # Relation extraction tests
│   ├── test_schemas.py         # Schema validation tests
│   ├── test_summary.py         # Summary generation tests
│   └── test_verifier.py        # Safety verification tests
├── tools/                      # Core utility modules
│   ├── data_loader.py          # Clinical dataset ingestion helpers
│   ├── fhir_validator.py       # FHIR standard schema validation
│   ├── llm_client.py           # Gemini Multimodal Vision & LLM client
│   ├── ontology_index.py       # Fast vector/lexical ontology index
│   └── preprocessing.py        # Clinical text normalizer and PHI masker
├── Dockerfile                  # Container definition for backend service
├── docker-compose.yml          # Container orchestration configuration
├── pytest.ini                  # Pytest runner configuration
└── requirements.txt            # Python dependencies
```

---

## Quick Start

### 1. Prerequisites
* Docker Desktop with Compose v2 for the supported deployment path
* Python 3.11+ and Node.js 20+ for local development
* Outbound network access on the first Hugging Face model request

### 2. Configuration

Copy the safe configuration template:

```bash
copy .env.example .env              # Windows PowerShell
# cp .env.example .env              # Linux/macOS
```

Set `DATABASE_URL` in `.env` to the Neon/PostgreSQL connection string when remote
persistence is required. Do not commit `.env` or credentials. Leave it empty to use
the persistent local SQLite fallback.

Important variables:

* `DATABASE_URL`: creates and uses the `clinical`, `agents`, and `files` schemas.
* `GEMINI_API_KEY`: optional Gemini extraction and multimodal OCR.
* `HF_TOKEN`: optional Hugging Face Hub authentication.
* `MODEL_DEVICE`: defaults to `cpu`; use `cuda` only with a compatible GPU runtime.
* `VITE_BACKEND_URL`: defaults to `/api`; Nginx proxies it to the backend container.

### 3. Local Installation

Clone the repository and set up a virtual environment:

```bash
git clone <repo-url> "internship"
cd "internship"

python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

## Running The Application

### Option A: Local Run Without Docker (Recommended For Development)

Use three terminals from the repository root.

Terminal 1, install the Python dependencies and start the API:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Terminal 2, install frontend dependencies and start Vite:

```powershell
cd frontend
npm ci
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` to the
local backend at `http://localhost:8000`. Verify the API before using the dashboard:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

The backend loads `.env` automatically, so `DATABASE_URL` is used for persistence.
Without it, the complete report state is stored in the local SQLite fallback.

### Option B: Docker Compose

Build and start both services:

```bash
docker compose up --build
```

Open the dashboard at [http://localhost:5173](http://localhost:5173), API docs at
[http://localhost:8000/docs](http://localhost:8000/docs), and the health probe at
[http://localhost:8000/health](http://localhost:8000/health).

The frontend waits for the backend health check. The first request may download Hugging
Face models; subsequent runs reuse the named `hf_cache` volume.

Stop the stack with:

```bash
docker compose down
```

### Persistence Layout

With PostgreSQL, the backend stores:

* `clinical.reports`: complete serialized `ReportState` snapshots.
* `clinical.report_inputs`: original text, source text, file metadata, OCR, and document analysis.
* `clinical.report_outputs`: summaries, final results, plans, traces, and replans.
* `agents.agent_outputs`: one JSON payload per agent output.
* `agents.audit_events`: timestamped agent actions and audit details.
* `files.uploads`: uploaded source bytes and metadata.

Writes are upserted by `document_id`, making retries safe. SQLite uses the same complete
state shape for local fallback and tests.

---

## API Documentation

### Legacy Dashboard
* **Endpoint**: `GET /`
* **Response**: The original dashboard served by FastAPI; the React application remains the primary UI.

### Ingest Plain Clinical Text
* **Endpoint**: `POST /process`
* **Content-Type**: `application/json`
* **Request**:
  ```json
  {
    "document_id": "DOC-1001",
    "text": "Patient Robert Davis (Age: 58). Diagnosed with Type 2 Diabetes Mellitus and Essential Hypertension. Prescribed Metformin 500 mg oral twice daily and Lisinopril 10 mg oral once daily."
  }
  ```
* **Response**: `ReportState` JSON containing extracted entities, medications, relationships, safety flags, and clinical summary.

### Upload Clinical Document / Prescription (OCR)
* **Endpoint**: `POST /process/upload`
* **Content-Type**: `multipart/form-data`
* **Parameters**:
  * `document_id`: Unique identifier string.
  * `file`: File upload (`.pdf`, `.png`, `.jpg`, `.jpeg`).
* **Response**: `ReportState` JSON with `ocr_result` (overall confidence, bounding box coordinates, transcribed clinical text) and full downstream clinical extraction.

### Retrieve Stored Report
* **Endpoint**: `GET /reports/{document_id}`
* **Response**: Persisted report state, execution trace, and audit log.

### List Reports
* **Endpoint**: `GET /reports?limit=20`
* **Response**: Recent report IDs with summary, replan count, and creation time.

### Inspect Agent Outputs and Audit Events
* **Endpoints**: `GET /agents/outputs?document_id=DOC-1001` and `GET /agents/audit?document_id=DOC-1001`
* **Parameters**: Both endpoints support `page` and `page_size`; agent outputs also support `agent_name`.

### List or Download Uploaded Files
* **Endpoints**: `GET /files?document_id=DOC-1001` and `GET /files/{upload_id}`
* **Response**: File metadata or the stored source document.

### Re-run a Report
* **Endpoint**: `POST /process/rerun`
* **Request**: `{"document_id": "DOC-1001"}`
* **Response**: HTTP 202 after the stored report has been reprocessed.

### Health Check
* **Endpoint**: `GET /health`
* **Response**: `{"status": "ok"}`

---

## Running Tests

Run the test suite using pytest:

```bash
python -m pytest
```

To run a specific module:

```bash
python -m pytest tests/test_ocr.py -v
python -m pytest tests/test_api.py -v
```

Validate the container images before pushing:

```bash
docker compose build
docker compose up -d
curl http://localhost:8000/health
docker compose down
```

## Benchmarking

The opt-in, offline-first benchmark framework is documented in
[benchmarks/README.md](./benchmarks/README.md). Run all suites without paid model
calls using `python -m benchmarks.run_benchmarks --all --mode mock`; attach
human-annotated datasets with `--dataset PATH` to calculate accuracy metrics.

If an old local checkout reports a missing SQLite column after upgrading, run the backend
once with the updated migration or remove only the ignored `data/reports.db` file. A
configured PostgreSQL database is migrated idempotently on backend startup.

---

## License

This project is developed for clinical document intelligence and healthcare informatics research.
