from pydantic import BaseModel
from typing import Dict, List
from datetime import datetime

class AssessmentQuestion(BaseModel):
    id: int
    question: str
    options: List[str]
    category: str

class AssessmentResponse(BaseModel):
    question_id: int
    answer: str

class AssessmentSubmission(BaseModel):
    responses: List[AssessmentResponse]

class AssessmentResult(BaseModel):
    learning_style_result: str
    visual_score: int
    auditory_score: int
    kinesthetic_score: int
    reading_score: int
    completed_at: datetime
    
    class Config:
        from_attributes = True
