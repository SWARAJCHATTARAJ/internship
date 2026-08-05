# Multi-Agent Clinical Report Understanding System

## Overview
This project is a clinical report understanding platform built as a multi-agent pipeline. Raw clinical text is routed through an orchestrator that selects the execution path based on report complexity. The pipeline can invoke:
- NER extraction
- Relation detection
- Timeline/event extraction
- Medical grounding
- Summarization
- Verification and re-planning

The system exposes a FastAPI backend and a Vite + React frontend. A SpaCy training pipeline generates a custom clinical NER model from the dataset.

## Architecture
- **Backend**: FastAPI API in `api/main.py`
- **Agent orchestration**: `agents/orchestrator.py` using LangGraph-style workflow
- **NER training**: `scripts/train_and_evaluate.py` with SpaCy weakly supervised labeling
- **Frontend**: Vite + React app in `frontend/`
- **Persistence**: local JSON storage via `data/db.py`
- **Schema validation**: Pydantic models in `schemas/core.py`
- **Containerization**: `Dockerfile` + `docker-compose.yml`

## What this project does
1. Accepts clinical report text via `/process`
2. Normalizes and masks protected information
3. Constructs a `ReportState` object
4. Routes the report through an orchestrator graph
5. Executes one or more specialist agents
6. Saves the processed report for later retrieval

## Key files and folders
- `Dockerfile` — backend image build and runtime entrypoint
- `docker-compose.yml` — orchestrates backend and frontend services
- `requirements.txt` — Python dependencies for backend and training
- `api/main.py` — FastAPI server and processing endpoints
- `agents/orchestrator.py` — route decision logic and workflow graph
- `agents/ner.py` — NER extraction agent
- `agents/relation.py` — relation extraction agent
- `agents/timeline.py` — timeline/event extraction agent
- `agents/grounding.py` — medical grounding agent
- `agents/summary.py` — summary generation agent
- `agents/verifier.py` — verification and replan logic
- `schemas/core.py` — Pydantic data models for report state
- `scripts/train_and_evaluate.py` — training and evaluation script for the custom SpaCy model
- `dataset/` — training and evaluation data sources
- `frontend/` — Vite + React user interface
- `data/db.py` — simple local persistence layer for processed reports
- `tools/` — preprocessing, data loading, ontology utilities

## Algorithm and workflow
### Orchestrator
The orchestrator inspects the input report and decides the execution plan based on:
- report length
- presence of clinical keywords such as `medication`, `lab`, `procedure`, `diagnos`, `history`

For short/simple clinical reports, it may route to NER only. For longer or more complex reports, it routes to a specialist path including relation, timeline, grounding, summary, and verifier.

### Agent pipeline
- **NER Agent**: extracts clinical entities, including medications, diagnoses, and symptoms
- **Relation Agent**: identifies causal, treatment, or temporal relationships between extracted entities
- **Timeline Agent**: converts events into a normalized timeline representation
- **Grounding Agent**: maps entities to medical ontologies such as SNOMED or RxNorm
- **Summary Agent**: generates a natural language summary of the clinical case
- **Verifier Agent**: checks consistency and flags contradictions, with optional replanning

### Training and evaluation
The training pipeline in `scripts/train_and_evaluate.py`:
- loads clinical text reports from `dataset/`
- applies weak supervision using SpaCy `PhraseMatcher`
- labels medications, diagnoses, and symptoms automatically
- trains a SpaCy NER model with custom labels
- evaluates precision / recall / F1 on a held-out set
- saves the model to `models/custom_medical_ner`
- optionally runs the orchestrator over a subset of examples and exports metrics to `model_evaluation_metrics.json`

## Setup guide
### 1. Clone repository
```bash
git clone <repo-url> "Internship"
cd "Internship"
```

### 2. Create a Python virtual environment
```bash
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Install Python dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 4. Install frontend dependencies
```bash
cd frontend
npm install
cd ..
```

### 5. Optional: build the frontend for production
```bash
cd frontend
npm run build
cd ..
```

## Running the system
### Option A: Run with Docker Compose
This is the recommended way to start the full stack.
```bash
docker compose up --build
```
If you want detached mode:
```bash
docker compose up -d --build
```

### Option B: Run backend only
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Option C: Run frontend only
```bash
cd frontend
npm run dev
```
The frontend expects the backend at `http://localhost:8000` by default, or it can use `VITE_BACKEND_URL`.

## API endpoints
- `POST /process`
  - payload: `{ "document_id": "<id>", "text": "<clinical report text>" }`
  - response: `ReportState`
- `GET /reports/{document_id}`
  - returns the stored processed report

## Useful commands
### Rebuild backend image after dependency changes
```bash
docker compose build --no-cache backend
```

### Check running containers
```bash
docker compose ps
```

### Stop and remove containers
```bash
docker compose down
```

### Troubleshoot port conflicts
If port `8000` is already occupied, stop the conflicting process or change the host port mapping in `docker-compose.yml`.

## Expected ports
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## Notes
- The backend loads and invokes the multi-agent graph in `api/main.py`.
- The schema definitions in `schemas/core.py` define entities, relations, timeline events, verifier flags, and audit trail recordings.
- The frontend application in `frontend/src/App.jsx` sends processing requests to the backend and renders the returned agent plan and outputs.
- The training script uses SpaCy weak supervision rather than manual annotation, which speeds up model development for medical NER.

## Project status
This repository includes the core multi-agent orchestration pipeline, a backend API, a React frontend demo, model training scripts, and Docker orchestration for local end-to-end execution.
