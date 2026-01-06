from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
import json
import logging

from app.db import get_db
from app.models_db import Session as SessionModel, Document, Invoice, Receipt, PurchaseOrder, ExtractionResult
from app.services.document_service import document_service
from app.services.ocr_service import ocr_service
from app.services.vector_service import vector_service
from app.llm.gemini_client import GeminiClient

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])
gemini = GeminiClient()
logger = logging.getLogger(__name__)


@router.post("")
def create_session(
    name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Create a new session for grouping multiple documents."""
    session_id = str(uuid.uuid4())
    session = SessionModel(
        id=session_id,
        name=name,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session_id,
        "name": name,
        "created_at": session.created_at.isoformat(),
    }


@router.get("/{session_id}")
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Get session details with document count."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    doc_count = db.query(Document).filter(Document.session_id == session_id).count()

    return {
        "session_id": session_id,
        "name": session.name,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "document_count": doc_count,
    }


@router.post("/{session_id}/upload")
async def upload_multiple_files(
    session_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload multiple files to a session."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    uploaded_files = []
    for file in files:
        file_bytes = await file.read()
        file_id = document_service.save_file(
            file_bytes,
            filename=file.filename,
            db=db,
        )

        # Update document with session_id
        doc = db.query(Document).filter(Document.id == file_id).first()
        if doc:
            doc.session_id = session_id
            db.commit()

        uploaded_files.append({
            "file_id": file_id,
            "filename": file.filename,
        })

    # Update session timestamp
    session.updated_at = datetime.utcnow()
    db.commit()

    return {
        "session_id": session_id,
        "uploaded_files": uploaded_files,
        "total_files": len(uploaded_files),
    }


@router.post("/{session_id}/process-all")
async def process_all_documents(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Process all documents in a session (OCR, detect, extract, vectorize)."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    documents = db.query(Document).filter(Document.session_id == session_id).all()
    logger.info("Processing %s documents for session %s", len(documents), session_id)

    if not documents:
        raise HTTPException(status_code=400, detail="No documents in session")

    results = []
    for idx, doc in enumerate(documents, 1):
        logger.info("Processing document %s/%s: %s (ID: %s)", idx, len(documents), doc.filename, doc.id)
        try:
            # OCR
            raw_bytes = document_service.read_file_bytes(doc.id, db=db)
            text = ocr_service.extract_text(raw_bytes)
            document_service.save_text(doc.id, text, db=db)

            # Vectorize OCR text
            vector_service.upsert_document(
                session_id=session_id,
                document_id=doc.id,
                text=text,
                metadata={"filename": doc.filename},
            )

            # Detect & Extract
            detected = gemini.classify_document(text)
            detected_type = detected.get("document_type")
            extraction = gemini.extract_structured(text, detected_type)

            if isinstance(extraction, dict):
                extraction_json = json.dumps(extraction)

                if detected_type == "invoice":
                    invoice = Invoice(
                        id=doc.id,
                        document_id=doc.id,
                        vendor=extraction.get("vendor_name") or extraction.get("supplier_name") or extraction.get("vendor"),
                        invoice_number=extraction.get("invoice_number"),
                        currency=extraction.get("currency"),
                        total_amount=str(extraction.get("total_amount")) if extraction.get("total_amount") else None,
                        raw_metadata=extraction_json,
                    )
                    db.merge(invoice)
                elif detected_type == "receipt":
                    receipt = Receipt(
                        id=doc.id,
                        document_id=doc.id,
                        merchant=extraction.get("merchant_name") or extraction.get("store_name") or extraction.get("merchant"),
                        receipt_number=extraction.get("receipt_number") or extraction.get("transaction_id"),
                        transaction_date=extraction.get("transaction_date") or extraction.get("date"),
                        currency=extraction.get("currency"),
                        total_amount=str(extraction.get("total_amount")) if extraction.get("total_amount") else None,
                        payment_method=extraction.get("payment_method"),
                        raw_metadata=extraction_json,
                    )
                    db.merge(receipt)
                elif detected_type in ["purchase_order", "po"]:
                    po = PurchaseOrder(
                        id=doc.id,
                        document_id=doc.id,
                        po_number=extraction.get("po_number") or extraction.get("purchase_order_number"),
                        vendor=extraction.get("vendor_name") or extraction.get("supplier_name") or extraction.get("vendor"),
                        buyer=extraction.get("buyer_name") or extraction.get("customer_name"),
                        order_date=extraction.get("order_date") or extraction.get("po_date"),
                        currency=extraction.get("currency"),
                        total_amount=str(extraction.get("total_amount")) if extraction.get("total_amount") else None,
                        raw_metadata=extraction_json,
                    )
                    db.merge(po)
                else:
                    extract_result = ExtractionResult(
                        id=doc.id,
                        document_id=doc.id,
                        document_type=detected_type,
                        raw_metadata=extraction_json,
                    )
                    db.merge(extract_result)

                db.commit()

            results.append({
                "file_id": doc.id,
                "filename": doc.filename,
                "status": "success",
                "detected_type": detected.get("document_type"),
            })
        except Exception as e:
            db.rollback()
            logger.error("Error processing %s: %s", doc.filename, str(e), exc_info=True)
            results.append({
                "file_id": doc.id,
                "filename": doc.filename,
                "status": "error",
                "error": str(e),
            })

    return {
        "session_id": session_id,
        "processed": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "error"]),
        "results": results,
    }


def _field_type_from_query(query: str) -> str:
    q = (query or "").lower()
    if any(word in q for word in ["date", "when", "invoice date", "transaction date"]):
        return "date"
    if any(word in q for word in ["vendor", "supplier", "merchant"]):
        return "vendor"
    if any(word in q for word in ["invoice number", "invoice no", "inv number"]):
        return "invoice_number"
    if any(word in q for word in ["receipt number", "receipt no"]):
        return "receipt_number"
    if any(word in q for word in ["po number", "purchase order", "po no"]):
        return "po_number"
    if any(word in q for word in ["amount", "total", "price", "cost"]):
        return "amount"
    if any(word in q for word in ["currency", "money"]):
        return "currency"
    return "general"


@router.get("/{session_id}/search")
def search_session(
    session_id: str,
    query: str = Query(..., description="Search keywords"),
    db: Session = Depends(get_db),
):
    """
    Vector search (Chroma) across OCR text for all documents in a session.
    If the query hints at a specific field (date/vendor/amount/etc), only that field is returned.
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Vector search
    search_res = vector_service.search(session_id, query, top_k=10)
    ids_nested = search_res.get("ids", [])
    distances_nested = search_res.get("distances", [])
    if not ids_nested or not ids_nested[0]:
        return {
            "session_id": session_id,
            "query": query,
            "field_type": _field_type_from_query(query),
            "total_results": 0,
            "results": [],
            "table_data": [],
        }

    doc_ids = ids_nested[0]
    distances = distances_nested[0] if distances_nested else [None] * len(doc_ids)
    doc_map = {
        d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()
    }

    field_type = _field_type_from_query(query)
    results = []
    table_data = []

    for doc_id, dist in zip(doc_ids, distances):
        doc = doc_map.get(doc_id)
        if not doc:
            continue

        # Fetch related records
        inv = db.query(Invoice).filter(Invoice.document_id == doc_id).first()
        rec = db.query(Receipt).filter(Receipt.document_id == doc_id).first()
        po = db.query(PurchaseOrder).filter(PurchaseOrder.document_id == doc_id).first()

        def add_result(field_label: str, value: Optional[str], extra: Optional[dict] = None):
            if value:
                results.append({
                    "document_id": doc_id,
                    "document_type": (inv and "invoice") or (rec and "receipt") or (po and "purchase_order") or "unknown",
                    "filename": doc.filename,
                    field_label: value,
                    "score": dist,
                    **(extra or {}),
                })
                table_data.append({
                    field_label.replace("_", " ").title(): value,
                    "Document Name": doc.filename,
                    "Score": dist,
                })

        if field_type == "date":
            date_val = None
            if inv:
                try:
                    meta = json.loads(inv.raw_metadata) if inv.raw_metadata else {}
                    date_val = meta.get("invoice_date") or meta.get("date") or meta.get("invoiceDate") or meta.get("invoice_date_formatted")
                except Exception:
                    date_val = None
            if not date_val and rec:
                date_val = rec.transaction_date
                if not date_val:
                    try:
                        meta = json.loads(rec.raw_metadata) if rec.raw_metadata else {}
                        date_val = meta.get("transaction_date") or meta.get("date") or meta.get("transactionDate")
                    except Exception:
                        date_val = None
            if not date_val and po:
                date_val = po.order_date
                if not date_val:
                    try:
                        meta = json.loads(po.raw_metadata) if po.raw_metadata else {}
                        date_val = meta.get("order_date") or meta.get("date") or meta.get("orderDate")
                    except Exception:
                        date_val = None
            add_result("date", date_val)
            continue

        if field_type == "vendor":
            vendor_val = None
            if inv:
                vendor_val = inv.vendor
                if not vendor_val:
                    try:
                        meta = json.loads(inv.raw_metadata) if inv.raw_metadata else {}
                        vendor_val = meta.get("vendor_name") or meta.get("supplier_name") or meta.get("vendor")
                    except Exception:
                        vendor_val = None
            if not vendor_val and rec:
                vendor_val = rec.merchant
                if not vendor_val:
                    try:
                        meta = json.loads(rec.raw_metadata) if rec.raw_metadata else {}
                        vendor_val = meta.get("merchant_name") or meta.get("store_name") or meta.get("merchant")
                    except Exception:
                        vendor_val = None
            if not vendor_val and po:
                vendor_val = po.vendor
                if not vendor_val:
                    try:
                        meta = json.loads(po.raw_metadata) if po.raw_metadata else {}
                        vendor_val = meta.get("vendor_name") or meta.get("supplier_name") or meta.get("vendor")
                    except Exception:
                        vendor_val = None
            add_result("vendor", vendor_val)
            continue

        if field_type == "invoice_number" and inv:
            add_result("invoice_number", inv.invoice_number)
            continue

        if field_type == "receipt_number" and rec:
            add_result("receipt_number", rec.receipt_number)
            continue

        if field_type == "po_number" and po:
            add_result("po_number", po.po_number)
            continue

        if field_type == "amount":
            amount_val = None
            currency_val = None
            if inv and inv.total_amount:
                amount_val = inv.total_amount
                currency_val = inv.currency
            if not amount_val and rec and rec.total_amount:
                amount_val = rec.total_amount
                currency_val = rec.currency
            if not amount_val and po and po.total_amount:
                amount_val = po.total_amount
                currency_val = po.currency
            if amount_val:
                add_result("total_amount", amount_val, {"currency": currency_val})
            continue

        if field_type == "currency":
            curr_val = None
            if inv and inv.currency:
                curr_val = inv.currency
            if not curr_val and rec and rec.currency:
                curr_val = rec.currency
            if not curr_val and po and po.currency:
                curr_val = po.currency
            add_result("currency", curr_val)
            continue

        # General fallback: return doc match with score
        results.append({
            "document_id": doc_id,
            "filename": doc.filename,
            "score": dist,
        })
        table_data.append({
            "Document Name": doc.filename,
            "Document ID": doc_id,
            "Score": dist,
        })

    return {
        "session_id": session_id,
        "query": query,
        "field_type": field_type,
        "total_results": len(results),
        "results": results,
        "table_data": table_data,
    }


@router.get("")
def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List all sessions."""
    sessions = db.query(SessionModel).offset(skip).limit(limit).order_by(SessionModel.created_at.desc()).all()
    total = db.query(SessionModel).count()

    session_list = []
    for session in sessions:
        doc_count = db.query(Document).filter(Document.session_id == session.id).count()
        session_list.append({
            "session_id": session.id,
            "name": session.name,
            "document_count": doc_count,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "sessions": session_list,
    }

