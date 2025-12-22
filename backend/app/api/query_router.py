from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, Float, func
from typing import List, Optional
from datetime import datetime

from app.db import get_db
from app.models_db import Document, Invoice

router = APIRouter(prefix="/api", tags=["Query"])


@router.get("/documents")
def list_documents(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: Session = Depends(get_db),
):
    """List all uploaded documents with pagination."""
    documents = db.query(Document).offset(skip).limit(limit).all()
    total = db.query(Document).count()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "content_type": doc.content_type,
                "storage_path": doc.storage_path,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ],
    }


@router.get("/documents/{document_id}")
def get_document(
        document_id: str,
        db: Session = Depends(get_db),
):
    """Get a specific document by ID."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "storage_path": doc.storage_path,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.get("/invoices")
def list_invoices(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        vendor: Optional[str] = Query(None),
        invoice_number: Optional[str] = Query(None),
        currency: Optional[str] = Query(None),
        min_amount: Optional[float] = Query(None),
        max_amount: Optional[float] = Query(None),
        db: Session = Depends(get_db),
):
    """
    List invoices with optional filtering.
    Supports filtering by vendor, invoice_number, currency, and amount range.
    """
    query = db.query(Invoice)

    # Apply filters
    if vendor:
        query = query.filter(Invoice.vendor.ilike(f"%{vendor}%"))
    if invoice_number:
        query = query.filter(Invoice.invoice_number.ilike(f"%{invoice_number}%"))
    if currency:
        query = query.filter(Invoice.currency == currency.upper())
    if min_amount is not None:
        # Try to parse total_amount as float for comparison
        # Note: total_amount is stored as string, so we cast it
        query = query.filter(
            or_(
                Invoice.total_amount.is_(None),
                cast(Invoice.total_amount, Float) >= min_amount
            )
        )
    if max_amount is not None:
        query = query.filter(
            or_(
                Invoice.total_amount.is_(None),
                cast(Invoice.total_amount, Float) <= max_amount
            )
        )

    total = query.count()
    invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "invoices": [
            {
                "id": inv.id,
                "document_id": inv.document_id,
                "vendor": inv.vendor,
                "invoice_number": inv.invoice_number,
                "currency": inv.currency,
                "total_amount": inv.total_amount,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }
            for inv in invoices
        ],
    }


@router.get("/invoices/{invoice_id}")
def get_invoice(
        invoice_id: str,
        include_raw_metadata: bool = Query(False),
        db: Session = Depends(get_db),
):
    """Get a specific invoice by ID, optionally including full raw metadata."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    result = {
        "id": inv.id,
        "document_id": inv.document_id,
        "vendor": inv.vendor,
        "invoice_number": inv.invoice_number,
        "currency": inv.currency,
        "total_amount": inv.total_amount,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }

    if include_raw_metadata and inv.raw_metadata:
        import json
        try:
            result["raw_metadata"] = json.loads(inv.raw_metadata)
        except json.JSONDecodeError:
            result["raw_metadata"] = inv.raw_metadata

    return result


@router.get("/invoices/stats/summary")
def get_invoice_summary(
        db: Session = Depends(get_db),
):
    """Get summary statistics about invoices."""
    total_invoices = db.query(Invoice).count()

    # Count by currency
    currency_counts = (
        db.query(Invoice.currency, func.count(Invoice.id))
        .filter(Invoice.currency.isnot(None))
        .group_by(Invoice.currency)
        .all()
    )

    # Unique vendors
    unique_vendors = db.query(func.count(func.distinct(Invoice.vendor))).scalar()

    return {
        "total_invoices": total_invoices,
        "unique_vendors": unique_vendors or 0,
        "by_currency": {curr: count for curr, count in currency_counts},
    }

