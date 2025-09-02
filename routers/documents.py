import os
import json
import re
import asyncio
import shutil
import time
from pathlib import Path
from fastapi import HTTPException, APIRouter, UploadFile, File, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from openai import AsyncOpenAI
from dotenv import load_dotenv
from PyPDF2 import PdfReader

from database import SessionLocal, get_db
from models.document import Document, ProcessingStatus
from models.quiz import Quiz
from dependencies import get_current_active_user
from config import settings

# Load environment variables from .env file
load_dotenv()

print("Documents router loading...")

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class DocumentService:
    @staticmethod
    async def process_document(document_id: int):
        """Background task: extract text, generate summary, topics, and quiz for a document."""
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                print(f"Document {document_id} not found")
                return

            # Update status to processing
            document.processing_status = ProcessingStatus.PROCESSING
            db.commit()

            # Extract text from PDF
            text_content = DocumentService.extract_pdf_text(document.file_path)
            if not text_content:
                raise Exception("Failed to extract text from PDF")

            document.content = text_content
            document.page_count = DocumentService.get_pdf_page_count(document.file_path)
            db.commit()

            # Generate summary + topics
            summary, key_topics = await DocumentService.generate_summary_and_topics(text_content)

            # Generate quiz
            quiz_questions = await DocumentService.generate_quiz_questions(text_content)

            # Save back to DB
            document.summary = summary
            document.key_topics = key_topics
            document.processing_status = ProcessingStatus.COMPLETED
            document.processed_at = func.now()
            
            print(f"Generated {len(quiz_questions)} quiz questions")
            for q in quiz_questions:
                quiz = Quiz(
                    document_id=document.id,
                    question=q["question"],
                    options=json.dumps(q["options"]) if q.get("options") else None,
                    correct_answer=q["answer"],
                    explanation=q.get("explanation", "")
                )
                db.add(quiz)

            db.commit()
            db.refresh(document)
            print(f"Document {document_id} processing completed")

        except Exception as e:
            db.rollback()
            # Update status to failed
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.processing_status = ProcessingStatus.FAILED
                db.commit()
            print(f"Error in process_document {document_id}: {str(e)}")
        finally:
            db.close()

    @staticmethod
    def extract_pdf_text(file_path: str) -> str:
        """Extract text content from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""

    @staticmethod
    def get_pdf_page_count(file_path: str) -> int:
        """Get number of pages in PDF"""
        try:
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                return len(reader.pages)
        except Exception as e:
            print(f"Error getting PDF page count: {e}")
            return 0

    @staticmethod
    async def generate_summary_and_topics(text: str):
        prompt = f"""
        Analyze the following educational text and provide:
        1. A concise summary (2-3 paragraphs)
        2. Key topics covered as a JSON array

        Format your response as:
        SUMMARY:
        [Your summary here]

        KEY_TOPICS:
        ["topic1", "topic2", "topic3"]

        Text:
        {text[:4000]}
        """

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert educational content analyzer."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
                temperature=0.3,
            )

            content = response.choices[0].message.content
            
            summary = ""
            key_topics = []
            
            try:
                if "SUMMARY:" in content and "KEY_TOPICS:" in content:
                    parts = content.split("KEY_TOPICS:")
                    summary = parts[0].replace("SUMMARY:", "").strip()
                    
                    # Extract JSON array from topics section
                    topics_text = parts[1].strip()
                    topics_match = re.search(r'\[(.*?)\]', topics_text, re.DOTALL)
                    if topics_match:
                        topics_json = f"[{topics_match.group(1)}]"
                        key_topics = json.loads(topics_json)
                else:
                    summary = content.strip()
            except Exception as parse_error:
                print(f"Error parsing AI response: {parse_error}")
                summary = content.strip()

            return summary, key_topics
        
        except Exception as e:
            print(f"Error generating summary: {e}")
            return "Summary generation failed", []

    @staticmethod
    async def generate_quiz_questions(text: str):
        prompt = f"""
        Create 5 multiple choice quiz questions based on this text. 
        Return the output in **valid JSON** format only.
        JSON format:
        [
          {{
            "question": "string",
            "options": {{"A": "option1", "B": "option2", "C": "option3", "D": "option4"}},
            "answer": "A",
            "explanation": "Brief explanation why this is correct"
          }}
        ]

        Text:
        {text[:3000]}
        """

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert quiz generator. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1200,
                temperature=0.5,
            )

            raw_output = response.choices[0].message.content.strip()

            # Clean up common JSON formatting issues
            raw_output = re.sub(r'^```json\s*', '', raw_output)
            raw_output = re.sub(r'\s*```$', '', raw_output)

            try:
                # Direct JSON parse
                return json.loads(raw_output)
            except json.JSONDecodeError:
                # Try to extract JSON with regex
                match = re.search(r'\[.*\]', raw_output, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except Exception:
                        pass
                print(f"Raw AI output (invalid JSON): {raw_output}")
                return []
                
        except Exception as e:
            print(f"Error generating quiz: {e}")
            return []


# Background task wrapper
def process_document_background(document_id: int):
    try:
        asyncio.run(DocumentService.process_document(document_id))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(DocumentService.process_document(document_id))


# Create router instance
router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Upload a document for processing."""
    try:
        print(f"Received file upload: {file.filename}")
        
        # Validate file type
        if not file.content_type == "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Create unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{current_user.id}_{int(time.time())}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_DIRECTORY, "documents", unique_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Create document record
        document = Document(
            user_id=current_user.id,
            filename=file.filename,
            original_name=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type,
            processing_status=ProcessingStatus.PENDING
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        print(f"Created document with ID: {document.id}")
        
        # Add background task
        background_tasks.add_task(process_document_background, document.id)
        
        return document.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in upload_document: {str(e)}")
        db.rollback()
        # Clean up file if it was created
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/")
async def get_documents(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get all documents for the current user."""
    try:
        documents = db.query(Document).filter(Document.user_id == current_user.id).all()
        return [doc.to_dict() for doc in documents]
    except Exception as e:
        print(f"Error getting documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve documents")


@router.get("/{document_id}")
async def get_document(
    document_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get a specific document."""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")


# In your documents router, update the status endpoint
@router.get("/{document_id}/status")
async def get_document_status(
    document_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get document processing status."""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "status": document.processing_status.value,
            "processing_complete": document.processing_status == ProcessingStatus.COMPLETED,
            "processed_at": document.processed_at.isoformat() if document.processed_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting document status {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document status")
    
@router.delete("/{document_id}")
async def delete_document(
    document_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Delete a document."""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete associated quizzes
        db.query(Quiz).filter(Quiz.document_id == document_id).delete()
        
        # Delete file from filesystem
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete document record
        db.delete(document)
        db.commit()
        
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting document {document_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get("/{document_id}/summary")
async def get_document_summary(
    document_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get document summary."""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not document.summary:
            if document.processing_status == ProcessingStatus.PROCESSING:
                return {"summary": "Summary is being generated. Please wait..."}
            elif document.processing_status == ProcessingStatus.FAILED:
                return {"summary": "Summary generation failed. Please try re-uploading the document."}
            else:
                return {"summary": "Summary not yet available. Document may still be processing."}
            
        return {
            "summary": document.summary,
            "key_topics": document.key_topics or []
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting summary for document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve summary")


print("Documents router loaded successfully")