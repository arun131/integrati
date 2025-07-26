import pytest

from app.crud.pending_action import (
    create_pending_action,
    get_pending_actions,
    update_pending_action_status,
)
from app.models.pending_action import PendingAction


class TestPendingActionCRUD:
    """Test cases for pending action CRUD operations"""

    def test_create_pending_action(self, db_session):
        """Test creating a new pending action"""
        user_id = 1
        integration_name = "gmail"
        tool_name = "send_email"
        parameters = {"to": "test@example.com", "subject": "Test"}

        action = create_pending_action(
            db_session, user_id, integration_name, tool_name, parameters
        )

        assert action.id is not None
        assert action.user_id == user_id
        assert action.integration_name == integration_name
        assert action.tool_name == tool_name
        assert action.parameters == parameters
        assert action.status == "pending"
        assert action.created_at is not None
        assert action.updated_at is not None

    def test_get_pending_actions(self, db_session):
        """Test getting pending actions for a user"""
        # Create multiple pending actions for user_id = 1
        user_id = 1
        action1 = create_pending_action(
            db_session, user_id, "gmail", "send_email", {"to": "test1@example.com"}
        )
        action2 = create_pending_action(
            db_session, user_id, "calendar", "create_event", {"title": "Meeting"}
        )

        # Create an action for a different user
        create_pending_action(
            db_session, 2, "gmail", "send_email", {"to": "test2@example.com"}
        )

        # Get pending actions for user_id = 1
        actions = get_pending_actions(db_session, user_id)

        assert len(actions) == 2
        assert all(action.user_id == user_id for action in actions)
        assert all(action.status == "pending" for action in actions)

    def test_get_pending_actions_with_status_filter(self, db_session):
        """Test getting pending actions with specific status"""
        user_id = 1

        # Create actions with different statuses
        action1 = create_pending_action(
            db_session, user_id, "gmail", "send_email", {"to": "test1@example.com"}
        )
        action2 = create_pending_action(
            db_session, user_id, "calendar", "create_event", {"title": "Meeting"}
        )

        # Update one action to approved
        update_pending_action_status(db_session, action1.id, "approved")

        # Get only pending actions
        pending_actions = get_pending_actions(db_session, user_id, "pending")
        assert len(pending_actions) == 1
        assert pending_actions[0].status == "pending"

        # Get approved actions
        approved_actions = get_pending_actions(db_session, user_id, "approved")
        assert len(approved_actions) == 1
        assert approved_actions[0].status == "approved"

    def test_update_pending_action_status(self, db_session):
        """Test updating pending action status"""
        user_id = 1
        action = create_pending_action(
            db_session, user_id, "gmail", "send_email", {"to": "test@example.com"}
        )

        # Update status to approved
        updated_action = update_pending_action_status(db_session, action.id, "approved")

        assert updated_action is not None
        assert updated_action.status == "approved"
        assert updated_action.id == action.id

    def test_update_pending_action_status_not_found(self, db_session):
        """Test updating status for non-existent action"""
        updated_action = update_pending_action_status(db_session, 999, "approved")

        assert updated_action is None

    def test_get_pending_actions_empty(self, db_session):
        """Test getting pending actions when none exist"""
        actions = get_pending_actions(db_session, 999)

        assert len(actions) == 0

    def test_create_pending_action_complex_parameters(self, db_session):
        """Test creating pending action with complex parameters"""
        user_id = 1
        integration_name = "gmail"
        tool_name = "send_email"
        complex_parameters = {
            "to": "test@example.com",
            "subject": "Test Subject",
            "body": "This is a test email body",
            "attachments": ["file1.pdf", "file2.jpg"],
            "cc": ["cc1@example.com", "cc2@example.com"],
            "bcc": ["bcc@example.com"],
            "metadata": {"priority": "high", "category": "work"},
        }

        action = create_pending_action(
            db_session, user_id, integration_name, tool_name, complex_parameters
        )

        assert action.parameters == complex_parameters
        assert action.integration_name == integration_name
        assert action.tool_name == tool_name
