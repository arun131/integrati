"""
This module contains the core functions for the Google Calendar integration.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core.config import settings
from app.crud.user import update_user_tokens


def get_google_credentials(user, db_user_id: int, db) -> Credentials | None:
    """Gets Google credentials from a user object."""
    # Get the actual SQLAlchemy user from database
    from app.crud.user import get_user_by_id

    db_user = get_user_by_id(db, db_user_id)
    if not db_user:
        print(f"User not found in database for ID: {db_user_id}")
        return None

    creds = None
    if db_user and db_user.access_token:
        print(f"Creating credentials for user: {db_user.email}")
        print(f"User scopes: {db_user.scope}")
        # Use the scopes that were granted during OAuth
        scopes = db_user.scope.split(" ") if db_user.scope else []
        print(f"Parsed scopes: {scopes}")
        user_info = {
            "token": db_user.access_token,
            "refresh_token": db_user.refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "scopes": scopes,
        }
        creds = Credentials.from_authorized_user_info(info=user_info)
        print(f"Credentials created: {creds is not None}")
        print(f"Credentials valid: {creds.valid if creds else False}")
        print(f"Credentials expired: {creds.expired if creds else False}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Attempting to refresh credentials...")
                from google.auth.transport.requests import Request

                creds.refresh(Request())
                print("Credentials refreshed successfully")
                if db_user:
                    update_user_tokens(
                        db,
                        db_user,
                        creds.token,
                        creds.refresh_token,
                        creds.expiry,
                        " ".join(creds.scopes),
                    )
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                return None
        else:
            print("No valid credentials or refresh token available")
            return None
    return creds


def get_calendar_service(creds: Credentials):
    """Builds the Google Calendar service from credentials."""
    return build("calendar", "v3", credentials=creds)


def get_calendar_events(
    service, time_min: str | None = None, time_max: str | None = None
) -> list:
    """Gets events from the user's primary Google Calendar.

    Args:
        service: The Google Calendar service object.
        time_min: The minimum time for events (ISO format). Defaults to now.
        time_max: The maximum time for events (ISO format). Defaults to 7 days from now.

    Returns:
        A list of calendar events.
    """
    if not time_min:
        time_min = datetime.utcnow().isoformat() + "Z"
    if not time_max:
        time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])


def create_calendar_event(
    service,
    summary: str,
    start_time: str,
    end_time: str,
    description: str | None = None,
    attendees: list[str] | None = None,
) -> dict:
    """Creates a new event on the user's primary Google Calendar.

    Args:
        service: The Google Calendar service object.
        summary: The event summary or title.
        start_time: The event start time (ISO format).
        end_time: The event end time (ISO format).
        description: The event description.
        attendees: A list of attendee email addresses.

    Returns:
        The created event.
    """
    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time, "timeZone": "UTC"},
        "end": {"dateTime": end_time, "timeZone": "UTC"},
    }
    if attendees:
        event["attendees"] = [{"email": email} for email in attendees]

    return service.events().insert(calendarId="primary", body=event).execute()


def delete_calendar_event(service, event_id: str):
    """Deletes an event from the user's primary Google Calendar.

    Args:
        service: The Google Calendar service object.
        event_id: The ID of the event to delete.
    """
    service.events().delete(calendarId="primary", eventId=event_id).execute()
