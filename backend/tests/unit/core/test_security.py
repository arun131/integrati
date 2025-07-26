from datetime import datetime, timedelta

from fastapi import HTTPException, status
from jose import JWTError, jwt
import pytest

from app.core.config import settings
from app.core.security import create_access_token, verify_token


class TestSecurity:
    """Test cases for security functions"""

    def test_create_access_token_with_expires_delta(self):
        """Test creating access token with custom expiry"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=30)

        token = create_access_token(data=data, expires_delta=expires_delta)

        assert token is not None
        assert isinstance(token, str)

        # Decode and verify the token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == "test@example.com"

    def test_create_access_token_without_expires_delta(self):
        """Test creating access token with default expiry"""
        data = {"sub": "test@example.com"}

        token = create_access_token(data=data)

        assert token is not None
        assert isinstance(token, str)

        # Decode and verify the token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == "test@example.com"

    def test_create_access_token_with_additional_data(self):
        """Test creating access token with additional data"""
        data = {"sub": "test@example.com", "user_id": 123, "role": "admin"}
        expires_delta = timedelta(minutes=30)

        token = create_access_token(data=data, expires_delta=expires_delta)

        assert token is not None

        # Decode and verify the token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == "test@example.com"
        assert payload["user_id"] == 123
        assert payload["role"] == "admin"

    def test_verify_token_valid(self):
        """Test verifying a valid token"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data=data, expires_delta=expires_delta)

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        token_data = verify_token(token, credentials_exception)

        assert token_data.email == "test@example.com"

    def test_verify_token_invalid(self):
        """Test verifying an invalid token"""
        invalid_token = "invalid_token"

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token, credentials_exception)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verify_token_missing_sub(self):
        """Test verifying a token without 'sub' field"""
        data = {"user_id": 123}  # Missing 'sub' field
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data=data, expires_delta=expires_delta)

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, credentials_exception)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verify_token_expired(self):
        """Test verifying an expired token"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=-30)  # Negative delta for expired token
        token = create_access_token(data=data, expires_delta=expires_delta)

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, credentials_exception)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
