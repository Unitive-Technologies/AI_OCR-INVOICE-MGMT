from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, Float, func, text
from typing import List, Optional
from datetime import datetime
import uuid
import json
import logging

from app.db import get_db
from app.models_db import Session as SessionModel, Document, Invoice, Receipt, PurchaseOrder, ExtractionResult
from app.services.document_service import document_service
from app.services.ocr_service import ocr_service
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
    """Process all documents in a session (OCR, detect, extract)."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get ALL documents in the session
    documents = db.query(Document).filter(Document.session_id == session_id).all()
    logger.info(f"Processing {len(documents)} documents for session {session_id}")

    if not documents:
        raise HTTPException(status_code=400, detail="No documents in session")

    results = []
    for idx, doc in enumerate(documents, 1):
        logger.info(f"Processing document {idx}/{len(documents)}: {doc.filename} (ID: {doc.id})")
        try:
            # OCR
            raw_bytes = document_service.read_file_bytes(doc.id, db=db)
            text = ocr_service.extract_text(raw_bytes)
            document_service.save_text(doc.id, text, db=db)
            logger.info(f"OCR completed for {doc.filename}")

            # Detect
            detected = gemini.classify_document(text)
            detected_type = detected.get("document_type")
            logger.info(f"Detected type: {detected_type} for {doc.filename}")

            # Extract
            extraction = gemini.extract_structured(text, detected_type)
            logger.info(f"Extraction completed for {doc.filename}")

            # Save extraction (similar to extract_router logic)
            if isinstance(extraction, dict):
                extraction_json = json.dumps(extraction)

                if detected_type == "invoice":
                    invoice = Invoice(
                        id=doc.id,
                        document_id=doc.id,
                        vendor=extraction.get("vendor_name") or extraction.get("supplier_name") or extraction.get(
                            "vendor"),
                        invoice_number=extraction.get("invoice_number"),
                        currency=extraction.get("currency"),
                        total_amount=str(extraction.get("total_amount")) if extraction.get("total_amount") else None,
                        raw_metadata=extraction_json,
                    )
                    db.merge(invoice)
                    logger.info(f"Invoice metadata saved for {doc.filename}")
                elif detected_type == "receipt":
                    receipt = Receipt(
                        id=doc.id,
                        document_id=doc.id,
                        merchant=extraction.get("merchant_name") or extraction.get("store_name") or extraction.get(
                            "merchant"),
                        receipt_number=extraction.get("receipt_number") or extraction.get("transaction_id"),
                        transaction_date=extraction.get("transaction_date") or extraction.get("date"),
                        currency=extraction.get("currency"),
                        total_amount=str(extraction.get("total_amount")) if extraction.get("total_amount") else None,
                        payment_method=extraction.get("payment_method"),
                        raw_metadata=extraction_json,
                    )
                    db.merge(receipt)
                    logger.info(f"Receipt metadata saved for {doc.filename}")
                elif detected_type in ["purchase_order", "po"]:
                    po = PurchaseOrder(
                        id=doc.id,
                        document_id=doc.id,
                        po_number=extraction.get("po_number") or extraction.get("purchase_order_number"),
                        vendor=extraction.get("vendor_name") or extraction.get("supplier_name") or extraction.get(
                            "vendor"),
                        buyer=extraction.get("buyer_name") or extraction.get("customer_name"),
                        order_date=extraction.get("order_date") or extraction.get("po_date"),
                        currency=extraction.get("currency"),
                        total_amount=str(extraction.get("total_amount")) if extraction.get("total_amount") else None,
                        raw_metadata=extraction_json,
                    )
                    db.merge(po)
                    logger.info(f"Purchase order metadata saved for {doc.filename}")
                else:
                    extract_result = ExtractionResult(
                        id=doc.id,
                        document_id=doc.id,
                        document_type=detected_type,
                        raw_metadata=extraction_json,
                    )
                    db.merge(extract_result)
                    logger.info(f"Extraction result saved for {detected_type}, {doc.filename}")

                db.commit()

            results.append({
                "file_id": doc.id,
                "filename": doc.filename,
                "status": "success",
                "detected_type": detected_type,
            })
        except Exception as e:
            logger.error(f"Error processing {doc.filename}: {str(e)}", exc_info=True)
            results.append({
                "file_id": doc.id,
                "filename": doc.filename,
                "status": "error",
                "error": str(e),
            })

    logger.info(
        f"Processing complete. Success: {len([r for r in results if r['status'] == 'success'])}, Failed: {len([r for r in results if r['status'] == 'error'])}")

    return {
        "session_id": session_id,
        "processed": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "error"]),
        "results": results,
    }


@router.get("/{session_id}/search")
def search_session(
        session_id: str,
        query: str = Query(..., description="Search keywords"),
        db: Session = Depends(get_db),
):
    """
    Search across all documents in a session using OCR text.
    If query matches a field name (e.g., "date", "vendor"), returns only that field.
    Returns results in table and JSON format.
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get all documents in session
    documents = db.query(Document).filter(Document.session_id == session_id).all()
    document_ids = [doc.id for doc in documents]

    if not document_ids:
        return {
            "session_id": session_id,
            "query": query,
            "total_results": 0,
            "results": [],
            "table_data": [],
        }

    query_lower = query.lower().strip()

    # Detect field type from query (simple keyword matching - no LLM)
    field_type = "general"
    if any(word in query_lower for word in ["date", "when", "invoice date", "transaction date"]):
        field_type = "date"
    elif any(word in query_lower for word in ["vendor", "supplier", "merchant"]):
        field_type = "vendor"
    elif any(word in query_lower for word in ["invoice number", "invoice no", "inv number"]):
        field_type = "invoice_number"
    elif any(word in query_lower for word in ["receipt number", "receipt no"]):
        field_type = "receipt_number"
    elif any(word in query_lower for word in ["po number", "purchase order", "po no"]):
        field_type = "po_number"
    elif any(word in query_lower for word in ["amount", "total", "price", "cost"]):
        field_type = "amount"
    elif any(word in query_lower for word in ["currency", "money"]):
        field_type = "currency"

    # Search OCR text for the query
    matching_docs = []
    for doc in documents:
        # Get OCR text
        ocr_text = document_service.get_text(doc.id, db=db)
        if ocr_text and query.lower() in ocr_text.lower():
            matching_docs.append(doc)

    if not matching_docs:
        return {
            "session_id": session_id,
            "query": query,
            "field_type": field_type,
            "total_results": 0,
            "results": [],
            "table_data": [],
        }

    results = []
    table_data = []

    # Get extraction results for matching documents
    matching_doc_ids = [doc.id for doc in matching_docs]

    if field_type == "date":
        # Get dates from invoices
        invoices = db.query(Invoice).filter(Invoice.document_id.in_(matching_doc_ids)).all()
        for inv in invoices:
            doc = next((d for d in matching_docs if d.id == inv.document_id), None)
            if not doc:
                continue
            try:
                metadata = json.loads(inv.raw_metadata) if inv.raw_metadata else {}
                invoice_date = (
                        metadata.get("invoice_date") or
                        metadata.get("date") or
                        metadata.get("invoiceDate") or
                        metadata.get("invoice_date_formatted") or
                        ""
                )
                if invoice_date:
                    results.append({
                        "document_id": inv.document_id,
                        "document_type": "invoice",
                        "filename": doc.filename,
                        "date": invoice_date,
                    })
                    table_data.append({
                        "Date": invoice_date,
                        "Document Name": doc.filename,
                    })
            except:
                pass

        # Get dates from receipts
        receipts = db.query(Receipt).filter(Receipt.document_id.in_(matching_doc_ids)).all()
        for rec in receipts:
            doc = next((d for d in matching_docs if d.id == rec.document_id), None)
            if not doc:
                continue
            transaction_date = rec.transaction_date or ""
            if not transaction_date:
                try:
                    metadata = json.loads(rec.raw_metadata) if rec.raw_metadata else {}
                    transaction_date = (
                            metadata.get("transaction_date") or
                            metadata.get("date") or
                            metadata.get("transactionDate") or
                            ""
                    )
                except:
                    pass

            if transaction_date:
                results.append({
                    "document_id": rec.document_id,
                    "document_type": "receipt",
                    "filename": doc.filename,
                    "date": transaction_date,
                })
                table_data.append({
                    "Date": transaction_date,
                    "Document Name": doc.filename,
                })

        # Get dates from purchase orders
        pos = db.query(PurchaseOrder).filter(PurchaseOrder.document_id.in_(matching_doc_ids)).all()
        for po in pos:
            doc = next((d for d in matching_docs if d.id == po.document_id), None)
            if not doc:
                continue
            order_date = po.order_date or ""
            if not order_date:
                try:
                    metadata = json.loads(po.raw_metadata) if po.raw_metadata else {}
                    order_date = (
                            metadata.get("order_date") or
                            metadata.get("date") or
                            metadata.get("orderDate") or
                            ""
                    )
                except:
                    pass

            if order_date:
                results.append({
                    "document_id": po.document_id,
                    "document_type": "purchase_order",
                    "filename": doc.filename,
                    "date": order_date,
                })
                table_data.append({
                    "Date": order_date,
                    "Document Name": doc.filename,
                })

    elif field_type == "vendor":
        # Get vendors from invoices
        invoices = db.query(Invoice).filter(Invoice.document_id.in_(matching_doc_ids)).all()
        for inv in invoices:
            doc = next((d for d in matching_docs if d.id == inv.document_id), None)
            if not doc:
                continue
            vendor = inv.vendor or ""
            if not vendor:
                try:
                    metadata = json.loads(inv.raw_metadata) if inv.raw_metadata else {}
                    vendor = (
                            metadata.get("vendor_name") or
                            metadata.get("supplier_name") or
                            metadata.get("vendor") or
                            ""
                    )
                except:
                    pass

            if vendor:
                results.append({
                    "document_id": inv.document_id,
                    "document_type": "invoice",
                    "filename": doc.filename,
                    "vendor": vendor,
                })
                table_data.append({
                    "Vendor": vendor,
                    "Document Name": doc.filename,
                })

        # Get merchants from receipts
        receipts = db.query(Receipt).filter(Receipt.document_id.in_(matching_doc_ids)).all()
        for rec in receipts:
            doc = next((d for d in matching_docs if d.id == rec.document_id), None)
            if not doc:
                continue
            merchant = rec.merchant or ""
            if not merchant:
                try:
                    metadata = json.loads(rec.raw_metadata) if rec.raw_metadata else {}
                    merchant = (
                            metadata.get("merchant_name") or
                            metadata.get("store_name") or
                            metadata.get("merchant") or
                            ""
                    )
                except:
                    pass

            if merchant:
                results.append({
                    "document_id": rec.document_id,
                    "document_type": "receipt",
                    "filename": doc.filename,
                    "merchant": merchant,
                })
                table_data.append({
                    "Vendor": merchant,
                    "Document Name": doc.filename,
                })

        # Get vendors from purchase orders
        pos = db.query(PurchaseOrder).filter(PurchaseOrder.document_id.in_(matching_doc_ids)).all()
        for po in pos:
            doc = next((d for d in matching_docs if d.id == po.document_id), None)
            if not doc:
                continue
            vendor = po.vendor or ""
            if not vendor:
                try:
                    metadata = json.loads(po.raw_metadata) if po.raw_metadata else {}
                    vendor = (
                            metadata.get("vendor_name") or
                            metadata.get("supplier_name") or
                            metadata.get("vendor") or
                            ""
                    )
                except:
                    pass

            if vendor:
                results.append({
                    "document_id": po.document_id,
                    "document_type": "purchase_order",
                    "filename": doc.filename,
                    "vendor": vendor,
                })
                table_data.append({
                    "Vendor": vendor,
                    "Document Name": doc.filename,
                })

    elif field_type == "invoice_number":
        invoices = db.query(Invoice).filter(Invoice.document_id.in_(matching_doc_ids)).all()
        for inv in invoices:
            doc = next((d for d in matching_docs if d.id == inv.document_id), None)
            if not doc:
                continue
            invoice_num = inv.invoice_number or ""
            if invoice_num:
                results.append({
                    "document_id": inv.document_id,
                    "document_type": "invoice",
                    "filename": doc.filename,
                    "invoice_number": invoice_num,
                })
                table_data.append({
                    "Invoice Number": invoice_num,
                    "Document Name": doc.filename,
                })

    elif field_type == "receipt_number":
        receipts = db.query(Receipt).filter(Receipt.document_id.in_(matching_doc_ids)).all()
        for rec in receipts:
            doc = next((d for d in matching_docs if d.id == rec.document_id), None)
            if not doc:
                continue
            receipt_num = rec.receipt_number or ""
            if receipt_num:
                results.append({
                    "document_id": rec.document_id,
                    "document_type": "receipt",
                    "filename": doc.filename,
                    "receipt_number": receipt_num,
                })
                table_data.append({
                    "Receipt Number": receipt_num,
                    "Document Name": doc.filename,
                })

    elif field_type == "po_number":
        pos = db.query(PurchaseOrder).filter(PurchaseOrder.document_id.in_(matching_doc_ids)).all()
        for po in pos:
            doc = next((d for d in matching_docs if d.id == po.document_id), None)
            if not doc:
                continue
            po_num = po.po_number or ""
            if po_num:
                results.append({
                    "document_id": po.document_id,
                    "document_type": "purchase_order",
                    "filename": doc.filename,
                    "po_number": po_num,
                })
                table_data.append({
                    "PO Number": po_num,
                    "Document Name": doc.filename,
                })

    elif field_type == "amount":
        # Get amounts from all document types
        invoices = db.query(Invoice).filter(Invoice.document_id.in_(matching_doc_ids)).all()
        for inv in invoices:
            doc = next((d for d in matching_docs if d.id == inv.document_id), None)
            if not doc:
                continue
            amount = inv.total_amount or ""
            currency = inv.currency or ""
            if amount:
                results.append({
                    "document_id": inv.document_id,
                    "document_type": "invoice",
                    "filename": doc.filename,
                    "total_amount": amount,
                    "currency": currency,
                })
                table_data.append({
                    "Total Amount": amount,
                    "Currency": currency,
                    "Document Name": doc.filename,
                })

        receipts = db.query(Receipt).filter(Receipt.document_id.in_(matching_doc_ids)).all()
        for rec in receipts:
            doc = next((d for d in matching_docs if d.id == rec.document_id), None)
            if not doc:
                continue
            amount = rec.total_amount or ""
            currency = rec.currency or ""
            if amount:
                results.append({
                    "document_id": rec.document_id,
                    "document_type": "receipt",
                    "filename": doc.filename,
                    "total_amount": amount,
                    "currency": currency,
                })
                table_data.append({
                    "Total Amount": amount,
                    "Currency": currency,
                    "Document Name": doc.filename,
                })

        pos = db.query(PurchaseOrder).filter(PurchaseOrder.document_id.in_(matching_doc_ids)).all()
        for po in pos:
            doc = next((d for d in matching_docs if d.id == po.document_id), None)
            if not doc:
                continue
            amount = po.total_amount or ""
            currency = po.currency or ""
            if amount:
                results.append({
                    "document_id": po.document_id,
                    "document_type": "purchase_order",
                    "filename": doc.filename,
                    "total_amount": amount,
                    "currency": currency,
                })
                table_data.append({
                    "Total Amount": amount,
                    "Currency": currency,
                    "Document Name": doc.filename,
                })

    elif field_type == "currency":
        invoices = db.query(Invoice).filter(Invoice.document_id.in_(matching_doc_ids)).all()
        for inv in invoices:
            doc = next((d for d in matching_docs if d.id == inv.document_id), None)
            if not doc:
                continue
            currency = inv.currency or ""
            if currency:
                results.append({
                    "document_id": inv.document_id,
                    "document_type": "invoice",
                    "filename": doc.filename,
                    "currency": currency,
                })
                table_data.append({
                    "Currency": currency,
                    "Document Name": doc.filename,
                })

        receipts = db.query(Receipt).filter(Receipt.document_id.in_(matching_doc_ids)).all()
        for rec in receipts:
            doc = next((d for d in matching_docs if d.id == rec.document_id), None)
            if not doc:
                continue
            currency = rec.currency or ""
            if currency:
                results.append({
                    "document_id": rec.document_id,
                    "document_type": "receipt",
                    "filename": doc.filename,
                    "currency": currency,
                })
                table_data.append({
                    "Currency": currency,
                    "Document Name": doc.filename,
                })

        pos = db.query(PurchaseOrder).filter(PurchaseOrder.document_id.in_(matching_doc_ids)).all()
        for po in pos:
            doc = next((d for d in matching_docs if d.id == po.document_id), None)
            if not doc:
                continue
            currency = po.currency or ""
            if currency:
                results.append({
                    "document_id": po.document_id,
                    "document_type": "purchase_order",
                    "filename": doc.filename,
                    "currency": currency,
                })
                table_data.append({
                    "Currency": currency,
                    "Document Name": doc.filename,
                })

    else:
        # General search - return basic document info
        for doc in matching_docs:
            results.append({
                "document_id": doc.id,
                "filename": doc.filename,
            })
            table_data.append({
                "Document Name": doc.filename,
                "Document ID": doc.id,
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