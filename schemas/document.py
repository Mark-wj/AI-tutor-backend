from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models.document import ProcessingStatus

class DocumentBase(BaseModel):
    filename: str

class DocumentSummary(BaseModel):
    id: int
    title: str
    description: str

class QuizQuestion(BaseModel):  # ✅ now defined here if you want
    id: int
    question: str
    options: List[str]
    answer: str

class DocumentCreate(DocumentBase):
    file_path: str
    file_size: int

class DocumentResponse(DocumentBase):
    id: int
    user_id: int
    file_size: int
    processing_status: ProcessingStatus
    ai_summary: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class DocumentSummary(BaseModel):
    summary: str
    word_count: int
    key_topics: List[str]