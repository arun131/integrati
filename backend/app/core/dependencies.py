from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.app.core.security import verify_token
from backend.app.database.connection import get_db
from backend.app.crud.user import get_user_by_email
from backend.app.models.user import UserInDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_token(token, credentials_exception)
    user = get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return UserInDB.from_orm(user) 