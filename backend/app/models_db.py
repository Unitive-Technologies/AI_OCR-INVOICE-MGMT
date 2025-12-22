from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Float, Boolean, Integer
from sqlalchemy.orm import relationship

from app.db import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    storage_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ocr_results = relationship("OCRResult", back_populates="document", uselist=False, cascade="all, delete-orphan")
    classifications = relationship("DocumentClassification", back_populates="document", cascade="all, delete-orphan")
    processing_history = relationship("DocumentProcessing", back_populates="document", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="document", cascade="all, delete-orphan")
    receipts = relationship("Receipt", back_populates="document", cascade="all, delete-orphan")
    purchase_orders = relationship("PurchaseOrder", back_populates="document", cascade="all, delete-orphan")
    extraction_results = relationship("ExtractionResult", back_populates="document", cascade="all, delete-orphan")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    vendor = Column(String, nullable=True)
    invoice_number = Column(String, nullable=True, index=True)
    currency = Column(String, nullable=True)
    total_amount = Column(String, nullable=True)
    raw_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship (optional, for easier querying)
    document = relationship("Document", back_populates="invoices")


# OCR Results - Store extracted text in DB instead of files
class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(String, primary_key=True, index=True)  # Same as document_id
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False,
                         index=True)
    extracted_text = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="ocr_results")


# Document Classification - Store detection results
class DocumentClassification(Base):
    __tablename__ = "document_classifications"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    detected_type = Column(String, nullable=False, index=True)
    confidence = Column(Float, nullable=True)
    classifier_used = Column(String, nullable=True)  # e.g., "gemini", "rules_engine"
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="classifications")


# Document Processing Status/History
class DocumentProcessing(Base):
    __tablename__ = "document_processing"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    operation = Column(String, nullable=False, index=True)  # "ocr", "classify", "extract", etc.
    status = Column(String, nullable=False, index=True)  # "pending", "processing", "completed", "failed"
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="processing_history")


# Receipt - Similar structure to Invoice
class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    merchant = Column(String, nullable=True)
    receipt_number = Column(String, nullable=True, index=True)
    transaction_date = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    total_amount = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)
    raw_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="receipts")


# Purchase Order
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    po_number = Column(String, nullable=True, index=True)
    vendor = Column(String, nullable=True)
    buyer = Column(String, nullable=True)
    order_date = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    total_amount = Column(String, nullable=True)
    raw_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="purchase_orders")


# Generic Extraction Results - For document types without dedicated tables
class ExtractionResult(Base):
    __tablename__ = "extraction_results"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    document_type = Column(String, nullable=False, index=True)  # "notes", "id_card", "resume", etc.
    raw_metadata = Column(Text, nullable=False)  # JSON blob
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="extraction_results")

