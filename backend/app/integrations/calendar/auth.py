from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.crud.user import (
    create_user,
    get_user_by_email,
    get_user_by_google_id,
    update_user_tokens,
)
from app.database.connection import get_db
from app.models.user import UserCreate

from ..common.google_auth import get_google_auth_flow

router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


@router.get("/login")
async def calendar_login():
    """
    Start the Calendar OAuth flow by redirecting to Google's authorization URL.
    """
    try:
        flow = get_google_auth_flow(
            redirect_uri=settings.CALENDAR_REDIRECT_URI, scopes=SCOPES
        )
        authorization_url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )
        return RedirectResponse(authorization_url)
    except Exception as e:
        print(f"Error starting Calendar OAuth flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start Calendar OAuth flow",
        )


@router.get("/callback")
async def calendar_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handle the OAuth callback from Google for Calendar integration.
    Creates or updates user with Calendar tokens and returns JWT token.
    """
    code = request.query_params.get("code")
    error = request.query_params.get("error")

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}",
        )
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not found",
        )

    try:
        print(f"Received authorization code: {code[:20]}...")

        # Exchange authorization code for tokens using direct HTTP request
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.CALENDAR_REDIRECT_URI,
        }

        print(
            f"Exchanging code for tokens with redirect_uri: {settings.CALENDAR_REDIRECT_URI}"
        )

        response = requests.post(token_url, data=token_data)
        print(f"Token exchange response status: {response.status_code}")

        if response.status_code != 200:
            print(f"Token exchange failed: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange authorization code: {response.text}",
            )

        token_info = response.json()
        print("Token exchange successful")
        print(f"Token response: {token_info}")

        # Calculate token expiry from expires_in
        from datetime import datetime, timedelta

        token_expiry = None
        if token_info.get("expires_in"):
            token_expiry = datetime.utcnow() + timedelta(
                seconds=token_info.get("expires_in")
            )

        # Create credentials object
        credentials = Credentials(
            token=token_info.get("access_token"),
            refresh_token=token_info.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )

        print(
            f"Credentials created with access token: {credentials.token[:20] if credentials.token else 'None'}..."
        )
        print(f"Token scopes: {token_info.get('scope', 'No scope in response')}")
        print(f"Token expiry: {token_expiry}")

        # Get user info from Google using direct HTTP request
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        }

        print(f"Making userinfo request with headers: {headers}")
        userinfo_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo", headers=headers
        )
        print(f"Userinfo response status: {userinfo_response.status_code}")
        print(f"Userinfo response headers: {dict(userinfo_response.headers)}")

        if userinfo_response.status_code != 200:
            print(f"Userinfo request failed: {userinfo_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get user info: {userinfo_response.text}",
            )

        user_info = userinfo_response.json()
        google_id = user_info["id"]
        email = user_info["email"]

        print(f"User info obtained: {email}")

        # Check if user exists in database
        db_user = get_user_by_google_id(db, google_id=google_id)
        new_scopes = set(SCOPES)

        if db_user:
            # Merge new scopes with existing ones
            existing_scopes = set(db_user.scope.split(" ") if db_user.scope else [])
            merged_scopes = existing_scopes.union(new_scopes)
            current_scopes = " ".join(merged_scopes)
            print(f"Existing scopes: {existing_scopes}")
            print(f"New scopes: {new_scopes}")
            print(f"Merged scopes: {merged_scopes}")
            # Update existing user with new tokens and merged scopes
            updated_user = update_user_tokens(
                db,
                db_user,
                credentials.token,
                credentials.refresh_token,
                token_expiry,
                current_scopes,
            )
        else:
            # Check if user exists with this email
            existing_email_user = get_user_by_email(db, email=email)
            if existing_email_user:
                # Merge new scopes with existing ones
                existing_scopes = set(
                    existing_email_user.scope.split(" ")
                    if existing_email_user.scope
                    else []
                )
                merged_scopes = existing_scopes.union(new_scopes)
                current_scopes = " ".join(merged_scopes)
                print(f"Existing scopes: {existing_scopes}")
                print(f"New scopes: {new_scopes}")
                print(f"Merged scopes: {merged_scopes}")
                # Update existing user with new google_id and tokens
                existing_email_user.google_id = google_id
                updated_user = update_user_tokens(
                    db,
                    existing_email_user,
                    credentials.token,
                    credentials.refresh_token,
                    token_expiry,
                    current_scopes,
                )
            else:
                # Create new user with just the new scopes
                current_scopes = " ".join(SCOPES)
                new_user = UserCreate(
                    google_id=google_id,
                    email=email,
                    access_token=credentials.token,
                    refresh_token=credentials.refresh_token,
                    token_expiry=token_expiry.isoformat() if token_expiry else None,
                    scope=current_scopes,
                )
                updated_user = create_user(db, new_user)

        # Generate JWT token for frontend
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        jwt_token = create_access_token(
            data={"sub": updated_user.email}, expires_delta=access_token_expires
        )

        print(f"JWT token generated for user: {updated_user.email}")

        # Create integration entry in the database
        from app.crud.integration import create_user_integration, get_user_integration

        existing_integration = get_user_integration(db, updated_user.id, "calendar")
        if not existing_integration:
            create_user_integration(db, updated_user.id, "calendar", "connected")
            print(f"Created Calendar integration for user: {updated_user.email}")
        else:
            print(f"Calendar integration already exists for user: {updated_user.email}")

        # Redirect to frontend with token and integration info
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?token={jwt_token}&integration=calendar",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as e:
        print(f"Error during Calendar OAuth callback: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Calendar OAuth callback",
        )
