from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.document_service import document_service

router = APIRouter(prefix="/api/upload", tags=["Upload"])

@router.post("")
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Read raw bytes
    file_bytes = await file.read()

    # Save raw bytes into service and persist document metadata
    file_id = document_service.save_file(
        file_bytes,
        filename=file.filename,
        db=db,
    )

    return {
        "file_id": file_id,
        "filename": file.filename
    }
