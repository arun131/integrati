from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
from pydantic import BaseModel

# SQLAlchemy Model
class UserTool(Base):
    __tablename__ = 'user_tools'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    integration_name = Column(String, nullable=False)
    tool_name = Column(String, nullable=False)
    state = Column(String, nullable=False, default='enabled')  # enabled, verify, disabled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic Models for API
class UserToolBase(BaseModel):
    integration_name: str
    tool_name: str
    state: str

class UserToolCreate(UserToolBase):
    user_id: int

class UserToolResponse(UserToolBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 