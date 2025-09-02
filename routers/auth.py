# auth.py - Updated login endpoint to accept JSON

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
from schemas.user import UserCreate, UserResponse, UserUpdate, Token
from services.auth_service import AuthService
from utils.security import create_access_token, create_refresh_token
from dependencies import get_current_active_user
from models.user import User
from utils.file_handler import save_file
from config import settings
import os
from datetime import timedelta
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Create a Pydantic model for login
class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    return AuthService.create_user(db, user_data)

# Updated login endpoint to accept JSON
@router.post("/login")
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):  # Changed LoginSchema to LoginRequest
    user = AuthService.authenticate_user(db, login_data.email, login_data.password)
    
    # Check if authentication failed
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)  # Fixed variable name
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Alternative: Keep OAuth2 form login for compatibility but add JSON endpoint
@router.post("/login/oauth2")
async def login_oauth2(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 compatible login endpoint for form data"""
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user.to_dict()
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/upload-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )
    
    # Create upload directory
    upload_dir = os.path.join(settings.UPLOAD_DIRECTORY, "profiles", str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_extension = file.filename.split(".")[-1]
    filename = f"profile.{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    await save_file(file, file_path)
    
    # Update user profile
    current_user.profile_photo_path = file_path
    db.commit()
    
    return {"message": "Profile photo uploaded successfully", "file_path": file_path}