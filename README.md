# EduTemplateFitAI — working prototype

Turns scattered departmental evidence (DOCX notes, Excel registers, PDFs, scanned
certificates) into a finished report that keeps the institution's original DOCX
template intact.

* **Frontend** — React 19 + Vite + Tailwind CSS v4 (`frontend/`)
* **Backend** — Python 3.13 + FastAPI (`backend/`)

## The pipeline

| Step | What happens | Module |
| --- | --- | --- |
| 1. Template audit | Headings/numbering/tables/placeholders detected, quality scored across structure, reproducibility, placeholder detection and mapping readiness. Sections get proposed schema categories you can override. | `backend/app/template_engine.py` |
| 2. Evidence ingest | DOCX, XLSX/CSV, PDF, TXT and images are parsed into **one canonical schema** (student achievement, FDP, guest lecture, workshop, publication, conference). Every record keeps its source file, locator, confidence and attached image. | `backend/app/extract.py`, `ingest.py` |
| 3. Validation | Confidence tiers (auto / review / manual), duplicate grouping, conflicting critical fields, evidence gaps, then human approval, inline editing, re-categorisation and bulk approval. | `backend/app/validation.py` |
| 4. Generation | A **copy of the uploaded template** is edited with python-docx: placeholders resolved, section text and tables filled, traceability annexure appended. A PDF companion is rendered with reportlab. | `backend/app/template_engine.py` |

Projects are persisted as JSON under `backend/data/projects/<id>/project.json`
along with their template, sources, media and generated files. Swapping that for
PostgreSQL only means replacing `backend/app/store.py`.

## Run it

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows; use source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` to `127.0.0.1:8000`.

Click **Load the demo dataset** for a complete run without preparing files: the
seeder builds a real template plus DOCX, XLSX, PDF and PNG evidence containing a
duplicate record and a conflicting value.

### Smoke test

With the backend running:

```bash
cd backend
./.venv/Scripts/python smoke_test.py
```

It walks demo → analysis → confirm → manual approval → bulk approval →
generation and asserts a DOCX and PDF were produced.

## Notes and limits

* Templates must be `.docx`; rendering preserves styles, tables, headers and
  footers because the template itself is edited rather than rebuilt.
* Extraction is rules-based (regex, header mapping, heuristics) — this is a
  prototype, not an OCR/LLM service. Unreadable scans surface as `no-data`
  sources instead of silently inventing records.
* Active PDF/attachment extraction of scanned images is out of scope; images are
  stored as evidence and linked to records.
* Everything runs locally; there is no auth or multi-tenant isolation yet.
