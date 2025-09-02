from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum

class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "processed"  # Changed to match frontend expectation
    FAILED = "failed"

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)  # Add original filename
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False, default="application/pdf")
    page_count = Column(Integer, nullable=True)
    content = Column(Text, nullable=True)  # Renamed from extracted_text
    summary = Column(Text, nullable=True)  # Renamed from ai_summary
    key_topics = Column(JSON, nullable=True)  # Add key topics as JSON array
    tags = Column(JSON, nullable=True)  # Add tags as JSON array
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="documents")
    quizzes = relationship("Quiz", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        """Convert model to dictionary matching frontend expectations"""
        return {
            "id": str(self.id),
            "name": self.filename,
            "originalName": self.original_name,
            "fileSize": self.file_size,
            "mimeType": self.mime_type,
            "status": self.processing_status.value,
            "uploadDate": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "processedAt": self.processed_at.isoformat() if self.processed_at else None,
            "summary": self.summary,
            "content": self.content,
            "pageCount": self.page_count,
            "tags": self.tags or [],
            "userId": str(self.user_id)
        }