from sqlalchemy.orm import Session
from models.quiz import Quiz, Question, QuizAttempt
from models.assessment import LearningAssessment
from models.document import Document
from schemas.quiz import QuizCreate, QuizAttemptCreate, QuizAttemptResponse
from services.ai_service import AIService
from fastapi import HTTPException, status
from datetime import datetime
from typing import List, Dict

class QuizService:
    
    @staticmethod
    async def generate_quiz(db: Session, quiz_data: QuizCreate, user_id: int) -> Quiz:
        # Get document
        document = db.query(Document).filter(
            Document.id == quiz_data.document_id,
            Document.user_id == user_id
        ).first()
        
        if not document or not document.extracted_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document not found or not processed"
            )
        
        # Get user's learning style
        assessment = db.query(LearningAssessment).filter(
            LearningAssessment.user_id == user_id
        ).order_by(LearningAssessment.completed_at.desc()).first()
        
        learning_style = assessment.learning_style_result if assessment else "reading"
        
        # Create quiz
        db_quiz = Quiz(
            document_id=quiz_data.document_id,
            user_id=user_id,
            title=quiz_data.title,
            description=quiz_data.description
        )
        
        db.add(db_quiz)
        db.commit()
        db.refresh(db_quiz)
        
        # Generate questions using AI
        questions_data = await AIService.generate_quiz_questions(
            document.extracted_text, 
            learning_style
        )
        
        # Create question objects
        for i, question_data in enumerate(questions_data):
            db_question = Question(
                quiz_id=db_quiz.id,
                question_text=question_data["question_text"],
                question_type=question_data["question_type"],
                correct_answer=question_data["correct_answer"],
                options=question_data.get("options"),
                explanation=question_data.get("explanation"),
                difficulty_level=question_data["difficulty_level"],
                order_index=i
            )
            db.add(db_question)
        
        # Update total questions count
        db_quiz.total_questions = len(questions_data)
        
        db.commit()
        db.refresh(db_quiz)
        
        return db_quiz
    
    @staticmethod
    def get_user_quizzes(db: Session, user_id: int):
        return db.query(Quiz).filter(Quiz.user_id == user_id, Quiz.is_active == True).all()
    
    @staticmethod
    def get_quiz(db: Session, quiz_id: int, user_id: int):
        quiz = db.query(Quiz).filter(
            Quiz.id == quiz_id,
            Quiz.user_id == user_id,
            Quiz.is_active == True
        ).first()
        
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        return quiz
    
    @staticmethod
    def submit_quiz_attempt(db: Session, quiz_id: int, user_id: int, attempt_data: QuizAttemptCreate) -> QuizAttemptResponse:
        quiz = QuizService.get_quiz(db, quiz_id, user_id)
        
        # Get quiz questions
        questions = db.query(Question).filter(Question.quiz_id == quiz_id).all()
        
        # Calculate score
        correct_answers = 0
        total_questions = len(questions)
        
        for question in questions:
            user_answer = attempt_data.answers.get(str(question.id))
            if user_answer and user_answer.lower().strip() == question.correct_answer.lower().strip():
                correct_answers += 1
        
        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        # Create quiz attempt
        db_attempt = QuizAttempt(
            quiz_id=quiz_id,
            user_id=user_id,
            answers=attempt_data.answers,
            score=score,
            total_questions=total_questions,
            correct_answers=correct_answers,
            completed_at=datetime.utcnow()
        )
        
        db.add(db_attempt)
        db.commit()
        db.refresh(db_attempt)
        
        return db_attempt