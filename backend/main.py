from dotenv import load_dotenv
load_dotenv()   # <-- MUST BE FIRST

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.upload_router import router as upload_router
from app.api.detect_router import router as detect_router
from app.api.ocr_router import router as ocr_router
from app.api.extract_router import router as extract_router
from app.api.health_router import router as health_router
from app.api.cache_router import router as cache_router  # ✅ NEW

app = FastAPI(
    title="DocAI — Universal Document Ingestion",
    description="Enterprise Document Intelligence with Smart Caching",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(upload_router)
app.include_router(detect_router)
app.include_router(ocr_router)
app.include_router(extract_router)
app.include_router(health_router)
app.include_router(cache_router)  # ✅ NEW

@app.get("/")
def root():
    return {
        "status": "DocAI backend running",
        "version": "1.1.0",
        "features": ["Smart Caching", "Multi-format OCR", "LLM Extraction"]
    }