from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserCreate
from utils.security import get_password_hash, verify_password
from fastapi import HTTPException, status

class AuthService:
    
    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        print(f"[DEBUG REGISTRATION] Email: {user_data.email}")
        print(f"[DEBUG REGISTRATION] Password length: {len(user_data.password)}")
        print(f"[DEBUG REGISTRATION] Hash length: {len(hashed_password)}")
        print(f"[DEBUG REGISTRATION] Hash starts with: {hashed_password[:20]}...")
        
        db_user = User(
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            password_hash=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        print(f"[DEBUG REGISTRATION] User created with ID: {db_user.id}")
        return db_user

    @staticmethod
    def debug_password_hash(password: str, stored_hash: str):
        """Debug function to test password hashing"""
        print(f"[DEBUG HASH] Testing password: '{password}'")
        print(f"[DEBUG HASH] Against hash: '{stored_hash}'")
        
        # Generate a new hash for the same password
        new_hash = get_password_hash(password)
        print(f"[DEBUG HASH] Newly generated hash: '{new_hash}'")
        
        # Test verification with the new hash
        new_verification = verify_password(password, new_hash)
        print(f"[DEBUG HASH] New hash verification: {new_verification}")
        
        # Test verification with the stored hash
        stored_verification = verify_password(password, stored_hash)
        print(f"[DEBUG HASH] Stored hash verification: {stored_verification}")
        
        return stored_verification

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User:
        print(f"[DEBUG LOGIN] Attempting to authenticate: {email}")
        
        email = email.strip().lower()
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"[DEBUG LOGIN] User not found for email: {email}")
            return None
        
        print(f"[DEBUG LOGIN] User found: {user.id}")
        
        # Debug password hashing
        AuthService.debug_password_hash(password, user.password_hash)
        
        # Check password
        password_valid = verify_password(password, user.password_hash)
        print(f"[DEBUG LOGIN] Final verification result: {password_valid}")
        
        if password_valid:
            return user
        else:
            print(f"[DEBUG LOGIN] Password verification failed")
            return None
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User:
        return db.query(User).filter(User.email == email).first()