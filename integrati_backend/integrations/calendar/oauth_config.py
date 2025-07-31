"""Calendar OAuth configuration settings."""

import os
from typing import Dict, Any


class CalendarOAuthConfig:
    """Configuration class for Calendar OAuth settings."""

    # OAuth 2.0 configuration
    CLIENT_ID = os.getenv("CALENDAR_CLIENT_ID", "your-calendar-client-id")
    CLIENT_SECRET = os.getenv("CALENDAR_CLIENT_SECRET", "your-calendar-client-secret")
    REDIRECT_URI = os.getenv(
        "CALENDAR_REDIRECT_URI",
        "http://localhost:8000/integrations/calendar/auth/callback",
    )

    # Calendar API scopes
    SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.readonly",
    ]

    # API endpoints
    AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"

    @classmethod
    def get_auth_url_params(cls, state: str) -> Dict[str, Any]:
        """Get parameters for OAuth authorization URL."""
        return {
            "client_id": cls.CLIENT_ID,
            "redirect_uri": cls.REDIRECT_URI,
            "scope": " ".join(cls.SCOPES),
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }

    @classmethod
    def get_token_request_data(cls, auth_code: str) -> Dict[str, Any]:
        """Get data for token exchange request."""
        return {
            "client_id": cls.CLIENT_ID,
            "client_secret": cls.CLIENT_SECRET,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": cls.REDIRECT_URI,
        }

    @classmethod
    def get_refresh_token_data(cls, refresh_token: str) -> Dict[str, Any]:
        """Get data for token refresh request."""
        return {
            "client_id": cls.CLIENT_ID,
            "client_secret": cls.CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
