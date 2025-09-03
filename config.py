from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    
    # Hugging Face
    HUGGINGFACEHUB_API_TOKEN: Optional[str] = None   # 👈 added
    
    # File Storage
    UPLOAD_DIRECTORY: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["pdf"]
    
    # Redis (optional)
    REDIS_URL: Optional[str] = None
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080"
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
