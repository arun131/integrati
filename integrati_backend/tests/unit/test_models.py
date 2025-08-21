"""Unit tests for chatbot API models."""

import pytest
from pydantic import ValidationError
from chatbot_api.models import (
    NewChatRequest,
    ChatbotMessageRequest,
    ContinueChatRequest,
    ChatbotResponse,
    ChatHistoryResponse,
    UserChatsResponse,
    StorageStatsResponse,
    ConversationHistory,
)


class TestNewChatRequest:
    """Test NewChatRequest model."""

    def test_new_chat_request_valid(self):
        """Test valid NewChatRequest creation."""
        request = NewChatRequest(
            tenant_id="test_tenant",
            user_id="test_user@example.com",
            integrations=["gmail", "calendar"],
            initial_message="Hello, I need help with my emails.",
        )

        assert request.tenant_id == "test_tenant"
        assert request.user_id == "test_user@example.com"
        assert request.integrations == ["gmail", "calendar"]
        assert request.initial_message == "Hello, I need help with my emails."

    def test_new_chat_request_without_initial_message(self):
        """Test NewChatRequest without initial message."""
        request = NewChatRequest(
            tenant_id="test_tenant",
            user_id="test_user@example.com",
            integrations=["gmail"],
        )

        assert request.initial_message is None

    def test_new_chat_request_empty_integrations(self):
        """Test NewChatRequest with empty integrations."""
        request = NewChatRequest(
            tenant_id="test_tenant", user_id="test_user@example.com", integrations=[]
        )

        assert request.integrations == []

    def test_new_chat_request_missing_required_fields(self):
        """Test NewChatRequest with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            NewChatRequest(
                tenant_id="test_tenant",
                # Missing user_id
                integrations=["gmail"],
            )

        assert "user_id" in str(exc_info.value)

    def test_new_chat_request_invalid_email_format(self):
        """Test NewChatRequest with invalid email format."""
        # The model doesn't have email validation, so this should pass
        request = NewChatRequest(
            tenant_id="test_tenant",
            user_id="invalid_email",  # This should work since there's no email validation
            integrations=["gmail"],
        )

        assert request.user_id == "invalid_email"


class TestChatbotMessageRequest:
    """Test ChatbotMessageRequest model."""

    def test_chatbot_message_request_valid(self):
        """Test valid ChatbotMessageRequest creation."""
        request = ChatbotMessageRequest(
            chat_id="test_tenant:test_user:abc123",
            message="How many unread emails do I have?",
            integrations=["gmail"],
            token="test_token_12345",
        )

        assert request.chat_id == "test_tenant:test_user:abc123"
        assert request.message == "How many unread emails do I have?"
        assert request.integrations == ["gmail"]
        assert request.token == "test_token_12345"

    def test_chatbot_message_request_long_message(self):
        """Test ChatbotMessageRequest with long message."""
        long_message = "A" * 1000
        request = ChatbotMessageRequest(
            chat_id="test_tenant:test_user:abc123",
            message=long_message,
            integrations=["gmail"],
            token="test_token",
        )

        assert request.message == long_message

    def test_chatbot_message_request_multiple_integrations(self):
        """Test ChatbotMessageRequest with multiple integrations."""
        request = ChatbotMessageRequest(
            chat_id="test_tenant:test_user:abc123",
            message="Test message",
            integrations=["gmail", "calendar", "slack"],
            token="test_token",
        )

        assert len(request.integrations) == 3
        assert "gmail" in request.integrations
        assert "calendar" in request.integrations
        assert "slack" in request.integrations

    def test_chatbot_message_request_missing_required_fields(self):
        """Test ChatbotMessageRequest with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ChatbotMessageRequest(
                chat_id="test_tenant:test_user:abc123",
                # Missing message
                integrations=["gmail"],
                token="test_token",
            )

        assert "message" in str(exc_info.value)

    def test_chatbot_message_request_empty_message(self):
        """Test ChatbotMessageRequest with empty message."""
        # The model doesn't have min_length validation, so empty string should work
        request = ChatbotMessageRequest(
            chat_id="test_tenant:test_user:abc123",
            message="",  # Empty string should be valid
            integrations=["gmail"],
            token="test_token_12345",
        )

        assert request.message == ""

    def test_chatbot_message_request_short_token(self):
        """Test ChatbotMessageRequest with short token."""
        # The model doesn't have min_length validation for token, so short token should work
        request = ChatbotMessageRequest(
            chat_id="test_tenant:test_user:abc123",
            message="Test message",
            integrations=["gmail"],
            token="short",  # Short token should be valid
        )

        assert request.token == "short"


