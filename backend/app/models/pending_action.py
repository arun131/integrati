from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
from pydantic import BaseModel
from typing import Dict, Any

# SQLAlchemy Model
class PendingAction(Base):
    __tablename__ = 'pending_actions'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    integration_name = Column(String, nullable=False)
    tool_name = Column(String, nullable=False)
    parameters = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default='pending')  # pending, approved, rejected, expired
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic Models for API
class PendingActionBase(BaseModel):
    integration_name: str
    tool_name: str
    parameters: Dict[str, Any]
    status: str

class PendingActionCreate(PendingActionBase):
    user_id: int

class PendingActionResponse(PendingActionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 