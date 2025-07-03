from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from backend.app.database.connection import get_db
from backend.app.core.config import settings
from backend.app.core.security import create_access_token
from backend.app.crud.user import create_user, get_user_by_google_id, update_user_tokens
from backend.app.models.user import UserCreate, Token, UserInDB
from backend.app.services.google_auth_gmail import get_google_auth_flow
from backend.app.core.dependencies import get_current_user
from datetime import timedelta
from googleapiclient.discovery import build

router = APIRouter()

@router.get("/google/login")
async def google_login():
    flow = get_google_auth_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    return RedirectResponse(authorization_url)

@router.get("/google/callback")
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
        flow.fetch_token(code=code)
        credentials = flow.credentials
        print("access_token:", credentials.token)
        print("refresh_token:", credentials.refresh_token)
        userinfo_service = build('oauth2', 'v2', credentials=credentials)
        user_info = userinfo_service.userinfo().get().execute()
        google_id = user_info['id']
        email = user_info['email']
        db_user = get_user_by_google_id(db, google_id=google_id)
        if db_user:
            updated_user = update_user_tokens(
                db, db_user, credentials.token, credentials.refresh_token,
                credentials.expiry, " ".join(credentials.scopes)
            )
        else:
            new_user = UserCreate(
                google_id=google_id,
                email=email,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_expiry=credentials.expiry.isoformat(),
                scope=" ".join(credentials.scopes)
            )
            created_user = create_user(db, new_user)
            updated_user = created_user
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        jwt_token = create_access_token(
            data={"sub": updated_user.email}, expires_delta=access_token_expires
        )
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard?token={jwt_token}",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        print(f"Error during Google OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Google login."
        )

@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    return current_user 