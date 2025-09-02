from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas.assessment import AssessmentQuestion, AssessmentSubmission, AssessmentResult
from services.assessment_service import AssessmentService
from dependencies import get_current_active_user
from models.user import User
from models.assessment import LearningAssessment
from typing import List

router = APIRouter(prefix="/api/assessment", tags=["assessment"])

@router.get("/questions", response_model=List[AssessmentQuestion])
async def get_assessment_questions():
    return AssessmentService.get_assessment_questions()

@router.post("/submit", response_model=AssessmentResult)
async def submit_assessment(
    submission: AssessmentSubmission,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    assessment = AssessmentService.submit_assessment(db, current_user.id, submission)
    return assessment

@router.get("/result", response_model=AssessmentResult)
async def get_assessment_result(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    assessment = db.query(LearningAssessment).filter(
        LearningAssessment.user_id == current_user.id
    ).order_by(LearningAssessment.completed_at.desc()).first()
    
    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="No assessment found. Please take the assessment first."
        )
    
    return assessment