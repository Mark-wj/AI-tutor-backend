from typing import List, Dict, Any
from config import settings
from models.quiz import QuestionType, DifficultyLevel
import json
from huggingface_hub import AsyncInferenceClient  

# Initialize Hugging Face client
client = AsyncInferenceClient(token=settings.HUGGINGFACEHUB_API_TOKEN)  # Changed client

class AIService:
    
    @staticmethod
    async def generate_summary(text: str) -> Dict[str, Any]:
        try:
            # Generate summary using Hugging Face
            response = await client.text_generation(
                prompt=f"Please provide a comprehensive summary of the following educational content, including key topics and main concepts:\n\n{text[:4000]}",
                model="mistralai/Mistral-7B-Instruct-v0.2",
                max_new_tokens=500,
                temperature=0.3
            )
            
            summary = response.strip()
            
            # Extract key topics
            topics_response = await client.text_generation(
                prompt=f"Extract 5-7 key topics from the given text. Return as a JSON array of strings:\n\n{text[:2000]}",
                model="mistralai/Mistral-7B-Instruct-v0.2",
                max_new_tokens=200,
                temperature=0.2
            )
            
            try:
                key_topics = json.loads(topics_response.strip())
            except:
                key_topics = ["Topic analysis unavailable"]
            
            return {
                "summary": summary,
                "word_count": len(text.split()),
                "key_topics": key_topics
            }
            
        except Exception as e:
            return {
                "summary": "Summary generation failed. Please try again later.",
                "word_count": len(text.split()),
                "key_topics": ["Analysis unavailable"],
                "error": str(e)
            }
    
    @staticmethod
    async def generate_quiz_questions(text: str, learning_style: str, num_questions: int = 10) -> List[Dict]:
        try:
            learning_style_prompt = {
                "visual": "Focus on questions that can be answered by understanding diagrams, charts, or visual representations of concepts.",
                "auditory": "Create questions that focus on explanations, discussions, and verbal understanding of concepts.",
                "kinesthetic": "Generate practical, hands-on questions that relate to real-world applications and problem-solving.",
                "reading": "Focus on text-based comprehension and written analysis questions."
            }
            
            style_instruction = learning_style_prompt.get(learning_style.lower(), learning_style_prompt["reading"])
            
            prompt = f"""You are an expert educational content creator. Generate {num_questions} quiz questions based on the provided content.
                        
                        Learning style adaptation: {style_instruction}
                        
                        Return a JSON array of questions with this exact format:
                        [
                            {{
                                "question_text": "Question here?",
                                "question_type": "multiple_choice",
                                "correct_answer": "A",
                                "options": {{"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"}},
                                "explanation": "Explanation of the correct answer",
                                "difficulty_level": "medium"
                            }}
                        ]
                        
                        Question types: multiple_choice, true_false, short_answer
                        Difficulty levels: easy, medium, hard
                        
                        Generate quiz questions based on this content:
                        {text[:3000]}
                        """
            
            response = await client.text_generation(
                prompt=prompt,
                model="koshkosh/quiz-generator",  # Using quiz generator model :cite[1]:cite[9]
                max_new_tokens=2000,
                temperature=0.4
            )
            
            questions_json = response.strip()
            questions = json.loads(questions_json)
            return questions
            
        except Exception as e:
            # Return fallback questions if AI generation fails
            return [
                {
                    "question_text": "What is the main topic discussed in the provided content?",
                    "question_type": "short_answer",
                    "correct_answer": "Main topic analysis",
                    "options": None,
                    "explanation": "This question tests comprehension of the main topic.",
                    "difficulty_level": "medium",
                    "error": str(e)
                }
            ]