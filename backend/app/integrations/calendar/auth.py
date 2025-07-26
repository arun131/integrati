from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.crud.user import create_user, get_user_by_google_id, update_user_tokens, get_user_by_email
from app.models.user import UserCreate
from ..common.google_auth import get_google_auth_flow
from datetime import timedelta
from googleapiclient.discovery import build

router = APIRouter()

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

@router.get("/login")
async def calendar_login():
    """
    Start the Calendar OAuth flow by redirecting to Google's authorization URL.
    """
    try:
        flow = get_google_auth_flow(redirect_uri=settings.CALENDAR_REDIRECT_URI, scopes=SCOPES)
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return RedirectResponse(authorization_url)
    except Exception as e:
        print(f"Error starting Calendar OAuth flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start Calendar OAuth flow"
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
            detail=f"Google OAuth error: {error}"
        )
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not found"
        )
    
    try:
        # Exchange authorization code for tokens
        flow = get_google_auth_flow(redirect_uri=settings.CALENDAR_REDIRECT_URI, scopes=SCOPES)
        
        # Set the redirect URI explicitly on the flow for token exchange
        flow.redirect_uri = settings.CALENDAR_REDIRECT_URI
        
        # Fetch the token
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        if not credentials or not credentials.token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token from Google"
            )
        
        # Get user info from Google
        userinfo_service = build('oauth2', 'v2', credentials=credentials)
        user_info = userinfo_service.userinfo().get().execute()
        google_id = user_info['id']
        email = user_info['email']
        
        # Check if user exists in database
        db_user = get_user_by_google_id(db, google_id=google_id)
        current_scopes = " ".join(flow.credentials.scopes) if flow.credentials.scopes else ""
        
        if db_user:
            # Update existing user with new tokens
            updated_user = update_user_tokens(
                db, db_user, credentials.token, credentials.refresh_token,
                credentials.expiry, current_scopes
            )
        else:
            # Check if user exists with this email
            existing_email_user = get_user_by_email(db, email=email)
            if existing_email_user:
                # Update existing user with new google_id and tokens
                existing_email_user.google_id = google_id
                updated_user = update_user_tokens(
                    db, existing_email_user, credentials.token, credentials.refresh_token,
                    credentials.expiry, current_scopes
                )
            else:
                # Create new user
                new_user = UserCreate(
                    google_id=google_id,
                    email=email,
                    access_token=credentials.token,
                    refresh_token=credentials.refresh_token,
                    token_expiry=credentials.expiry.isoformat(),
                    scope=current_scopes
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
        existing_integration = get_user_integration(db, updated_user.id, 'calendar')
        if not existing_integration:
            create_user_integration(db, updated_user.id, 'calendar', 'connected')
            print(f"Created Calendar integration for user: {updated_user.email}")
        else:
            print(f"Calendar integration already exists for user: {updated_user.email}")
        
        # Redirect to frontend with token and integration info
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?token={jwt_token}&integration=calendar",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        print(f"Error during Calendar OAuth callback: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Calendar OAuth callback"
        ) 