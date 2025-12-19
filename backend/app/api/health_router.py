from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok", "message": "DocAI is alive"}


@router.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    """
    Database health check.
    Returns 200 if a simple SELECT 1 succeeds against Postgres.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database connected"}
    except Exception:
        # Surface a proper HTTP error instead of hanging the UI.
        raise HTTPException(
            status_code=503,
            detail="Database not reachable; check DATABASE_URL and Postgres container.",
        )
