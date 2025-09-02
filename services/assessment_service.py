from sqlalchemy.orm import Session
from models.assessment import LearningAssessment
from schemas.assessment import AssessmentSubmission
from typing import List, Dict

class AssessmentService:
    
    @staticmethod
    def get_assessment_questions() -> List[Dict]:
        """Return predefined assessment questions"""
        return [
            {
                "id": 1,
                "question": "When learning something new, I prefer to:",
                "options": [
                    "Read about it in detail",
                    "Watch a demonstration",
                    "Listen to someone explain it",
                    "Try it hands-on immediately"
                ],
                "category": "learning_preference"
            },
            {
                "id": 2,
                "question": "I remember information best when:",
                "options": [
                    "I see it written down or in diagrams",
                    "I hear it explained verbally",
                    "I write notes or summaries",
                    "I practice or apply it physically"
                ],
                "category": "memory_style"
            },
            {
                "id": 3,
                "question": "When solving problems, I tend to:",
                "options": [
                    "Draw diagrams or charts",
                    "Talk through the problem aloud",
                    "Write out the steps carefully",
                    "Jump in and experiment"
                ],
                "category": "problem_solving"
            },
            {
                "id": 4,
                "question": "In a classroom, I learn best when:",
                "options": [
                    "There are visual aids and presentations",
                    "There's group discussion",
                    "I can take detailed notes",
                    "There are hands-on activities"
                ],
                "category": "classroom_preference"
            },
            {
                "id": 5,
                "question": "I prefer to study:",
                "options": [
                    "Using highlighted texts and colorful materials",
                    "In quiet environments where I can focus",
                    "By reading and rereading materials",
                    "By moving around or using manipulatives"
                ],
                "category": "study_environment"
            }
        ]
    
    @staticmethod
    def calculate_learning_style(responses: List[Dict]) -> Dict:
        """Calculate learning style based on responses"""
        scores = {
            "visual": 0,
            "auditory": 0,
            "reading": 0,
            "kinesthetic": 0
        }
        
        # Simple scoring logic based on answer patterns
        for response in responses:
            answer = response["answer"]
            if "visual" in answer.lower() or "see" in answer.lower() or "diagram" in answer.lower():
                scores["visual"] += 1
            elif "hear" in answer.lower() or "listen" in answer.lower() or "discussion" in answer.lower():
                scores["auditory"] += 1
            elif "read" in answer.lower() or "write" in answer.lower() or "notes" in answer.lower():
                scores["reading"] += 1
            elif "hands-on" in answer.lower() or "practice" in answer.lower() or "physical" in answer.lower():
                scores["kinesthetic"] += 1
        
        # Determine primary learning style
        primary_style = max(scores, key=scores.get)
        
        return {
            "learning_style_result": primary_style,
            "visual_score": scores["visual"],
            "auditory_score": scores["auditory"],
            "reading_score": scores["reading"],
            "kinesthetic_score": scores["kinesthetic"]
        }
    
    @staticmethod
    def submit_assessment(db: Session, user_id: int, submission: AssessmentSubmission) -> LearningAssessment:
        # Calculate learning style
        style_data = AssessmentService.calculate_learning_style(submission.responses)
        
        # Create assessment record
        db_assessment = LearningAssessment(
            user_id=user_id,
            assessment_data={"responses": [r.dict() for r in submission.responses]},
            learning_style_result=style_data["learning_style_result"],
            visual_score=style_data["visual_score"],
            auditory_score=style_data["auditory_score"],
            kinesthetic_score=style_data["kinesthetic_score"],
            reading_score=style_data["reading_score"]
        )
        
        db.add(db_assessment)
        db.commit()
        db.refresh(db_assessment)
        
        return db_assessment