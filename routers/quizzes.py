import os
import json
from typing import List, Optional
from fastapi import HTTPException, APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from huggingface_hub import AsyncInferenceClient
# from openai import AsyncOpenAI
from dotenv import load_dotenv

from database import get_db
from models.document import Document
from models.quiz import Quiz, Question, QuizSubmission, DifficultyLevel, QuestionType
from dependencies import get_current_active_user

# Load environment variables
load_dotenv()

print("Quizzes router loading...")

# Initialize OpenAI client
client = AsyncInferenceClient(token=os.getenv("HUGGINGFACEHUB_API_TOKEN"))

# Pydantic models
class QuizGenerateRequest(BaseModel):
    documentId: str
    options: Optional[dict] = None

class QuizAnswerRequest(BaseModel):
    questionId: str
    answer: str
    isCorrect: bool

class QuizSubmissionRequest(BaseModel):
    answers: List[QuizAnswerRequest]

class QuizService:
    @staticmethod
    async def generate_quiz_from_document(document: Document, difficulty: str = "medium", question_count: int = 10):
        """Generate a quiz from document content using AI"""
        if not document.content:
            raise HTTPException(status_code=400, detail="Document content not available")

        try:
            # Create quiz record first
            quiz_title = f"Quiz: {document.filename[:50]}{'...' if len(document.filename) > 50 else ''}"
            quiz = Quiz(
                document_id=document.id,
                title=quiz_title,
                description=f"Auto-generated quiz from {document.filename}",
                difficulty=DifficultyLevel(difficulty),
                estimated_duration=max(5, question_count * 2)  # 2 minutes per question minimum
            )
            
            # Generate questions using Hugging Face AI
            questions_data = await QuizService._generate_questions_ai(
                document.content, difficulty, question_count
            )
            
            if not questions_data:
                raise HTTPException(status_code=500, detail="Failed to generate quiz questions")
            
            # Create question records
            questions = []
            for i, q_data in enumerate(questions_data):
                question = Question(
                    question_text=q_data.get("question", ""),
                    question_type=QuestionType.MULTIPLE_CHOICE,
                    options=q_data.get("options", {}),
                    correct_answer=q_data.get("answer", ""),
                    explanation=q_data.get("explanation", ""),
                    order_index=i
                )
                questions.append(question)
            
            quiz.questions = questions
            return quiz
            
        except Exception as e:
            print(f"Error generating quiz: {e}")
            raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")

    @staticmethod
    async def _generate_questions_ai(content: str, difficulty: str, count: int) -> List[dict]:
        """Generate questions using Hugging Face AI"""
        difficulty_prompts = {
            "easy": "Focus on basic comprehension and recall questions.",
            "medium": "Create questions requiring understanding and application of concepts.",
            "hard": "Generate questions requiring critical thinking, analysis, and synthesis."
        }
        
        prompt = f"""
        Generate {count} multiple choice quiz questions from the following content.
        Difficulty level: {difficulty} - {difficulty_prompts.get(difficulty, "")}
        
        Return a valid JSON array with this exact format:
        [
          {{
            "question": "Clear, specific question text?",
            "options": {{"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"}},
            "answer": "A",
            "explanation": "Brief explanation of why this answer is correct"
          }}
        ]
        
        Guidelines:
        - Make questions specific and test understanding, not just memorization
        - Ensure all options are plausible
        - Vary question types (definition, application, analysis)
        - Keep questions concise but comprehensive
        
        Content:
        {content[:4000]}
        """

        try:
            response = await client.text_generation(
                prompt=prompt,
                model="koshkosh/quiz-generator",  # Using quiz generator model :cite[1]:cite[9]
                max_new_tokens=2000,
                temperature=0.7
            )

            raw_output = response.strip()
            
            # Clean up JSON formatting
            raw_output = raw_output.replace('```json', '').replace('```', '').strip()
            
            try:
                questions = json.loads(raw_output)
                
                # Validate structure
                valid_questions = []
                for q in questions:
                    if all(key in q for key in ["question", "options", "answer"]):
                        valid_questions.append(q)
                
                return valid_questions[:count]  # Ensure we don't exceed requested count
                
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Raw output: {raw_output}")
                return []

        except Exception as e:
            print(f"AI generation error: {e}")
            return []

    @staticmethod
    def calculate_score(quiz: Quiz, answers: List[QuizAnswerRequest]) -> int:
        """Calculate quiz score as percentage"""
        if not quiz.questions or not answers:
            return 0
        
        correct_count = 0
        total_questions = len(quiz.questions)
        
        # Create a map of question_id to correct_answer
        correct_answers = {str(q.id): q.correct_answer for q in quiz.questions}
        
        for answer in answers:
            if answer.questionId in correct_answers:
                if answer.answer == correct_answers[answer.questionId]:
                    correct_count += 1
        
        return int((correct_count / total_questions) * 100) if total_questions > 0 else 0