class TestContinueChatRequest:
    """Test ContinueChatRequest model."""

    def test_continue_chat_request_valid(self):
        """Test valid ContinueChatRequest creation."""
        request = ContinueChatRequest(
            message="Continue the conversation",
            integrations=["gmail"],
            token="test_token_12345",
        )

        assert request.message == "Continue the conversation"
        assert request.integrations == ["gmail"]
        assert request.token == "test_token_12345"

    def test_continue_chat_request_without_integrations(self):
        """Test ContinueChatRequest without integrations."""
        request = ContinueChatRequest(
            message="Test message", integrations=[], token="test_token"
        )

        assert request.integrations == []

    def test_continue_chat_request_missing_required_fields(self):
        """Test ContinueChatRequest with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ContinueChatRequest(
                # Missing message
                integrations=["gmail"],
                token="test_token",
            )

        assert "message" in str(exc_info.value)


class TestChatbotResponse:
    """Test ChatbotResponse model."""

    def test_chatbot_response_success(self):
        """Test successful ChatbotResponse creation."""
        response = ChatbotResponse(
            success=True,
            response="You have 5 unread emails.",
            agent_used="orchestrator",
            tools_used=["gmail_tool"],
            reasoning="Used Gmail tool to check unread emails",
            trajectory="Sample trajectory data",
            chat_id="test_tenant:test_user:abc123",
            tenant_id="test_tenant",
        )

        assert response.success is True
        assert response.response == "You have 5 unread emails."
        assert response.agent_used == "orchestrator"
        assert response.tools_used == ["gmail_tool"]
        assert response.reasoning == "Used Gmail tool to check unread emails"
        assert response.trajectory == "Sample trajectory data"
        assert response.chat_id == "test_tenant:test_user:abc123"
        assert response.tenant_id == "test_tenant"
        assert response.session_active is None
        assert response.error is None

    def test_chatbot_response_error(self):
        """Test ChatbotResponse for error case."""
        response = ChatbotResponse(
            success=False,
            error="Processing failed",
            chat_id="test_tenant:test_user:abc123",
            tenant_id="test_tenant",
        )

        assert response.success is False
        assert response.error == "Processing failed"
        assert response.response is None
        assert response.agent_used is None
        assert response.tools_used is None
        assert response.reasoning is None
        assert response.trajectory is None

    def test_chatbot_response_with_optional_fields(self):
        """Test ChatbotResponse with all optional fields."""
        response = ChatbotResponse(
            success=True,
            response="Test response",
            agent_used="test_agent",
            tools_used=["tool1", "tool2"],
            reasoning="Test reasoning",
            trajectory="Test trajectory",
            chat_id="test_chat",
            tenant_id="test_tenant",
            session_active=True,
            error=None,
        )

        assert response.session_active is True
        assert response.error is None

    def test_chatbot_response_missing_required_fields(self):
        """Test ChatbotResponse with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ChatbotResponse(
                success=True,
                # Missing chat_id
                tenant_id="test_tenant",
            )

        assert "chat_id" in str(exc_info.value)

    def test_chatbot_response_trajectory_as_string(self):
        """Test ChatbotResponse with trajectory as string."""
        response = ChatbotResponse(
            success=True,
            response="Test response",
            chat_id="test_chat",
            tenant_id="test_tenant",
            trajectory="String trajectory data",
        )

        assert response.trajectory == "String trajectory data"
        assert isinstance(response.trajectory, str)


class TestChatHistoryResponse:
    """Test ChatHistoryResponse model."""

    def test_chat_history_response_success(self):
        """Test successful ChatHistoryResponse creation."""
        history_data = {
            "history_of_messages": [
                {"message": "Hello", "timestamp": "2024-01-01T10:00:00"},
                {"message": "Hi there", "timestamp": "2024-01-01T11:00:00"},
            ]
        }

        response = ChatHistoryResponse(success=True, history=history_data)

        assert response.success is True
        assert response.history == history_data
        assert response.error is None

    def test_chat_history_response_error(self):
        """Test ChatHistoryResponse for error case."""
        response = ChatHistoryResponse(
            success=False, error="Failed to retrieve history"
        )

        assert response.success is False
        assert response.error == "Failed to retrieve history"
        assert response.history is None

    def test_chat_history_response_missing_required_fields(self):
        """Test ChatHistoryResponse with missing required fields."""
        # The model doesn't have required field validation for history, so this should work
        response = ChatHistoryResponse(
            success=True
            # Missing history field, but it's Optional
        )

        assert response.success is True
        assert response.history is None


