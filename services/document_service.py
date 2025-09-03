import json, re, asyncio
from fastapi import HTTPException
from sqlalchemy.orm import Session
from huggingface_hub import AsyncInferenceClient  # Changed import
from database import SessionLocal
from models.document import Document
from models.quiz import Quiz
import os

# Initialize Hugging Face client
client = AsyncInferenceClient(token=os.getenv("HUGGINGFACEHUB_API_TOKEN"))  # Changed client

class DocumentService:
    @staticmethod
    async def process_document(document_id: int):
        """Background task: generate summary, topics, and quiz for a document."""
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")

            text = document.content[:4000]  

            summary, key_topics = await DocumentService.generate_summary_and_topics(text)
            quiz_questions = await DocumentService.generate_quiz_questions(text)

            document.summary = summary
            document.key_topics = key_topics
            for q in quiz_questions:
                db.add(Quiz(
                    document_id=document.id,
                    question=q["question"],
                    options=q["options"],
                    answer=q["answer"]
                ))

            db.commit()
            db.refresh(document)

        except Exception as e:
            db.rollback()
            print("❌ Error in process_document:", str(e))
            raise
        finally:
            db.close()

    @staticmethod
    async def generate_summary_and_topics(text: str):
        prompt = f"""
        Analyze the following educational text and provide:
        1. A concise summary
        2. Key topics covered as a list

        Text:
        {text}
        """

        try:
            # Using Hugging Face text generation
            response = await client.text_generation(
                prompt=prompt,
                model="mistralai/Mistral-7B-Instruct-v0.2",  # Using a suitable model
                max_new_tokens=500,
                temperature=0.7,
            )

            content = response
            summary, key_topics = "", []

            if "Key topics:" in content:
                parts = content.split("Key topics:")
                summary = parts[0].replace("Summary:", "").strip()
                key_topics = [t.strip("-• \n") for t in parts[1].split("\n") if t.strip()]
            else:
                summary = content.strip()

            return summary, key_topics
        
        except Exception as e:
            print(f"Error generating summary and topics: {e}")
            return "Summary generation failed", []

    @staticmethod
    async def generate_quiz_questions(text: str):
        try:
            # Using Hugging Face's quiz generator model :cite[1]:cite[9]
            response = await client.text_generation(
                prompt=f"Generate quiz questions from: {text[:3000]}",
                model="koshkosh/quiz-generator",  # Specific quiz generation model
                max_new_tokens=700,
                temperature=0.7,
            )

            raw_output = response.strip()
            try:
                return json.loads(raw_output)
            except json.JSONDecodeError:
                match = re.search(r"\[.*\]", raw_output, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                print("❌ Raw AI output:", raw_output)
                raise HTTPException(status_code=500, detail="AI response not valid JSON")
        
        except Exception as e:
            print(f"Error generating quiz questions: {e}")
            raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")

# Wrapper for background tasks (unchanged)
def process_document_background(document_id: int):
    try:
        asyncio.run(DocumentService.process_document(document_id))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(DocumentService.process_document(document_id))