# Create router instance
router = APIRouter()

@router.get("/")
async def get_quizzes(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get all quizzes for the current user."""
    try:
        quizzes = db.query(Quiz).join(Document).filter(
            Document.user_id == current_user.id
        ).all()
        return [quiz.to_dict() for quiz in quizzes]
    except Exception as e:
        print(f"Error getting quizzes: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve quizzes")

@router.post("/generate")
async def generate_quiz(
    request: QuizGenerateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Generate a new quiz from a document."""
    try:
        # Get the document
        document = db.query(Document).filter(
            Document.id == int(request.documentId),
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.processing_status.value != "processed":
            raise HTTPException(
                status_code=400, 
                detail="Document must be fully processed before generating quiz"
            )
        
        # Extract options
        options = request.options or {}
        difficulty = options.get("difficulty", "medium")
        question_count = min(options.get("questionCount", 10), 50)  # Max 50 questions
        
        # Generate quiz
        quiz = await QuizService.generate_quiz_from_document(
            document, difficulty, question_count
        )
        
        # Save to database
        db.add(quiz)
        db.commit()
        db.refresh(quiz)
        
        return quiz.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating quiz: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")

@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get a specific quiz."""
    try:
        quiz = db.query(Quiz).join(Document).filter(
            Quiz.id == quiz_id,
            Document.user_id == current_user.id
        ).first()
        
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        return quiz.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting quiz {quiz_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve quiz")

@router.post("/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: int,
    request: QuizSubmissionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Submit quiz answers and get results."""
    try:
        # Get the quiz
        quiz = db.query(Quiz).join(Document).filter(
            Quiz.id == quiz_id,
            Document.user_id == current_user.id
        ).first()
        
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        # Calculate score
        score = QuizService.calculate_score(quiz, request.answers)
        
        # Create submission record
        submission = QuizSubmission(
            quiz_id=quiz_id,
            user_id=current_user.id,
            answers=[answer.dict() for answer in request.answers],
            score=score,
            time_spent=None  # TODO: Add time tracking from frontend
        )
        
        db.add(submission)
        db.commit()
        db.refresh(submission)
        
        return submission.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error submitting quiz {quiz_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to submit quiz")

@router.get("/{quiz_id}/submissions")
async def get_quiz_submissions(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get all submissions for a quiz by the current user."""
    try:
        # Verify quiz ownership
        quiz = db.query(Quiz).join(Document).filter(
            Quiz.id == quiz_id,
            Document.user_id == current_user.id
        ).first()
        
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        submissions = db.query(QuizSubmission).filter(
            QuizSubmission.quiz_id == quiz_id,
            QuizSubmission.user_id == current_user.id
        ).order_by(QuizSubmission.completed_at.desc()).all()
        
        return [submission.to_dict() for submission in submissions]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting submissions for quiz {quiz_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve submissions")

@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Delete a quiz."""
    try:
        # Verify quiz ownership
        quiz = db.query(Quiz).join(Document).filter(
            Quiz.id == quiz_id,
            Document.user_id == current_user.id
        ).first()
        
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        # Delete quiz (cascade will handle questions and submissions)
        db.delete(quiz)
        db.commit()
        
        return {"message": "Quiz deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting quiz {quiz_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete quiz")

print("Quizzes router loaded successfully")