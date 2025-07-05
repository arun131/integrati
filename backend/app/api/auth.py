from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.crud.user import create_user, get_user_by_google_id, update_user_tokens, get_user_by_email
from app.models.user import UserCreate, Token, UserInDB
# from app.services.google_auth_gmail import get_google_auth_flow
from app.core.dependencies import get_current_user
from datetime import timedelta
from googleapiclient.discovery import build
import firebase_admin
from firebase_admin import auth as firebase_auth
import os
import json

router = APIRouter()

# Google OAuth endpoints are handled by the integration-specific auth routers
# These endpoints are kept for reference but not used in this implementation

# Initialize Firebase Admin once at startup
if not firebase_admin._apps:
    # Try to use service account file if available
    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-service-account.json")
    if os.path.exists(service_account_path):
        cred = firebase_admin.credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    elif os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"):
        # Use service account JSON from environment variable
        service_account_info = json.loads(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"))
        cred = firebase_admin.credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
    else:
        # Fallback to default credentials (for development)
        firebase_admin.initialize_app()

@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    return current_user

@router.post("/firebase-token")
async def create_firebase_token(request: Request):
    """
    Exchange a Firebase ID token for a backend JWT.
    """
    body = await request.json()
    id_token = body.get('id_token')
    if not id_token:
        raise HTTPException(status_code=400, detail="id_token required")
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        firebase_uid = decoded_token['uid']
        email = decoded_token.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="No email in Firebase token")
        
        # Create or get user from database
        db = next(get_db())
        db_user = get_user_by_google_id(db, firebase_uid)
        
        if not db_user:
            # Check if user exists with this email
            existing_user = get_user_by_email(db, email)
            if existing_user:
                # Update existing user with new google_id
                existing_user.google_id = firebase_uid
                db.add(existing_user)
                db.commit()
                db.refresh(existing_user)
                db_user = existing_user
            else:
                # Create new user
                new_user = UserCreate(
                    google_id=firebase_uid,
                    email=email,
                    access_token="",
                    refresh_token="",
                    token_expiry="",
                    scope="firebase_auth"
                )
                db_user = create_user(db, new_user)
        
        # Generate backend JWT
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        jwt_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        return {"access_token": jwt_token, "token_type": "bearer"}
    except Exception as e:
        print(f"Error verifying Firebase ID token: {e}")
        raise HTTPException(status_code=401, detail="Invalid Firebase ID token") 