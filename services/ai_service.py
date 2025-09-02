from typing import List, Dict, Any
from config import settings
from models.quiz import QuestionType, DifficultyLevel
import json
from openai import AsyncOpenAI

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

class AIService:
    
    @staticmethod
    async def generate_summary(text: str) -> Dict[str, Any]:
        try:
            # First: generate summary
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educational content summarizer. Create concise, informative summaries that highlight key concepts and learning objectives."
                    },
                    {
                        "role": "user",
                        "content": f"Please provide a comprehensive summary of the following educational content, including key topics and main concepts:\n\n{text[:4000]}"
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Second: extract key topics
            topics_response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Extract 5-7 key topics from the given text. Return as a JSON array of strings."
                    },
                    {
                        "role": "user",
                        "content": f"Extract key topics from: {text[:2000]}"
                    }
                ],
                max_tokens=200,
                temperature=0.2
            )
            
            try:
                key_topics = json.loads(topics_response.choices[0].message.content.strip())
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
            
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an expert educational content creator. Generate {num_questions} quiz questions based on the provided content.
                        
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
                        """
                    },
                    {
                        "role": "user",
                        "content": f"Generate quiz questions based on this content:\n\n{text[:3000]}"
                    }
                ],
                max_tokens=2000,
                temperature=0.4
            )
            
            questions_json = response.choices[0].message.content.strip()
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
