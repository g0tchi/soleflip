"""
Simplified SQLAlchemy Models for Demo
Only the essential models for the import functionality
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class ImportBatch(Base, TimestampMixin):
    """Batch tracking for data imports"""
    __tablename__ = "import_batches"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_type = Column(String(50), nullable=False)  # stockx, notion, manual
    source_file = Column(String(255))
    total_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    error_records = Column(Integer, default=0)
    status = Column(String(50), default="pending")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    import_records = relationship("ImportRecord", back_populates="batch")

class ImportRecord(Base, TimestampMixin):
    """Individual import records with validation"""
    __tablename__ = "import_records"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id = Column(String(36), ForeignKey("import_batches.id"), nullable=False)
    source_data = Column(Text, nullable=False)  # JSON as TEXT for SQLite
    processed_data = Column(Text)  # JSON as TEXT for SQLite
    validation_errors = Column(Text)  # JSON array as TEXT for SQLite
    status = Column(String(50), default="pending")
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    error_message = Column(Text)
    
    # Relationships
    batch = relationship("ImportBatch", back_populates="import_records")