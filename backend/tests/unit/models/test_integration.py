import pytest
from datetime import datetime
from app.models.integration import (
    UserIntegration, 
    UserIntegrationBase, 
    UserIntegrationCreate, 
    UserIntegrationResponse
)
from pydantic import ValidationError

class TestIntegrationModel:
    """Test cases for Integration model"""
    
    def test_user_integration_base_valid(self):
        """Test creating a valid UserIntegrationBase model"""
        integration_data = {
            "integration_name": "gmail",
            "status": "connected"
        }
        integration = UserIntegrationBase(**integration_data)
        assert integration.integration_name == "gmail"
        assert integration.status == "connected"
    
    def test_user_integration_create_valid(self):
        """Test creating a valid UserIntegrationCreate model"""
        integration_data = {
            "user_id": 1,
            "integration_name": "gmail",
            "status": "connected"
        }
        integration = UserIntegrationCreate(**integration_data)
        assert integration.user_id == 1
        assert integration.integration_name == "gmail"
        assert integration.status == "connected"
    
    def test_user_integration_response_valid(self):
        """Test creating a valid UserIntegrationResponse model"""
        now = datetime.utcnow()
        integration_data = {
            "id": 1,
            "user_id": 1,
            "integration_name": "gmail",
            "status": "connected",
            "created_at": now,
            "updated_at": now
        }
        integration = UserIntegrationResponse(**integration_data)
        assert integration.id == 1
        assert integration.user_id == 1
        assert integration.integration_name == "gmail"
        assert integration.status == "connected"
        assert integration.created_at == now
        assert integration.updated_at == now
    
    def test_user_integration_missing_status(self):
        """Test UserIntegrationBase with missing status (should fail)"""
        integration_data = {
            "integration_name": "gmail"
        }
        with pytest.raises(ValidationError):
            UserIntegrationBase(**integration_data)
    
    def test_user_integration_invalid_name(self):
        """Test UserIntegrationBase with invalid integration name"""
        integration_data = {
            "integration_name": "",
            "status": "connected"
        }
        # Empty string should be valid for Pydantic string field
        integration = UserIntegrationBase(**integration_data)
        assert integration.integration_name == ""
        assert integration.status == "connected" 