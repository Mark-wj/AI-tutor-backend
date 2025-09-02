from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.quiz import QuestionType, DifficultyLevel

class QuestionBase(BaseModel):
    question_text: str
    question_type: QuestionType
    correct_answer: str
    options: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    difficulty_level: DifficultyLevel

class QuestionCreate(QuestionBase):
    order_index: int = 0

class QuestionResponse(QuestionBase):
    id: int
    quiz_id: int
    order_index: int
    
    class Config:
        from_attributes = True

class QuizBase(BaseModel):
    title: str
    description: Optional[str] = None

class QuizCreate(QuizBase):
    document_id: int

class QuizResponse(QuizBase):
    id: int
    document_id: int
    user_id: int
    total_questions: int
    is_active: bool
    created_at: datetime
    questions: Optional[List[QuestionResponse]] = None
    
    class Config:
        from_attributes = True

class QuizAttemptCreate(BaseModel):
    answers: Dict[int, str]  # question_id -> answer

class QuizAttemptResponse(BaseModel):
    id: int
    quiz_id: int
    score: float
    total_questions: int
    correct_answers: int
    time_taken: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True