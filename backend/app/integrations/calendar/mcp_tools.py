from app.mcp.instance import mcp
from app.mcp.access_control import user_has_permission
from app.mcp.utils import create_pending_action_for_tool
from fastapi import Depends
from app.database.connection import get_db
from app.crud.user import get_user_by_id
from .google_auth import get_google_credentials, get_calendar_service
from datetime import datetime, timedelta

def get_db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@mcp.tool()
def list_events(user_id: int, days: int = 7, db=Depends(get_db_session)):
    allowed, state = user_has_permission(db, user_id, 'calendar', 'list_events')
    if not allowed and state != 'verify':
        raise Exception('Not authorized')
    if state == 'verify':
        create_pending_action_for_tool(db, user_id, 'calendar', 'list_events', {"days": days})
        return {"status": "pending_user_approval"}
    user = get_user_by_id(db, user_id)
    if not user:
        raise Exception('User not found')
    creds = get_google_credentials(user.__dict__, user_id, db)
    if not creds:
        raise Exception('Could not refresh Google credentials.')
    service = get_calendar_service(creds)
    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(days=days)).isoformat() + 'Z'
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
        formatted_events.append({
            'id': event['id'],
            'summary': event.get('summary', 'No Title'),
            'description': event.get('description'),
            'start_time': start,
            'end_time': end,
            'attendees': [attendee['email'] for attendee in event.get('attendees', [])],
            'html_link': event.get('htmlLink', '')
        })
    return {"events": formatted_events}

@mcp.tool()
def create_event(user_id: int, title: str, start: str, end: str, db=Depends(get_db_session)):
    allowed, state = user_has_permission(db, user_id, 'calendar', 'create_event')
    if not allowed and state != 'verify':
        raise Exception('Not authorized')
    if state == 'verify':
        create_pending_action_for_tool(db, user_id, 'calendar', 'create_event', {"title": title, "start": start, "end": end})
        return {"status": "pending_user_approval"}
    user = get_user_by_id(db, user_id)
    if not user:
        raise Exception('User not found')
    creds = get_google_credentials(user.__dict__, user_id, db)
    if not creds:
        raise Exception('Could not refresh Google credentials.')
    service = get_calendar_service(creds)
    event = {
        'summary': title,
        'start': {'dateTime': start, 'timeZone': 'UTC'},
        'end': {'dateTime': end, 'timeZone': 'UTC'},
    }
    event_result = service.events().insert(calendarId='primary', body=event).execute()
    return {
        'id': event_result['id'],
        'summary': event_result.get('summary', 'No Title'),
        'description': event_result.get('description'),
        'start_time': event_result['start'].get('dateTime', event_result['start'].get('date')),
        'end_time': event_result['end'].get('dateTime', event_result['end'].get('date')),
        'attendees': [attendee['email'] for attendee in event_result.get('attendees', [])],
        'html_link': event_result.get('htmlLink', '')
    } 