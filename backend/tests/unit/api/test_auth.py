import pytest
from unittest.mock import patch, Mock
from fastapi import HTTPException
from app.api.auth import router
from app.models.user import UserInDB

class TestAuthAPI:
    """Test cases for auth API endpoints"""
    
    def test_read_users_me_success(self, client, auth_headers, test_user):
        """Test successful /me endpoint"""
        with patch('app.api.auth.get_current_user') as mock_get_current_user:
            mock_get_current_user.return_value = UserInDB(
                id=test_user.id,
                google_id=test_user.google_id,
                email=test_user.email,
                access_token=test_user.access_token,
                refresh_token=test_user.refresh_token,
                token_expiry=test_user.token_expiry,
                scope=test_user.scope
            )
            
            response = client.get("/api/auth/me", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "test@example.com"
            assert data["google_id"] == "test_google_id_123"
    
    def test_read_users_me_unauthorized(self, client):
        """Test /me endpoint without authentication"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
    
    def test_create_firebase_token_success(self, client, mock_firebase_auth, db_session, test_user):
        """Test successful Firebase token exchange"""
        with patch('app.api.auth.get_db') as mock_get_db:
            mock_get_db.return_value = iter([db_session])
            
            response = client.post(
                "/api/auth/firebase-token",
                json={"id_token": "valid_firebase_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
    
    def test_create_firebase_token_missing_id_token(self, client):
        """Test Firebase token exchange with missing id_token"""
        response = client.post(
            "/api/auth/firebase-token",
            json={}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "id_token required"
    
    def test_create_firebase_token_invalid_token(self, client, mock_firebase_auth):
        """Test Firebase token exchange with invalid token"""
        mock_firebase_auth.verify_id_token.side_effect = Exception("Invalid token")
        
        response = client.post(
            "/api/auth/firebase-token",
            json={"id_token": "invalid_firebase_token"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid Firebase ID token"
    
    def test_create_firebase_token_no_email(self, client, mock_firebase_auth):
        """Test Firebase token exchange with token missing email"""
        mock_firebase_auth.verify_id_token.return_value = {
            'uid': 'test_firebase_uid'
            # Missing email
        }
        
        response = client.post(
            "/api/auth/firebase-token",
            json={"id_token": "valid_firebase_token"}
        )
        
        # The exception is caught and re-raised as 401, not 400
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid Firebase ID token"
    
    def test_create_firebase_token_new_user(self, client, mock_firebase_auth, db_session):
        """Test Firebase token exchange creating new user"""
        with patch('app.api.auth.get_db') as mock_get_db:
            mock_get_db.return_value = iter([db_session])
            
            # Mock that user doesn't exist
            with patch('app.api.auth.get_user_by_google_id') as mock_get_user:
                mock_get_user.return_value = None
                
                with patch('app.api.auth.get_user_by_email') as mock_get_email:
                    mock_get_email.return_value = None
                    
                    with patch('app.api.auth.create_user') as mock_create_user:
                        mock_create_user.return_value = Mock(
                            id=1,
                            email="test@example.com",
                            google_id="test_firebase_uid"
                        )
                        
                        response = client.post(
                            "/api/auth/firebase-token",
                            json={"id_token": "valid_firebase_token"}
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert "access_token" in data
                        assert data["token_type"] == "bearer"
    
    def test_create_firebase_token_existing_user_update(self, client, mock_firebase_auth, db_session, test_user):
        """Test Firebase token exchange updating existing user"""
        with patch('app.api.auth.get_db') as mock_get_db:
            mock_get_db.return_value = iter([db_session])
            
            # Mock that user doesn't exist by google_id but exists by email
            with patch('app.api.auth.get_user_by_google_id') as mock_get_user:
                mock_get_user.return_value = None
                
                with patch('app.api.auth.get_user_by_email') as mock_get_email:
                    mock_get_email.return_value = test_user
                    
                    response = client.post(
                        "/api/auth/firebase-token",
                        json={"id_token": "valid_firebase_token"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert "access_token" in data
                    assert data["token_type"] == "bearer" 