from models.user import User
from utils.security import get_password_hash
from database import SessionLocal
from models.document import Document  # <-- Import so SQLAlchemy can resolve relationships


db = SessionLocal()
user = db.query(User).filter(User.id == 1).first()
if user:
    user.password_hash = get_password_hash("spizzoH23.")
    db.commit()
    print("Password reset successfully")
else:
    print("User not found")