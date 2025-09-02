from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum
import json

class QuestionType(enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"

class DifficultyLevel(enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class Quiz(Base):
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    estimated_duration = Column(Integer, nullable=True)  # in minutes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="quizzes")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    submissions = relationship("QuizSubmission", back_populates="quiz", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "documentId": str(self.document_id),
            "difficulty": self.difficulty.value,
            "totalQuestions": len(self.questions),
            "estimatedDuration": self.estimated_duration or 10,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "questions": [q.to_dict() for q in self.questions]
        }

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), default=QuestionType.MULTIPLE_CHOICE)
    options = Column(JSON, nullable=True)  # Store as JSON for multiple choice
    correct_answer = Column(String(500), nullable=False)
    explanation = Column(Text, nullable=True)
    order_index = Column(Integer, default=0)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")

    def to_dict(self):
        return {
            "id": str(self.id),
            "text": self.question_text,
            "type": self.question_type.value,
            "options": self.parse_options() if self.options else None,
            "correctAnswer": self.correct_answer,
            "explanation": self.explanation
        }

    def parse_options(self):
        """Parse options from JSON or string format"""
        if not self.options:
            return None
            
        if isinstance(self.options, dict):
            return [{"id": k, "text": v, "isCorrect": k == self.correct_answer} 
                   for k, v in self.options.items()]
        elif isinstance(self.options, str):
            try:
                options_dict = json.loads(self.options)
                return [{"id": k, "text": v, "isCorrect": k == self.correct_answer} 
                       for k, v in options_dict.items()]
            except json.JSONDecodeError:
                return None
        return None

class QuizSubmission(Base):
    __tablename__ = "quiz_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answers = Column(JSON, nullable=False)  # Store user answers
    score = Column(Integer, nullable=False)  # Score as percentage
    time_spent = Column(Integer, nullable=True)  # Time in seconds
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships - FIXED: Removed problematic document relationship
    quiz = relationship("Quiz", back_populates="submissions")
    user = relationship("User", back_populates="quiz_submissions")
    
    # Property to access document through quiz
    @property
    def document(self):
        return self.quiz.document if self.quiz else None

    def to_dict(self):
        return {
            "id": str(self.id),
            "quizId": str(self.quiz_id),
            "userId": str(self.user_id),
            "answers": self.answers,
            "score": self.score,
            "timeSpent": self.time_spent,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None
        }