from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class LearningAssessment(Base):
    __tablename__ = "learning_assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assessment_data = Column(JSON, nullable=False)
    learning_style_result = Column(String(100), nullable=False)
    visual_score = Column(Integer, default=0)
    auditory_score = Column(Integer, default=0)
    kinesthetic_score = Column(Integer, default=0)
    reading_score = Column(Integer, default=0)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", backref="assessments")