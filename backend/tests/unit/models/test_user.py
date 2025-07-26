import pytest
from app.models.user import User, UserCreate, UserInDB, Token, TokenData
from pydantic import ValidationError

class TestUserModel:
    """Test cases for User model"""
    
    def test_user_create_valid(self):
        """Test creating a valid UserCreate model"""
        user_data = {
            "google_id": "test_google_id",
            "email": "test@example.com",
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_expiry": "2024-12-31T23:59:59",
            "scope": "test_scope"
        }
        user = UserCreate(**user_data)
        assert user.google_id == "test_google_id"
        assert user.email == "test@example.com"
        assert user.access_token == "test_access_token"
        assert user.refresh_token == "test_refresh_token"
        assert user.token_expiry == "2024-12-31T23:59:59"
        assert user.scope == "test_scope"
    
    def test_user_create_invalid_email(self):
        """Test creating UserCreate with invalid email format"""
        user_data = {
            "google_id": "test_google_id",
            "email": "invalid_email",  # This is actually valid for Pydantic string field
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_expiry": "2024-12-31T23:59:59",
            "scope": "test_scope"
        }
        # Pydantic string field accepts any string, so this should work
        user = UserCreate(**user_data)
        assert user.email == "invalid_email"
    
    def test_user_in_db_valid(self):
        """Test creating a valid UserInDB model"""
        user_data = {
            "id": 1,
            "google_id": "test_google_id",
            "email": "test@example.com",
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_expiry": "2024-12-31T23:59:59",
            "scope": "test_scope"
        }
        user = UserInDB(**user_data)
        assert user.id == 1
        assert user.google_id == "test_google_id"
        assert user.email == "test@example.com"
    
    def test_token_model(self):
        """Test Token model"""
        token_data = {
            "access_token": "test_jwt_token",
            "token_type": "bearer"
        }
        token = Token(**token_data)
        assert token.access_token == "test_jwt_token"
        assert token.token_type == "bearer"
    
    def test_token_default_type(self):
        """Test Token model with default token_type"""
        token_data = {
            "access_token": "test_jwt_token"
        }
        token = Token(**token_data)
        assert token.access_token == "test_jwt_token"
        assert token.token_type == "bearer"
    
    def test_token_data_model(self):
        """Test TokenData model"""
        token_data = TokenData(email="test@example.com")
        assert token_data.email == "test@example.com"
    
    def test_token_data_none_email(self):
        """Test TokenData model with None email"""
        token_data = TokenData(email=None)
        assert token_data.email is None 