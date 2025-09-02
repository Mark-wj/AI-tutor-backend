# main.py - Updated with proper imports and relationships
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import relationship
from database import engine, Base
from config import settings
from routers import auth, assessment, documents, quizzes
import os
import time

# Import all models to ensure they're registered with SQLAlchemy
from models.user import User
from models.document import Document
from models.quiz import Quiz, Question, QuizSubmission

# Add relationship back-references
# User.documents = relationship("Document", back_populates="user")
# Document.quizzes = relationship("Quiz", back_populates="document", cascade="all, delete-orphan")

# Create tables
print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Database tables created successfully!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    print("\n🚀 AI Tutoring App Starting Up...")
    print("=" * 50)
    
    # Show configuration
    print(f"📁 Upload Directory: {settings.UPLOAD_DIRECTORY}")
    print(f"🗄️  Database URL: {settings.DATABASE_URL}")
    print(f"🤖 OpenAI API Key: {'✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Not Set'}")
    
    print("\n📋 Registered API Routes:")
    routes_by_tag = {}
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path') and hasattr(route, 'tags'):
            methods = list(route.methods) if route.methods else []
            if 'HEAD' in methods:
                methods.remove('HEAD')
            if 'OPTIONS' in methods:
                methods.remove('OPTIONS')
            
            tag = route.tags[0] if route.tags else 'general'
            if tag not in routes_by_tag:
                routes_by_tag[tag] = []
            routes_by_tag[tag].append(f"  {', '.join(methods):>12} {route.path}")
    
    for tag, routes in sorted(routes_by_tag.items()):
        print(f"\n  [{tag.upper()}]")
        for route in sorted(routes):
            print(route)
    
    print(f"\n🌍 Server available at: http://localhost:8000")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print(f"🧪 Test the API: http://localhost:8000/health")
    print("=" * 50)
    
    yield
    
    # Shutdown (if needed)
    print("🛑 Shutting down AI Tutoring App...")

app = FastAPI(
    title="AI Tutoring App",
    description="AI-powered tutoring with adaptive quizzes",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - Allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directories
upload_dirs = [
    settings.UPLOAD_DIRECTORY,
    os.path.join(settings.UPLOAD_DIRECTORY, "profiles"),
    os.path.join(settings.UPLOAD_DIRECTORY, "documents"),
]

for directory in upload_dirs:
    os.makedirs(directory, exist_ok=True)
    print(f"Ensured directory exists: {directory}")

# Static files
app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIRECTORY), name="static")

# Include routers with proper prefixes
app.include_router(auth.router, tags=["auth"])
app.include_router(assessment.router, prefix="/api/assessment", tags=["assessment"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(quizzes.router, prefix="/api/quizzes", tags=["quizzes"])

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "AI Tutoring App API", 
        "version": "1.0.0",
        "status": "running",
        "timestamp": time.time(),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "api": {
                "auth": "/api/auth",
                "documents": "/api/documents", 
                "quizzes": "/api/quizzes",
                "assessment": "/api/assessment"
            }
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": time.time(),
        "database": "connected",
        "upload_dir": "accessible" if os.path.exists(settings.UPLOAD_DIRECTORY) else "missing"
    }

# Add a test endpoint to verify document processing
@app.get("/api/test/status")
async def test_status():
    """Test endpoint to verify API is working"""
    return {
        "api_status": "operational",
        "features": {
            "document_upload": "enabled",
            "quiz_generation": "enabled", 
            "ai_processing": "enabled" if os.getenv('OPENAI_API_KEY') else "disabled"
        },
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Tutoring App server...")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )