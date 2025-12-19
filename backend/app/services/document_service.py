import os
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models_db import Document


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
    def read_file_bytes(self, file_id: str) -> bytes:
        path = os.path.join(self.upload_dir, f"{file_id}.pdf")

        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found in uploads/: {file_id}")

        with open(path, "rb") as f:
            return f.read()

    # ------------------------------------------
    # SAVE OCR TEXT TO CACHE
    # ------------------------------------------
    def save_text(self, file_id: str, text: str):
        path = os.path.join(self.cache_dir, f"{file_id}.txt")

        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    # ------------------------------------------
    # GET OCR TEXT FROM CACHE
    # ------------------------------------------
    def get_text(self, file_id: str) -> Optional[str]:
        path = os.path.join(self.cache_dir, f"{file_id}.txt")

        if not os.path.exists(path):
            return None

        with open(path, "r", encoding="utf-8") as f:
            return f.read()


# Singleton instance
document_service = DocumentService()
