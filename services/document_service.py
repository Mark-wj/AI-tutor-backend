import json, re, asyncio
from fastapi import HTTPException
from sqlalchemy.orm import Session
from openai import AsyncOpenAI
from database import SessionLocal
from models.document import Document
from models.quiz import Quiz
import os

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # use lightweight model
            messages=[
                {"role": "system", "content": "You are an expert educational content analyzer."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.7,
        )

        content = response.choices[0].message.content
        summary, key_topics = "", []

        if "Key topics:" in content:
            parts = content.split("Key topics:")
            summary = parts[0].replace("Summary:", "").strip()
            key_topics = [t.strip("-• \n") for t in parts[1].split("\n") if t.strip()]
        else:
            summary = content.strip()

        return summary, key_topics

    @staticmethod
    async def generate_quiz_questions(text: str):
        prompt = f"""
        Create 5 multiple choice quiz questions based on this text. 
        Return valid JSON in this format only:
        [
          {{
            "question": "string",
            "options": ["A", "B", "C", "D"],
            "answer": "string"
          }}
        ]

        Text:
        {text[:3000]}
        """

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert quiz generator."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=700,
            temperature=0.7,
        )

        raw_output = response.choices[0].message.content.strip()
        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", raw_output, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            print("❌ Raw AI output:", raw_output)
            raise HTTPException(status_code=500, detail="AI response not valid JSON")

# Wrapper for background tasks
def process_document_background(document_id: int):
    try:
        asyncio.run(DocumentService.process_document(document_id))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(DocumentService.process_document(document_id))
