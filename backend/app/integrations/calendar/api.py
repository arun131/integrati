from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.core.dependencies import get_current_user
from app.models.user import UserInDB
from .google_auth import get_google_credentials, get_calendar_service
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

router = APIRouter()

class EventRequest(BaseModel):
    summary: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    attendees: Optional[List[str]] = None

class EventResponse(BaseModel):
    id: str
    summary: str
    description: Optional[str]
    start_time: str
    end_time: str
    attendees: Optional[List[str]]
    html_link: str

@router.get("/events", response_model=List[EventResponse])
async def get_events(
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        creds = get_google_credentials(current_user.dict(), current_user.id, db)
        if not creds:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not refresh Google credentials.")
        
        service = get_calendar_service(creds)
        
        # Get events for the next 7 days
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=7)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            formatted_events.append(EventResponse(
                id=event['id'],
                summary=event.get('summary', 'No Title'),
                description=event.get('description'),
                start_time=start,
                end_time=end,
                attendees=[attendee['email'] for attendee in event.get('attendees', [])],
                html_link=event.get('htmlLink', '')
            ))
        
        return formatted_events
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get events: {e}")

@router.post("/events", response_model=EventResponse)
async def create_event(
    request: EventRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        creds = get_google_credentials(current_user.dict(), current_user.id, db)
        if not creds:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not refresh Google credentials.")
        
        service = get_calendar_service(creds)
        
        event = {
            'summary': request.summary,
            'description': request.description,
            'start': {
                'dateTime': request.start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': request.end_time,
                'timeZone': 'UTC',
            },
        }
        
        if request.attendees:
            event['attendees'] = [{'email': email} for email in request.attendees]
        
        event_result = service.events().insert(
            calendarId='primary',
            body=event
        ).execute()
        
        return EventResponse(
            id=event_result['id'],
            summary=event_result.get('summary', 'No Title'),
            description=event_result.get('description'),
            start_time=event_result['start'].get('dateTime', event_result['start'].get('date')),
            end_time=event_result['end'].get('dateTime', event_result['end'].get('date')),
            attendees=[attendee['email'] for attendee in event_result.get('attendees', [])],
            html_link=event_result.get('htmlLink', '')
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create event: {e}")

@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        creds = get_google_credentials(current_user.dict(), current_user.id, db)
        if not creds:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not refresh Google credentials.")
        
        service = get_calendar_service(creds)
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        
        return {"message": "Event deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete event: {e}")

 