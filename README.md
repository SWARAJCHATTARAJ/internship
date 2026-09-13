# Clinical Document Understanding & Decision Support Platform

An agentic clinical document intelligence platform designed to ingest, transcribe, analyze, and verify medical records, doctor prescriptions, and clinical narratives.

Built with an adaptive multi-agent LangGraph architecture, multimodal vision OCR, medical ontology grounding, and clinical safety verification.

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
  * Fully integrated single-page application served directly by FastAPI at `http://localhost:8000/`.
  * Live multi-agent execution trace inspection, entity cards, relationship maps, and audit trail.
  * Optional standalone Vite + React client in `frontend/`.

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
                         [SQLite Audit & Report Store]
                                        │
                                        ▼
                  [Interactive Clinical Dashboard (Port 8000)]
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
│   ├── dashboard.py            # Integrated single-page clinical dashboard UI
│   └── main.py                 # API router, middleware, and upload endpoints
├── data/                       # Local database & ontology indices
│   ├── db.py                   # SQLite storage for reports and audit events
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
* Python 3.10+ (tested on Python 3.11 - 3.14)
* *(Optional)* Docker and Docker Desktop

### 2. Installation

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

### 3. Environment Configuration

Create a `.env` file in the root directory:

```env
# Optional: Gemini API key enables multimodal vision OCR for handwritten prescriptions
GEMINI_API_KEY=your_gemini_api_key_here

# Allowed origins for CORS (default: http://localhost:5173)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

> **Note:** If no `GEMINI_API_KEY` is provided, the platform gracefully uses local Windows OCR (`winocr`) and Tesseract OCR.

---

## Running the Application

### Option A: Local Python Server (Fastest)

Start the Uvicorn ASGI server:

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Once running:
* **Clinical Dashboard**: Open [http://localhost:8000/](http://localhost:8000/) in any web browser.
* **Interactive Swagger Docs**: Access [http://localhost:8000/docs](http://localhost:8000/docs).
* **Health Probe**: [http://localhost:8000/health](http://localhost:8000/health).

### Option B: Docker Compose

To start the containerized stack:

```bash
docker compose up --build
```

* **Frontend UI**: [http://localhost:5173](http://localhost:5173)
* **Backend API**: [http://localhost:8000](http://localhost:8000)

---

## API Documentation

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

---

## License

This project is developed for clinical document intelligence and healthcare informatics research.
