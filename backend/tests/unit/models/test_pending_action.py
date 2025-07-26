from datetime import datetime
from typing import Any, Dict

from pydantic import ValidationError
import pytest

from app.models.pending_action import (
    PendingAction,
    PendingActionBase,
    PendingActionCreate,
    PendingActionResponse,
)


class TestPendingActionModel:
    """Test cases for PendingAction model"""

    def test_pending_action_base_valid(self):
        """Test creating a valid PendingActionBase model"""
        action_data = {
            "integration_name": "gmail",
            "tool_name": "send_email",
            "parameters": {"to": "test@example.com", "subject": "Test"},
            "status": "pending",
        }
        action = PendingActionBase(**action_data)
        assert action.integration_name == "gmail"
        assert action.tool_name == "send_email"
        assert action.parameters == {"to": "test@example.com", "subject": "Test"}
        assert action.status == "pending"

    def test_pending_action_create_valid(self):
        """Test creating a valid PendingActionCreate model"""
        action_data = {
            "user_id": 1,
            "integration_name": "gmail",
            "tool_name": "send_email",
            "parameters": {"to": "test@example.com", "subject": "Test"},
            "status": "pending",
        }
        action = PendingActionCreate(**action_data)
        assert action.user_id == 1
        assert action.integration_name == "gmail"
        assert action.tool_name == "send_email"
        assert action.parameters == {"to": "test@example.com", "subject": "Test"}
        assert action.status == "pending"

    def test_pending_action_response_valid(self):
        """Test creating a valid PendingActionResponse model"""
        now = datetime.utcnow()
        action_data = {
            "id": 1,
            "user_id": 1,
            "integration_name": "gmail",
            "tool_name": "send_email",
            "parameters": {"to": "test@example.com", "subject": "Test"},
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        action = PendingActionResponse(**action_data)
        assert action.id == 1
        assert action.user_id == 1
        assert action.integration_name == "gmail"
        assert action.tool_name == "send_email"
        assert action.parameters == {"to": "test@example.com", "subject": "Test"}
        assert action.status == "pending"
        assert action.created_at == now
        assert action.updated_at == now

    def test_pending_action_missing_status(self):
        """Test PendingActionBase with missing status (should fail)"""
        action_data = {
            "integration_name": "gmail",
            "tool_name": "send_email",
            "parameters": {"to": "test@example.com", "subject": "Test"},
        }
        with pytest.raises(ValidationError):
            PendingActionBase(**action_data)

    def test_pending_action_empty_integration_name(self):
        """Test PendingActionBase with empty integration name"""
        action_data = {
            "integration_name": "",
            "tool_name": "send_email",
            "parameters": {"to": "test@example.com", "subject": "Test"},
            "status": "pending",
        }
        # Empty string should be valid for Pydantic string field
        action = PendingActionBase(**action_data)
        assert action.integration_name == ""
        assert action.tool_name == "send_email"
        assert action.status == "pending"

    def test_pending_action_empty_tool_name(self):
        """Test PendingActionBase with empty tool name"""
        action_data = {
            "integration_name": "gmail",
            "tool_name": "",
            "parameters": {"to": "test@example.com", "subject": "Test"},
            "status": "pending",
        }
        # Empty string should be valid for Pydantic string field
        action = PendingActionBase(**action_data)
        assert action.integration_name == "gmail"
        assert action.tool_name == ""
        assert action.status == "pending"

    def test_pending_action_complex_parameters(self):
        """Test PendingActionBase with complex parameters"""
        complex_params = {
            "to": "test@example.com",
            "subject": "Test Subject",
            "body": "This is a test email body",
            "attachments": ["file1.pdf", "file2.jpg"],
            "cc": ["cc1@example.com", "cc2@example.com"],
            "bcc": ["bcc@example.com"],
        }
        action_data = {
            "integration_name": "gmail",
            "tool_name": "send_email",
            "parameters": complex_params,
            "status": "approved",
        }
        action = PendingActionBase(**action_data)
        assert action.parameters == complex_params
        assert action.status == "approved"
