import sys
import os

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.database import SessionLocal, UserDB, engine, Base
from modules.security import get_password_hash

def create_admin_user():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    username = "admin"
    password = "password123"
    
    # Check if exists
    existing_user = db.query(UserDB).filter(UserDB.username == username).first()
    if existing_user:
        print(f"User '{username}' already exists.")
        return

    hashed_pw = get_password_hash(password)
    new_user = UserDB(username=username, hashed_password=hashed_pw)
    
    db.add(new_user)
    db.commit()
    print(f"✅ Success! Created user '{username}' with password '{password}'")
    db.close()

if __name__ == "__main__":
    create_admin_user()
