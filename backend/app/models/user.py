from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from backend.app.database.connection import Base
from pydantic import BaseModel
from typing import Optional

# SQLAlchemy Model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    access_token = Column(String)
    refresh_token = Column(String)
    token_expiry = Column(String)
    scope = Column(String)

# Pydantic Models for API (request/response)
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    google_id: str
    access_token: str
    refresh_token: str
    token_expiry: str
    scope: str

class UserInDB(UserBase):
    id: int
    google_id: str
    access_token: str
    refresh_token: str
    token_expiry: str
    scope: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None 