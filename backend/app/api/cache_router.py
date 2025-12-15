# backend/app/api/cache_router.py

from fastapi import APIRouter
from app.services.cache_service import cache_service

router = APIRouter(prefix="/api/cache", tags=["Cache Management"])


@router.get("/stats")
def get_cache_stats():
    """
    Get cache statistics.
    Returns total entries, size, and breakdown by operation.
    """
    stats = cache_service.stats()

    return {
        "status": "ok",
        "cache_stats": stats,
        "message": f"Cache contains {stats['total_entries']} entries"
    }


@router.delete("/clear")
def clear_cache(operation: str = None):
    """
    Clear cache entries.

    Query params:
        - operation (optional): Only clear specific operation type
          (classify, extract, summarize, embeddings)

    Examples:
        DELETE /api/cache/clear
        DELETE /api/cache/clear?operation=classify
    """

    cache_service.clear(operation)

    message = f"Cleared cache"
    if operation:
        message += f" for operation: {operation}"

    return {
        "status": "ok",
        "message": message,
        "new_stats": cache_service.stats()
    }


@router.post("/warm")
def warm_cache():
    """
    Pre-warm cache with common document types.
    Useful for testing or demo purposes.
    """

    sample_texts = {
        "invoice": "INVOICE\nInvoice No: INV-12345\nDate: 2024-01-15\nTotal: $1,234.56",
        "receipt": "RECEIPT\nStore: ABC Mart\nDate: 2024-01-15\nTotal: $45.99",
        "report": "QUARTERLY REPORT\nQ4 2024\nRevenue: $1.2M\nProfit: $450K"
    }

    from app.llm.gemini_client import gemini

    warmed = []
    for doc_type, text in sample_texts.items():
        result = gemini.classify_document(text)
        warmed.append({
            "type": doc_type,
            "classified_as": result.get("document_type"),
            "confidence": result.get("confidence")
        })

    return {
        "status": "ok",
        "message": "Cache warmed with sample documents",
        "warmed": warmed,
        "new_stats": cache_service.stats()
    }