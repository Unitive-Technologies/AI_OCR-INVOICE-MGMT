from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import json
import logging
import uuid
from datetime import datetime

from app.services.document_service import document_service
from app.llm.gemini_client import GeminiClient
from app.services.nlp_service import nlp_service
from app.db import get_db
from app.models_db import (
    Invoice, Receipt, PurchaseOrder, ExtractionResult, DocumentProcessing
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Extraction"])
gemini = GeminiClient()


@router.post("/extract/{file_id}")
async def extract_document(
        file_id: str,
        override_type: str | None = None,
        include_summary: bool = False,
        include_embeddings: bool = False,
        db: Session = Depends(get_db),
):
    # Track processing start
    process_id = str(uuid.uuid4())
    try:
        process_record = DocumentProcessing(
            id=process_id,
            document_id=file_id,
            operation="extract",
            status="processing",
            processed_at=datetime.utcnow(),
        )
        db.add(process_record)
        db.commit()
    except Exception:
        db.rollback()

    # 1. Get OCR text
    text = document_service.get_text(file_id, db=db)
    if not text:
        try:
            process_record.status = "failed"
            process_record.error_message = "OCR missing. Run /api/ocr first."
            process_record.completed_at = datetime.utcnow()
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(status_code=400, detail="OCR missing. Run /api/ocr first.")

    # 2. Detect type using Gemini
    detected = gemini.classify_document(text)
    detected_type = detected.get("document_type")
    confidence = detected.get("confidence", 0.0)

    # Use override only if provided
    used_type = override_type or detected_type

    # 3. Extract structured information
    try:
        extraction = gemini.extract_structured(text, used_type)
    except Exception as e:
        try:
            process_record.status = "failed"
            process_record.error_message = f"Extraction failed: {str(e)}"
            process_record.completed_at = datetime.utcnow()
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    # 3b. Save extraction results to appropriate table based on document type
    if isinstance(extraction, dict):
        try:
            extraction_json = json.dumps(extraction)

            if used_type == "invoice":
                invoice = Invoice(
                    id=file_id,
                    document_id=file_id,
                    vendor=extraction.get("vendor_name") or extraction.get("supplier_name"),
                    invoice_number=extraction.get("invoice_number"),
                    currency=extraction.get("currency"),
                    total_amount=str(extraction.get("total_amount")) if extraction.get(
                        "total_amount") is not None else None,
                    raw_metadata=extraction_json,
                )
                db.merge(invoice)
                logger.info(f"Invoice metadata saved for file_id: {file_id}")

            elif used_type == "receipt":
                receipt = Receipt(
                    id=file_id,
                    document_id=file_id,
                    merchant=extraction.get("merchant_name") or extraction.get("store_name"),
                    receipt_number=extraction.get("receipt_number") or extraction.get("transaction_id"),
                    transaction_date=extraction.get("transaction_date") or extraction.get("date"),
                    currency=extraction.get("currency"),
                    total_amount=str(extraction.get("total_amount")) if extraction.get(
                        "total_amount") is not None else None,
                    payment_method=extraction.get("payment_method"),
                    raw_metadata=extraction_json,
                )
                db.merge(receipt)
                logger.info(f"Receipt metadata saved for file_id: {file_id}")

            elif used_type == "purchase_order" or used_type == "po":
                po = PurchaseOrder(
                    id=file_id,
                    document_id=file_id,
                    po_number=extraction.get("po_number") or extraction.get("purchase_order_number"),
                    vendor=extraction.get("vendor_name") or extraction.get("supplier_name"),
                    buyer=extraction.get("buyer_name") or extraction.get("customer_name"),
                    order_date=extraction.get("order_date") or extraction.get("po_date"),
                    currency=extraction.get("currency"),
                    total_amount=str(extraction.get("total_amount")) if extraction.get(
                        "total_amount") is not None else None,
                    raw_metadata=extraction_json,
                )
                db.merge(po)
                logger.info(f"Purchase order metadata saved for file_id: {file_id}")

            else:
                # Generic extraction result for other document types
                extract_result = ExtractionResult(
                    id=file_id,
                    document_id=file_id,
                    document_type=used_type,
                    raw_metadata=extraction_json,
                )
                db.merge(extract_result)
                logger.info(f"Extraction result saved for {used_type}, file_id: {file_id}")

            # Mark processing as completed
            process_record.status = "completed"
            process_record.completed_at = datetime.utcnow()
            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save extraction metadata for {file_id}: {e}", exc_info=True)
            # Don't fail the request, but mark processing as failed
            try:
                process_record.status = "failed"
                process_record.error_message = f"DB save failed: {str(e)}"
                process_record.completed_at = datetime.utcnow()
                db.commit()
            except Exception:
                db.rollback()

    # 4. Summary
    summary = gemini.summarize(text) if include_summary else None

    # 5. Embeddings
    embeddings = nlp_service.embed_text(text) if include_embeddings else None

    return {
        "file_id": file_id,
        "detected_type": detected_type,
        "used_type": used_type,
        "override_used": override_type is not None,
        "detection_confidence": confidence,
        "extraction": extraction,
        "summary": summary,
        "embeddings": embeddings,
    }
