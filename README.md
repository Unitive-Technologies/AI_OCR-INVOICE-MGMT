# 📑 DocAI: Intelligent Document Processing Engine

**DocAI** is an enterprise-grade document intelligence platform that automates the transition from unstructured documents (PDFs, Images) to structured, validated data. By combining **Google Cloud Document AI** for high-accuracy OCR with **Google Gemini** for semantic understanding, DocAI handles complex financial and administrative documents with ease.

---

## 🏗 Repository Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI Endpoint Routers (Upload, OCR, LLM, Cache)
│   │   ├── detectors/       # Classification logic (Gemini + Rules Engine)
│   │   ├── extractors/      # Specialized logic for Invoices, POs, Receipts, and IDs
│   │   ├── llm/             # Gemini Client integration and prompt engineering
│   │   ├── models/          # Pydantic Request/Response schemas
│   │   ├── nlp/             # Text cleaning and date/number normalization
│   │   ├── schemas/         # Data validation & Pydantic schemas
│   │   ├── services/        # Orchestration layer (OCR, File, Cache services)
│   │   ├── utils/           # Configuration, Logging, and Mime-type utilities
│   │   ├── models_db.py     # SQLAlchemy Database Models
│   │   └── db.py            # Database connection and session management
│   ├── cache/               # Persistent on-disk OCR and LLM result caching
│   ├── storage/             # Secure storage for uploaded raw documents
│   ├── main.py              # FastAPI application entrypoint
│   └── docker-compose.yml   # Infrastructure (PostgreSQL)
└── frontend/
    ├── src/
    │   ├── api/             # Frontend client for Backend & Firestore integration
    │   ├── components/      # UI: DragDrop, PDF Preview, Cache Analytics
    │   ├── utils/           # CSV generation and export tools
    │   └── App.jsx          # Main application dashboard logic

```

---

## 🚀 Key Technical Features

### 1. Intelligent Pipeline

DocAI doesn't just "read" text; it understands it. The workflow is modularized into specialized stages:

* **Hybrid Classification:** Uses a combination of a **Rules Engine** and **Gemini-based classification** to identify document types (Invoice, Receipt, PO, ID, etc.).
* **Specialized Extractors:** Dedicated logic for different document types ensures high-precision field mapping (e.g., `invoice_extractor.py` vs `po_extractor.py`).
* **NLP Normalization:** Post-extraction processing to standardize dates, currencies, and numeric formats for database consistency.

### 2. Performance & Cost Optimization

* **Dual-Layer Caching:**
* **OCR Cache:** Stores raw Document AI results to prevent redundant expensive OCR calls.
* **LLM Cache:** Stores Gemini responses (Classification/Extraction) to minimize token consumption and latency.


* **Cache Analytics:** Real-time visibility into cache hit/miss ratios and estimated cost savings.

### 3. Enterprise Data Handling

* **Postgres Persistence:** Full relational storage of document metadata and extracted line items.
* **Analytics Views:** Includes `db_views.sql` for advanced data reporting and document insights.
* **Firestore Integration:** Optional secondary persistence via `saveToFirestore.js` for real-time frontend syncing.

---

## 🛠 Tech Stack

| Layer | Technologies |
| --- | --- |
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy, Psycopg |
| **OCR & AI** | Google Cloud Document AI, Google Gemini (GenAI) |
| **Database** | PostgreSQL, Firestore (Optional) |
| **Frontend** | React, Vite, Axios, Tailwind/CSS |
| **DevOps** | Docker, Docker Compose |

---

## 🚦 Getting Started

### 1. Backend Setup

1. **Environment:** Create a `.env` in `backend/` based on your GCP credentials.
2. **Infrastructure:**
```bash
cd backend
docker-compose up -d  # Launches Postgres

```


3. **Install & Run:**
```bash
pip install -r requirements.txt
python main.py

```



### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev

```

## 🛡 API Endpoints

* `POST /api/upload`: Ingest documents to `storage/`.
* `POST /api/ocr/{file_id}`: Execute or retrieve cached OCR text.
* `POST /api/detect`: Classify document via LLM.
* `POST /api/extract/{file_id}`: Perform type-specific extraction (Invoice/Receipt/PO).
* `GET /api/cache/stats`: View performance metrics.

---

