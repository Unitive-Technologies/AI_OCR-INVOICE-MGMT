# DocAI

End‑to‑end document intelligence demo: upload invoices (and other docs), run OCR via Google Document AI, classify & extract structured fields with Gemini, and visualize results in a React UI with smart caching and a Postgres backend.

---

## Features

- Upload PDFs / images via a FastAPI backend
- OCR using Google Cloud Document AI
- Document type detection (invoice / receipt / PO / etc.) via Gemini
- Structured data extraction & optional summarization + embeddings via Gemini
- Smart on‑disk caching for Gemini calls (classify / extract / summarize / embeddings)
- React + Vite frontend:
  - Drag & drop upload
  - PDF / image preview
  - Summary card & key invoice fields
  - Line‑item table
  - Download JSON / CSV or copy JSON to clipboard
  - Live cache statistics and cache‑hit indicators
- Postgres persistence of:
  - Documents, OCR text, classifications, processing history
  - Invoices / receipts / purchase orders / generic extraction results
- Query APIs to list documents & invoices with filters
- Health endpoints and DB health check

---

## Tech Stack

**Backend**

- Python / FastAPI (`backend/main.py`)
- SQLAlchemy ORM + Postgres (`backend/app/db.py`, `backend/app/models_db.py`)
- Google Cloud Document AI (`google-cloud-documentai`) for OCR
- Google Gemini (`google-genai`) for classification, extraction, summaries, embeddings
- Smart file‑based cache (`backend/app/services/cache_service.py`)
- Docker Compose for Postgres (`backend/docker-compose.yml`)

**Frontend**

- React + Vite (`frontend/`)
- Axios for HTTP calls
- Custom UI with PDF/image preview and cache metrics
- Optional Firebase initialization via CDN (`frontend/index.html`)

---

## Repository Structure

High‑level layout:

- `backend/`
  - `main.py` – FastAPI app entrypoint
  - `docker-compose.yml` – Postgres service
  - `requirements.txt` – core Python deps (SQLAlchemy, psycopg); additional deps described below
  - `app/`
    - `api/` – FastAPI routers:
      - `upload_router.py` – `/api/upload` (file upload)
      - `ocr_router.py` – `/api/ocr/{file_id}` (Document AI OCR)
      - `detect_router.py` – `/api/detect` (Gemini classification)
      - `extract_router.py` – `/api/extract/{file_id}` (Gemini extraction, summary, embeddings)
      - `cache_router.py` – `/api/cache/*` (cache stats / clear / warm)
      - `health_router.py` – `/health`, `/health/db`
      - `query_router.py` – list/query documents & invoices
    - `services/` – OCR, document, NLP, cache, file services
    - `llm/` – Gemini client + prompts
    - `models_db.py` – SQLAlchemy models for documents, invoices, receipts, POs, etc.
    - `db.py` – SQLAlchemy engine/session + `get_db` dependency
    - `db_views.sql`, `create_views.py` – convenience SQL views for analytics
    - `cache/` – Gemini cache files (created at runtime)
    - `uploads/` – stored uploaded files (created at runtime)
- `frontend/`
  - `src/App.jsx` – main UI
  - `src/api/invoice.js` – API client wrapper
  - `src/components/` – `DragDrop`, `PdfPreview`, `CacheStats`
  - `src/index.css` – styling
  - `vite.config.js`, `eslint.config.js`, `index.html`

---

## Prerequisites

- **Python** 3.10+ (recommended)
- **Node.js** 18+ and npm
- **Docker** + Docker Compose (for Postgres)
- **Google Cloud**
  - Project with **Document AI** enabled
  - Project with **Gemini** (Google Generative AI) access
  - Service account JSON key for Document AI

---

## Configuration

Create a `.env` file in `backend/` (next to `main.py`) with:

```bash
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=your-document-ai-location          # e.g. us, us-central1
GCP_PROCESSOR_ID=your-document-ai-processor-id  # the Document AI processor
GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json # absolute or relative path

GEMINI_API_KEY=your-gemini-api-key

# Optional: override DB connection (otherwise defaults to local Postgres)
DATABASE_URL=postgresql+psycopg://docai:docai@localhost:5432/docai
