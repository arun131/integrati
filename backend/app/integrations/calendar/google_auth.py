import os
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.crud.user import update_user_tokens
from .config import CALENDAR_REDIRECT_URI

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/calendar',
]

CLIENT_SECRETS_FILE = "./app/credentials.json"

def get_google_auth_flow():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=CALENDAR_REDIRECT_URI
    )
    return flow

def get_google_credentials(user_data: dict, user_id: int, db):
    """Get Google credentials for calendar access"""
    try:
        creds = None
        if user_data:
            creds = Credentials(
                token=user_data.get('access_token'),
                refresh_token=user_data.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=SCOPES
            )
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    from app.crud.user import get_user_by_google_id
                    db_user = get_user_by_google_id(db, user_data['google_id'])
                    if db_user:
                        update_user_tokens(db, db_user, creds.token, creds.refresh_token, creds.expiry, " ".join(creds.scopes))
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    return None
            else:
                print("No valid credentials or refresh token available.")
                return None
        return creds
    except Exception as e:
        print(f"Error getting Google credentials: {e}")
        return None

def get_calendar_service(credentials):
    """Get Google Calendar service"""
    try:
        service = build('calendar', 'v3', credentials=credentials)
        return service
    except Exception as e:
        print(f"Error building calendar service: {e}")
        return None 