from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.db import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    storage_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, index=True, nullable=False)
    vendor = Column(String, nullable=True)
    invoice_number = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    total_amount = Column(String, nullable=True)
    raw_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


