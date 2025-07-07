from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
from pydantic import BaseModel

# SQLAlchemy Model
class UserIntegration(Base):
    __tablename__ = 'user_integrations'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    integration_name = Column(String, nullable=False)
    status = Column(String, default='connected')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic Models for API
class UserIntegrationBase(BaseModel):
    integration_name: str
    status: str

class UserIntegrationCreate(UserIntegrationBase):
    user_id: int

class UserIntegrationResponse(UserIntegrationBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 