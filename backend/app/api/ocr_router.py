from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.services.ocr_service import ocr_service
from app.services.document_service import document_service
from app.models.ocr_response import OCRResponse
from app.db import get_db
from app.models_db import DocumentProcessing

router = APIRouter(prefix="/api/ocr", tags=["OCR"])


@router.post("/{file_id}", response_model=OCRResponse)
async def perform_ocr(
        file_id: str,
        db: Session = Depends(get_db),
):
    # Track processing start
    process_id = str(uuid.uuid4())
    process_record = None
    try:
        process_record = DocumentProcessing(
            id=process_id,
            document_id=file_id,
            operation="ocr",
            status="processing",
            processed_at=datetime.utcnow(),
        )
        db.add(process_record)
        db.commit()
    except Exception as e:
        db.rollback()
        # Log but continue - processing record is optional for tracking

    try:
        raw_bytes = document_service.read_file_bytes(file_id, db=db)
    except FileNotFoundError as e:
        # Update status to failed if we have a process_record
        if process_record:
            try:
                process_record.status = "failed"
                process_record.error_message = str(e)
                process_record.completed_at = datetime.utcnow()
                db.commit()
            except Exception:
                db.rollback()
        raise HTTPException(status_code=404, detail=str(e))

    try:
        text = ocr_service.extract_text(raw_bytes)

        # Save to DB (and file cache)
        document_service.save_text(file_id, text, db=db)

        # Update processing status to completed
        if process_record:
            try:
                process_record.status = "completed"
                process_record.completed_at = datetime.utcnow()
                db.commit()
            except Exception:
                db.rollback()

        return OCRResponse(file_id=file_id, text=text)

    except Exception as e:
        # Update status to failed if we have a process_record
        if process_record:
            try:
                process_record.status = "failed"
                process_record.error_message = str(e)
                process_record.completed_at = datetime.utcnow()
                db.commit()
            except Exception:
                db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Document AI OCR failed: {str(e)}"
        )
