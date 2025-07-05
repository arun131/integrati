from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.crud.user import create_user, get_user_by_google_id, update_user_tokens
from app.models.user import UserCreate
from .google_auth import get_google_auth_flow
from datetime import timedelta
from googleapiclient.discovery import build

router = APIRouter()

@router.get("/login")
async def google_login():
    flow = get_google_auth_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    return RedirectResponse(authorization_url)

@router.get("/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
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
    flow = get_google_auth_flow()
    try:
        # Configure the flow to handle scope changes gracefully
        flow.oauth2session.scope = None  # Allow any scope
        flow.fetch_token(code=code)
        credentials = flow.credentials
        userinfo_service = build('oauth2', 'v2', credentials=credentials)
        user_info = userinfo_service.userinfo().get().execute()
        google_id = user_info['id']
        email = user_info['email']
        db_user = get_user_by_google_id(db, google_id=google_id)
        
        # Log the scopes for debugging
        # credentials.scopes can be None depending on library version
        current_scopes = " ".join(credentials.scopes) if credentials.scopes else ""
        print(f"Current scopes: {current_scopes}")
        
        if db_user:
            print(f"Existing user scopes: {db_user.scope}")
            # Update existing user by google_id
            updated_user = update_user_tokens(
                db, db_user, credentials.token, credentials.refresh_token,
                credentials.expiry, current_scopes
            )
        else:
            # Check if a user already exists with this email (but without google_id)
            from app.crud.user import get_user_by_email
            existing_email_user = get_user_by_email(db, email=email)
            if existing_email_user:
                # Link Google account to existing user
                existing_email_user.google_id = google_id
                updated_user = update_user_tokens(
                    db, existing_email_user, credentials.token, credentials.refresh_token,
                    credentials.expiry, current_scopes
                )
            else:
                new_user = UserCreate(
                    google_id=google_id,
                    email=email,
                    access_token=credentials.token,
                    refresh_token=credentials.refresh_token,
                    token_expiry=credentials.expiry.isoformat(),
                    scope=current_scopes
                )
                created_user = create_user(db, new_user)
                updated_user = created_user
            
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        jwt_token = create_access_token(
            data={"sub": updated_user.email}, expires_delta=access_token_expires
        )
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?token={jwt_token}&integration=gmail",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        print(f"Error during Google OAuth callback: {e}")
        # Log the full exception for debugging
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Google login."
        ) 