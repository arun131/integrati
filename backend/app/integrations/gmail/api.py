from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.core.dependencies import get_current_user
from app.models.user import UserInDB
from .google_auth import get_google_credentials, get_gmail_service, search_gmail_messages, get_last_received_email, send_gmail_message
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class EmailSearchRequest(BaseModel):
    query: str

class EmailSendRequest(BaseModel):
    to_email: str
    subject: str
    message_text: str
    thread_id: Optional[str] = None

class EmailResponse(BaseModel):
    id: str
    threadId: str
    subject: str
    sender: str
    date: str
    snippet: str
    body: str

@router.post("/search", response_model=List[EmailResponse])
async def search_emails(
    request: EmailSearchRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        creds = get_google_credentials(current_user.dict(), current_user.id, db)
        if not creds:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not refresh Google credentials.")
        service = get_gmail_service(creds)
        messages = search_gmail_messages(service, request.query)
        return messages
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to search emails: {e}")

@router.get("/last-received", response_model=Optional[EmailResponse])
async def get_last_email(
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        creds = get_google_credentials(current_user.dict(), current_user.id, db)
        if not creds:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not refresh Google credentials.")
        service = get_gmail_service(creds)
        email = get_last_received_email(service)
        return email
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get last email: {e}")

@router.post("/send")
async def send_email(
    request: EmailSendRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        creds = get_google_credentials(current_user.dict(), current_user.id, db)
        if not creds:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not refresh Google credentials.")
        service = get_gmail_service(creds)
        send_result = send_gmail_message(service, current_user.email, request.to_email, request.subject, request.message_text, request.thread_id)
        if send_result:
            return {"message": "Email sent successfully", "id": send_result['id']}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send email.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to send email: {e}") 