import os
import uuid
import logging
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.models_db import Document, OCRResult

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self):
        self.upload_dir = "uploads"
        self.cache_dir = "cache"

        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

    # ------------------------------------------
    # SAVE FILE
    # ------------------------------------------
    def save_file(self, file: bytes, filename: str | None = None, db: Session | None = None) -> str:
        """
        Save raw file bytes to disk, return file_id (UUID).
        Optionally persist basic document metadata to the database if a Session is provided.
        """
        file_id = str(uuid.uuid4())
        # Keep original filename extension if available, else default to .pdf
        if filename:
            _, ext = os.path.splitext(filename)
            ext = ext or ".pdf"
        else:
            ext = ".pdf"

        stored_filename = f"{file_id}{ext}"

        path = os.path.join(self.upload_dir, stored_filename)

        with open(path, "wb") as f:
            f.write(file)

        # Optionally record metadata in DB
        if db is not None:
            doc = Document(
                id=file_id,
                filename=filename or stored_filename,
                content_type=None,  # can be filled by caller if needed
                storage_path=path,
            )
            db.add(doc)
            db.commit()

        return file_id

    # ------------------------------------------
    # READ RAW BYTES FOR OCR
    # ------------------------------------------
    def read_file_bytes(self, file_id: str, db: Session | None = None) -> bytes:
        """
        Read file bytes. Try to get path from DB if session provided, otherwise search by file_id prefix.
        """
        path = None

        # Try to get path from DB first
        if db is not None:
            try:
                doc = db.query(Document).filter(Document.id == file_id).first()
                if doc and doc.storage_path and os.path.exists(doc.storage_path):
                    path = doc.storage_path
            except Exception:
                pass  # Fall back to file search

        # If not found in DB, search for file by file_id prefix
        if not path:
            if os.path.exists(self.upload_dir):
                for fname in os.listdir(self.upload_dir):
                    if fname.startswith(file_id):
                        path = os.path.join(self.upload_dir, fname)
                        break

        # Last resort: try .pdf extension (legacy)
        if not path:
            legacy_path = os.path.join(self.upload_dir, f"{file_id}.pdf")
            if os.path.exists(legacy_path):
                path = legacy_path

        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"File not found for file_id: {file_id}")

        with open(path, "rb") as f:
            return f.read()

    # ------------------------------------------
    # SAVE OCR TEXT TO CACHE (and optionally DB)
    # ------------------------------------------
    def save_text(self, file_id: str, text: str, db: Session | None = None):
        """
        Save OCR text to file cache (legacy) and optionally to database.
        """
        # Save to file (legacy support)
        path = os.path.join(self.cache_dir, f"{file_id}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

        # Save to database if session provided
        if db is not None:
            try:
                word_count = len(text.split()) if text else 0
                ocr_result = OCRResult(
                    id=file_id,
                    document_id=file_id,
                    extracted_text=text,
                    word_count=word_count,
                    processed_at=datetime.utcnow(),
                )
                db.merge(ocr_result)  # upsert
                db.commit()
                logger.info(f"OCR result saved to DB for file_id: {file_id}, word_count: {word_count}")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to save OCR result to DB for {file_id}: {e}", exc_info=True)
                # Don't fail if DB write fails, file cache still works

    # ------------------------------------------
    # GET OCR TEXT FROM CACHE (or DB)
    # ------------------------------------------
    def get_text(self, file_id: str, db: Session | None = None) -> Optional[str]:
        """
        Get OCR text, trying DB first if session provided, then falling back to file cache.
        """
        # Try DB first if session provided
        if db is not None:
            try:
                ocr_result = db.query(OCRResult).filter(OCRResult.document_id == file_id).first()
                if ocr_result and ocr_result.extracted_text:
                    return ocr_result.extracted_text
            except Exception:
                pass  # Fall back to file cache

        # Fall back to file cache (legacy)
        path = os.path.join(self.cache_dir, f"{file_id}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

        return None


# Singleton instance
document_service = DocumentService()
