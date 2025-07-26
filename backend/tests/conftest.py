from datetime import datetime, timedelta
import os
import tempfile
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.crud.user import create_user
from app.database.connection import Base, get_db

# Import your app and database
from app.main import app
from app.models.user import User, UserCreate

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the get_db dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    """Database session for testing"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_db(db_session):
    """Clean database before each test"""
    # Clear all tables
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user_data = UserCreate(
        google_id="test_google_id_123",
        email="test@example.com",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_expiry="2024-12-31T23:59:59",
        scope="test_scope",
    )
    user = create_user(db_session, user_data)
    return user


@pytest.fixture
def mock_google_credentials():
    """Mock Google credentials"""
    mock_creds = Mock()
    mock_creds.valid = True
    mock_creds.expired = False
    mock_creds.refresh_token = "test_refresh_token"
    return mock_creds


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service"""
    mock_service = Mock()
    return mock_service


@pytest.fixture
def mock_calendar_service():
    """Mock Calendar service"""
    mock_service = Mock()
    return mock_service


@pytest.fixture
def valid_token():
    """Create a valid JWT token for testing"""
    from datetime import timedelta

    from app.core.security import create_access_token

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": "test@example.com"}, expires_delta=access_token_expires
    )
    return token


@pytest.fixture
def auth_headers(valid_token):
    """Headers with valid authentication token"""
    return {"Authorization": f"Bearer {valid_token}"}


@pytest.fixture
def mock_firebase_auth():
    """Mock Firebase authentication"""
    with patch("app.api.auth.firebase_auth") as mock_auth:
        mock_auth.verify_id_token.return_value = {
            "uid": "test_firebase_uid",
            "email": "test@example.com",
        }
        yield mock_auth
