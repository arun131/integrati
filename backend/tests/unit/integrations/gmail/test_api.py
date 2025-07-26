import pytest
from unittest.mock import patch, Mock
from fastapi import HTTPException
from app.integrations.gmail.api import router
from app.models.user import UserInDB

class TestGmailAPI:
    """Test cases for Gmail API endpoints"""
    
    def test_search_emails_success(self, client, auth_headers, test_user):
        """Test successful email search"""
        with patch('app.integrations.gmail.api.get_current_user') as mock_get_current_user:
            mock_get_current_user.return_value = UserInDB(
                id=test_user.id,
                google_id=test_user.google_id,
                email=test_user.email,
                access_token=test_user.access_token,
                refresh_token=test_user.refresh_token,
                token_expiry=test_user.token_expiry,
                scope=test_user.scope
            )
            
            with patch('app.integrations.gmail.api.get_google_credentials') as mock_get_creds:
                mock_get_creds.return_value = Mock()
                
                with patch('app.integrations.gmail.api.get_gmail_service') as mock_get_service:
                    mock_service = Mock()
                    mock_get_service.return_value = mock_service
                    
                    with patch('app.integrations.gmail.api.search_gmail_messages') as mock_search:
                        mock_search.return_value = [
                            {
                                "id": "msg1",
                                "threadId": "thread1",
                                "subject": "Test Email",
                                "sender": "sender@example.com",
                                "date": "2024-01-01T10:00:00Z",
                                "snippet": "Test email snippet",
                                "body": "Test email body"
                            }
                        ]
                        
                        response = client.post(
                            "/integrations/gmail/api/search",
                            headers=auth_headers,
                            json={"query": "test"}
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert len(data) == 1
                        assert data[0]["subject"] == "Test Email"
    
    def test_search_emails_no_credentials(self, client, auth_headers, test_user):
        """Test email search with no valid credentials"""
        with patch('app.integrations.gmail.api.get_current_user') as mock_get_current_user:
            mock_get_current_user.return_value = UserInDB(
                id=test_user.id,
                google_id=test_user.google_id,
                email=test_user.email,
                access_token=test_user.access_token,
                refresh_token=test_user.refresh_token,
                token_expiry=test_user.token_expiry,
                scope=test_user.scope
            )
            
            with patch('app.integrations.gmail.api.get_google_credentials') as mock_get_creds:
                mock_get_creds.return_value = None
                
                response = client.post(
                    "/integrations/gmail/api/search",
                    headers=auth_headers,
                    json={"query": "test"}
                )
                
                assert response.status_code == 401
                data = response.json()
                assert data["detail"] == "Could not refresh Google credentials."
    
    def test_get_last_email_success(self, client, auth_headers, test_user):
        """Test successful last email retrieval"""
        with patch('app.integrations.gmail.api.get_current_user') as mock_get_current_user:
            mock_get_current_user.return_value = UserInDB(
                id=test_user.id,
                google_id=test_user.google_id,
                email=test_user.email,
                access_token=test_user.access_token,
                refresh_token=test_user.refresh_token,
                token_expiry=test_user.token_expiry,
                scope=test_user.scope
            )
            
            with patch('app.integrations.gmail.api.get_google_credentials') as mock_get_creds:
                mock_get_creds.return_value = Mock()
                
                with patch('app.integrations.gmail.api.get_gmail_service') as mock_get_service:
                    mock_service = Mock()
                    mock_get_service.return_value = mock_service
                    
                    with patch('app.integrations.gmail.api.get_last_received_email') as mock_get_last:
                        mock_get_last.return_value = {
                            "id": "msg1",
                            "threadId": "thread1",
                            "subject": "Last Email",
                            "sender": "sender@example.com",
                            "date": "2024-01-01T10:00:00Z",
                            "snippet": "Last email snippet",
                            "body": "Last email body"
                        }
                        
                        response = client.get(
                            "/integrations/gmail/api/last-received",
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["subject"] == "Last Email"
    
    def test_get_last_email_no_credentials(self, client, auth_headers, test_user):
        """Test last email retrieval with no valid credentials"""
        with patch('app.integrations.gmail.api.get_current_user') as mock_get_current_user:
            mock_get_current_user.return_value = UserInDB(
                id=test_user.id,
                google_id=test_user.google_id,
                email=test_user.email,
                access_token=test_user.access_token,
                refresh_token=test_user.refresh_token,
                token_expiry=test_user.token_expiry,
                scope=test_user.scope
            )
            
            with patch('app.integrations.gmail.api.get_google_credentials') as mock_get_creds:
                mock_get_creds.return_value = None
                
                response = client.get(
                    "/integrations/gmail/api/last-received",
                    headers=auth_headers
                )
                
                assert response.status_code == 401
                data = response.json()
                assert data["detail"] == "Could not refresh Google credentials."
    
    def test_send_email_success(self, client, auth_headers, test_user):
        """Test successful email sending"""
        with patch('app.integrations.gmail.api.get_current_user') as mock_get_current_user:
            mock_get_current_user.return_value = UserInDB(
                id=test_user.id,
                google_id=test_user.google_id,
                email=test_user.email,
                access_token=test_user.access_token,
                refresh_token=test_user.refresh_token,
                token_expiry=test_user.token_expiry,
                scope=test_user.scope
            )
            
            with patch('app.integrations.gmail.api.get_google_credentials') as mock_get_creds:
                mock_get_creds.return_value = Mock()
                
                with patch('app.integrations.gmail.api.get_gmail_service') as mock_get_service:
                    mock_service = Mock()
                    mock_get_service.return_value = mock_service
                    
                    with patch('app.integrations.gmail.api.send_gmail_message') as mock_send:
                        mock_send.return_value = {"id": "msg_sent_123"}
                        
                        response = client.post(
                            "/integrations/gmail/api/send",
                            headers=auth_headers,
                            json={
                                "to_email": "recipient@example.com",
                                "subject": "Test Subject",
                                "message_text": "Test message",
                                "thread_id": "thread123"
                            }
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["message"] == "Email sent successfully"
                        assert data["id"] == "msg_sent_123"
    
    def test_send_email_failure(self, client, auth_headers, test_user):
        """Test email sending failure"""
        with patch('app.integrations.gmail.api.get_current_user') as mock_get_current_user:
            mock_get_current_user.return_value = UserInDB(
                id=test_user.id,
                google_id=test_user.google_id,
                email=test_user.email,
                access_token=test_user.access_token,
                refresh_token=test_user.refresh_token,
                token_expiry=test_user.token_expiry,
                scope=test_user.scope
            )
            
            with patch('app.integrations.gmail.api.get_google_credentials') as mock_get_creds:
                mock_get_creds.return_value = Mock()
                
                with patch('app.integrations.gmail.api.get_gmail_service') as mock_get_service:
                    mock_service = Mock()
                    mock_get_service.return_value = mock_service
                    
                    with patch('app.integrations.gmail.api.send_gmail_message') as mock_send:
                        mock_send.return_value = None
                        
                        response = client.post(
                            "/integrations/gmail/api/send",
                            headers=auth_headers,
                            json={
                                "to_email": "recipient@example.com",
                                "subject": "Test Subject",
                                "message_text": "Test message"
                            }
                        )
                        
                        assert response.status_code == 500
                        data = response.json()
                        assert data["detail"] == "Failed to send email."
    
    def test_send_email_no_credentials(self, client, auth_headers, test_user):
        """Test email sending with no valid credentials"""
        with patch('app.integrations.gmail.api.get_current_user') as mock_get_current_user:
            mock_get_current_user.return_value = UserInDB(
                id=test_user.id,
                google_id=test_user.google_id,
                email=test_user.email,
                access_token=test_user.access_token,
                refresh_token=test_user.refresh_token,
                token_expiry=test_user.token_expiry,
                scope=test_user.scope
            )
            
            with patch('app.integrations.gmail.api.get_google_credentials') as mock_get_creds:
                mock_get_creds.return_value = None
                
                response = client.post(
                    "/integrations/gmail/api/send",
                    headers=auth_headers,
                    json={
                        "to_email": "recipient@example.com",
                        "subject": "Test Subject",
                        "message_text": "Test message"
                    }
                )
                
                assert response.status_code == 401
                data = response.json()
                assert data["detail"] == "Could not refresh Google credentials." 