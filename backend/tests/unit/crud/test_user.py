from datetime import datetime

import pytest

from app.crud.user import (
    create_user,
    get_user_by_email,
    get_user_by_google_id,
    get_user_by_id,
    update_user_tokens,
)
from app.models.user import User, UserCreate


class TestUserCRUD:
    """Test cases for user CRUD operations"""

    def test_create_user(self, db_session):
        """Test creating a new user"""
        user_data = UserCreate(
            google_id="test_google_id_123",
            email="test@example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry="2024-12-31T23:59:59",
            scope="test_scope",
        )

        user = create_user(db_session, user_data)

        assert user.id is not None
        assert user.google_id == "test_google_id_123"
        assert user.email == "test@example.com"
        assert user.access_token == "test_access_token"
        assert user.refresh_token == "test_refresh_token"
        assert user.token_expiry == "2024-12-31T23:59:59"
        assert user.scope == "test_scope"

    def test_get_user_by_google_id(self, db_session, test_user):
        """Test getting user by Google ID"""
        user = get_user_by_google_id(db_session, "test_google_id_123")

        assert user is not None
        assert user.google_id == "test_google_id_123"
        assert user.email == "test@example.com"

    def test_get_user_by_google_id_not_found(self, db_session):
        """Test getting user by non-existent Google ID"""
        user = get_user_by_google_id(db_session, "non_existent_id")

        assert user is None

    def test_get_user_by_email(self, db_session, test_user):
        """Test getting user by email"""
        user = get_user_by_email(db_session, "test@example.com")

        assert user is not None
        assert user.email == "test@example.com"
        assert user.google_id == "test_google_id_123"

    def test_get_user_by_email_not_found(self, db_session):
        """Test getting user by non-existent email"""
        user = get_user_by_email(db_session, "nonexistent@example.com")

        assert user is None

    def test_get_user_by_id(self, db_session, test_user):
        """Test getting user by ID"""
        user = get_user_by_id(db_session, test_user.id)

        assert user is not None
        assert user.id == test_user.id
        assert user.email == "test@example.com"

    def test_get_user_by_id_not_found(self, db_session):
        """Test getting user by non-existent ID"""
        user = get_user_by_id(db_session, 999)

        assert user is None

    def test_update_user_tokens(self, db_session, test_user):
        """Test updating user tokens"""
        new_access_token = "new_access_token"
        new_refresh_token = "new_refresh_token"
        new_token_expiry = datetime(2024, 12, 31, 23, 59, 59)
        new_scope = "new_scope"

        updated_user = update_user_tokens(
            db_session,
            test_user,
            new_access_token,
            new_refresh_token,
            new_token_expiry,
            new_scope,
        )

        assert updated_user.access_token == new_access_token
        assert updated_user.refresh_token == new_refresh_token
        assert updated_user.token_expiry == new_token_expiry.isoformat()
        assert updated_user.scope == new_scope

    def test_update_user_tokens_none_expiry(self, db_session, test_user):
        """Test updating user tokens with None expiry"""
        new_access_token = "new_access_token"
        new_refresh_token = "new_refresh_token"
        new_scope = "new_scope"

        updated_user = update_user_tokens(
            db_session, test_user, new_access_token, new_refresh_token, None, new_scope
        )

        assert updated_user.access_token == new_access_token
        assert updated_user.refresh_token == new_refresh_token
        assert updated_user.token_expiry is None
        assert updated_user.scope == new_scope
