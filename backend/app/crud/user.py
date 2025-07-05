from sqlalchemy.orm import Session
from app.models.user import User, UserCreate
from datetime import datetime

def get_user_by_google_id(db: Session, google_id: str):
    return db.query(User).filter(User.google_id == google_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate):
    db_user = User(
        google_id=user.google_id,
        email=user.email,
        access_token=user.access_token,
        refresh_token=user.refresh_token,
        token_expiry=user.token_expiry,
        scope=user.scope
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_tokens(db: Session, user: User, access_token: str, refresh_token: str, token_expiry: datetime, scope: str):
    user.access_token = access_token
    user.refresh_token = refresh_token
    user.token_expiry = token_expiry.isoformat()
    user.scope = scope
    db.add(user)
    db.commit()
    db.refresh(user)
    return user 