class TestUserChatsResponse:
    """Test UserChatsResponse model."""

    def test_user_chats_response_success(self):
        """Test successful UserChatsResponse creation."""
        chats_data = [
            {"chat_id": "chat1", "created_at": "2024-01-01T10:00:00"},
            {"chat_id": "chat2", "created_at": "2024-01-01T11:00:00"},
        ]

        response = UserChatsResponse(success=True, chats=chats_data)

        assert response.success is True
        assert response.chats == chats_data
        assert response.error is None

    def test_user_chats_response_empty_chats(self):
        """Test UserChatsResponse with empty chats."""
        response = UserChatsResponse(success=True, chats=[])

        assert response.chats == []

    def test_user_chats_response_error(self):
        """Test UserChatsResponse for error case."""
        response = UserChatsResponse(success=False, error="Failed to retrieve chats")

        assert response.success is False
        assert response.error == "Failed to retrieve chats"
        assert response.chats is None


class TestStorageStatsResponse:
    """Test StorageStatsResponse model."""

    def test_storage_stats_response_success(self):
        """Test successful StorageStatsResponse creation."""
        stats_data = {
            "active_sessions": 5,
            "session_timeout_seconds": 1800,
            "total_sessions_created": 100,
        }

        response = StorageStatsResponse(success=True, stats=stats_data)

        assert response.success is True
        assert response.stats == stats_data
        assert response.error is None

    def test_storage_stats_response_zero_stats(self):
        """Test StorageStatsResponse with zero values."""
        stats_data = {
            "active_sessions": 0,
            "session_timeout_seconds": 0,
            "total_sessions_created": 0,
        }

        response = StorageStatsResponse(success=True, stats=stats_data)

        assert response.stats["active_sessions"] == 0

    def test_storage_stats_response_error(self):
        """Test StorageStatsResponse for error case."""
        response = StorageStatsResponse(success=False, error="Failed to retrieve stats")

        assert response.success is False
        assert response.error == "Failed to retrieve stats"
        assert response.stats is None


class TestConversationHistory:
    """Test ConversationHistory model."""

    def test_conversation_history_valid(self):
        """Test valid ConversationHistory creation."""
        history = ConversationHistory(
            conversation_id="conv_123",
            tenant_id="test_tenant",
            user_id="test_user@example.com",
            messages=[
                {"message": "Hello", "timestamp": "2024-01-01T10:00:00"},
                {"message": "Hi there", "timestamp": "2024-01-01T11:00:00"},
            ],
            integrations=["gmail", "calendar"],
        )

        assert history.conversation_id == "conv_123"
        assert history.tenant_id == "test_tenant"
        assert history.user_id == "test_user@example.com"
        assert len(history.messages) == 2
        assert history.integrations == ["gmail", "calendar"]

    def test_conversation_history_empty_messages(self):
        """Test ConversationHistory with empty messages."""
        history = ConversationHistory(
            conversation_id="conv_123",
            tenant_id="test_tenant",
            user_id="test_user@example.com",
            messages=[],
            integrations=["gmail"],
        )

        assert history.messages == []

    def test_conversation_history_no_integrations(self):
        """Test ConversationHistory with no integrations."""
        history = ConversationHistory(
            conversation_id="conv_123",
            tenant_id="test_tenant",
            user_id="test_user@example.com",
            messages=[],
            integrations=[],
        )

        assert history.integrations == []

    def test_conversation_history_missing_required_fields(self):
        """Test ConversationHistory with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationHistory(
                conversation_id="conv_123",
                # Missing tenant_id
                user_id="test_user@example.com",
                messages=[],
                integrations=["gmail"],
            )

        assert "tenant_id" in str(exc_info.value)


class TestModelValidation:
    """Test model validation edge cases."""

    def test_very_long_strings(self):
        """Test models with very long string values."""
        long_string = "A" * 10000

        # Should handle long strings without issues
        request = ChatbotMessageRequest(
            chat_id="test_tenant:test_user:abc123",
            message=long_string,
            integrations=["gmail"],
            token="test_token_12345",
        )

        assert request.message == long_string

    def test_special_characters(self):
        """Test models with special characters."""
        special_message = (
            "Hello! How are you? I need help with emails 📧 and calendar 📅"
        )

        request = ChatbotMessageRequest(
            chat_id="test_tenant:test_user:abc123",
            message=special_message,
            integrations=["gmail"],
            token="test_token_12345",
        )

        assert request.message == special_message

    def test_unicode_characters(self):
        """Test models with unicode characters."""
        unicode_message = "Привет! 你好! Hello! 🌍"

        request = ChatbotMessageRequest(
            chat_id="test_tenant:test_user:abc123",
            message=unicode_message,
            integrations=["gmail"],
            token="test_token_12345",
        )

        assert request.message == unicode_message

    def test_numeric_strings(self):
        """Test models with numeric string values."""
        numeric_chat_id = "123:456:789"

        request = ChatbotMessageRequest(
            chat_id=numeric_chat_id,
            message="Test message",
            integrations=["gmail"],
            token="test_token_12345",
        )

        assert request.chat_id == numeric_chat_id
