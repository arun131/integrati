"""Unit tests for ConversationManager class."""

import pytest
import json
from unittest.mock import AsyncMock
from chatbot_api.conversation_manager import ConversationManager


class TestConversationManager:
    """Test cases for ConversationManager class."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client for testing."""
        mock_client = AsyncMock()
        mock_client.hget = AsyncMock()
        mock_client.hset = AsyncMock()
        mock_client.hmget = AsyncMock()
        return mock_client

    @pytest.fixture
    def conversation_manager(self, mock_redis_client):
        """Create a ConversationManager instance with mock Redis client."""
        return ConversationManager(mock_redis_client)

    @pytest.fixture
    def sample_conversation_history(self):
        """Sample conversation history data."""
        return [
            {
                "trajectory": "Sample trajectory 1",
                "reasoning": "Sample reasoning 1",
                "tools_used": ["tool1", "tool2"],
                "response": "Sample response 1",
                "response_timestamp": "2024-01-01T10:00:00",
                "user_query": "Sample query 1",
            },
            {
                "trajectory": "Sample trajectory 2",
                "reasoning": "Sample reasoning 2",
                "tools_used": ["tool3"],
                "response": "Sample response 2",
                "response_timestamp": "2024-01-01T11:00:00",
                "user_query": "Sample query 2",
            },
        ]

    @pytest.fixture
    def sample_message(self):
        """Sample message data for testing."""
        return {
            "trajectory": "Test trajectory",
            "reasoning": "Test reasoning",
            "tools_used": ["test_tool"],
            "response": "Test response",
            "response_timestamp": "2024-01-01T12:00:00",
            "user_query": "Test query",
        }

    @pytest.mark.asyncio
    async def test_init(self, mock_redis_client):
        """Test ConversationManager initialization."""
        manager = ConversationManager(mock_redis_client)
        assert manager.redis_client == mock_redis_client

    @pytest.mark.asyncio
    async def test_get_conversation_history_success(
        self, conversation_manager, mock_redis_client, sample_conversation_history
    ):
        """Test successful retrieval of conversation history."""
        chat_id = "test_chat_123"
        mock_redis_client.hget.return_value = json.dumps(sample_conversation_history)

        result = await conversation_manager.get_conversation_history(chat_id)

        mock_redis_client.hget.assert_called_once_with(
            f"conversation:{chat_id}", "history"
        )
        assert result == sample_conversation_history

    @pytest.mark.asyncio
    async def test_get_conversation_history_no_data(
        self, conversation_manager, mock_redis_client
    ):
        """Test retrieval when no conversation history exists."""
        chat_id = "test_chat_123"
        mock_redis_client.hget.return_value = None

        result = await conversation_manager.get_conversation_history(chat_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_conversation_history_exception(
        self, conversation_manager, mock_redis_client
    ):
        """Test handling of exceptions during history retrieval."""
        chat_id = "test_chat_123"
        mock_redis_client.hget.side_effect = Exception("Redis connection error")

        result = await conversation_manager.get_conversation_history(chat_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_save_conversation_history_success(
        self, conversation_manager, mock_redis_client, sample_conversation_history
    ):
        """Test successful saving of conversation history."""
        chat_id = "test_chat_123"
        mock_redis_client.hset.return_value = True

        result = await conversation_manager.save_conversation_history(
            chat_id, sample_conversation_history
        )

        mock_redis_client.hset.assert_called_once_with(
            f"conversation:{chat_id}",
            "history",
            json.dumps(sample_conversation_history),
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_save_conversation_history_exception(
        self, conversation_manager, mock_redis_client, sample_conversation_history
    ):
        """Test handling of exceptions during history saving."""
        chat_id = "test_chat_123"
        mock_redis_client.hset.side_effect = Exception("Redis write error")

        result = await conversation_manager.save_conversation_history(
            chat_id, sample_conversation_history
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_add_message_to_history_success(
        self, conversation_manager, mock_redis_client, sample_message
    ):
        """Test successful addition of message to history."""
        chat_id = "test_chat_123"
        existing_history = [{"old": "message"}]

        # Mock the get_conversation_history call
        conversation_manager.get_conversation_history = AsyncMock(
            return_value=existing_history
        )
        conversation_manager.save_conversation_history = AsyncMock(return_value=True)

        result = await conversation_manager.add_message_to_history(
            chat_id, sample_message
        )

        # Verify save was called - the timestamp will be modified by the method
        conversation_manager.save_conversation_history.assert_called_once()
        call_args = conversation_manager.save_conversation_history.call_args
        assert call_args[0][0] == chat_id  # chat_id
        assert len(call_args[0][1]) == 2  # existing_history + new_message

        # Check the new message was added with modified timestamp
        new_message = call_args[0][1][1]  # The second item should be the new message
        assert new_message["trajectory"] == sample_message["trajectory"]
        assert new_message["reasoning"] == sample_message["reasoning"]
        assert new_message["tools_used"] == sample_message["tools_used"]
        assert new_message["response"] == sample_message["response"]
        assert new_message["user_query"] == sample_message["user_query"]
        # The timestamp will be different (generated by datetime.now())
        assert "response_timestamp" in new_message

        assert result is True

    @pytest.mark.asyncio
    async def test_add_message_to_history_with_defaults(
        self, conversation_manager, mock_redis_client
    ):
        """Test adding message with missing fields (should use defaults)."""
        chat_id = "test_chat_123"
        incomplete_message = {"user_query": "Test query"}
        existing_history = []

        conversation_manager.get_conversation_history = AsyncMock(
            return_value=existing_history
        )
        conversation_manager.save_conversation_history = AsyncMock(return_value=True)

        result = await conversation_manager.add_message_to_history(
            chat_id, incomplete_message
        )

        # Verify defaults were applied - check that save was called with the right structure
        save_call_args = conversation_manager.save_conversation_history.call_args
        assert save_call_args is not None
        assert save_call_args[0][0] == chat_id  # chat_id
        assert len(save_call_args[0][1]) == 1  # history list has one item

        saved_message = save_call_args[0][1][0]
        assert saved_message["trajectory"] == ""
        assert saved_message["reasoning"] == ""
        assert saved_message["tools_used"] == []
        assert saved_message["response"] == ""
        assert saved_message["user_query"] == "Test query"
        assert "response_timestamp" in saved_message  # timestamp should be added

        assert result is True

    @pytest.mark.asyncio
    async def test_add_message_to_history_exception(
        self, conversation_manager, mock_redis_client, sample_message
    ):
        """Test handling of exceptions during message addition."""
        chat_id = "test_chat_123"

        # Mock the method to raise an exception
        conversation_manager.get_conversation_history = AsyncMock(
            side_effect=Exception("Redis read error")
        )

        result = await conversation_manager.add_message_to_history(
            chat_id, sample_message
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_conversation_metadata_success(
        self, conversation_manager, mock_redis_client
    ):
        """Test successful update of conversation metadata."""
        chat_id = "test_chat_123"
        tenant_id = "test_tenant"
        integrations = ["gmail", "calendar"]
        mock_redis_client.hset.return_value = True

        result = await conversation_manager.update_conversation_metadata(
            chat_id, tenant_id, integrations
        )

        # Verify the mapping was called with correct data
        mock_redis_client.hset.assert_called_once()
        call_args = mock_redis_client.hset.call_args
        assert call_args[0][0] == f"conversation:{chat_id}"  # key
        assert call_args[1]["mapping"]["tenant_id"] == tenant_id  # mapping parameter
        assert call_args[1]["mapping"]["integrations"] == json.dumps(integrations)
        assert "last_seen" in call_args[1]["mapping"]

        assert result is True

    @pytest.mark.asyncio
    async def test_update_conversation_metadata_exception(
        self, conversation_manager, mock_redis_client
    ):
        """Test handling of exceptions during metadata update."""
        chat_id = "test_chat_123"
        tenant_id = "test_tenant"
        integrations = ["gmail"]
        mock_redis_client.hset.side_effect = Exception("Redis update error")

        result = await conversation_manager.update_conversation_metadata(
            chat_id, tenant_id, integrations
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_get_conversation_metadata_success(
        self, conversation_manager, mock_redis_client
    ):
        """Test successful retrieval of conversation metadata."""
        chat_id = "test_chat_123"
        tenant_id = "test_tenant"
        integrations = ["gmail", "calendar"]
        last_seen = "2024-01-01T10:00:00"

        mock_redis_client.hmget.return_value = [
            tenant_id,
            json.dumps(integrations),
            last_seen,
        ]

        result = await conversation_manager.get_conversation_metadata(chat_id)

        mock_redis_client.hmget.assert_called_once_with(
            f"conversation:{chat_id}", "tenant_id", "integrations", "last_seen"
        )

        expected_result = {
            "tenant_id": tenant_id,
            "integrations": integrations,
            "last_seen": last_seen,
        }
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_get_conversation_metadata_no_tenant_id(
        self, conversation_manager, mock_redis_client
    ):
        """Test metadata retrieval when tenant_id doesn't exist."""
        chat_id = "test_chat_123"
        mock_redis_client.hmget.return_value = [None, None, None]

        result = await conversation_manager.get_conversation_metadata(chat_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_conversation_metadata_exception(
        self, conversation_manager, mock_redis_client
    ):
        """Test handling of exceptions during metadata retrieval."""
        chat_id = "test_chat_123"
        mock_redis_client.hmget.side_effect = Exception("Redis read error")

        result = await conversation_manager.get_conversation_metadata(chat_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_conversation_metadata_malformed_integrations(
        self, conversation_manager, mock_redis_client
    ):
        """Test metadata retrieval with malformed integrations JSON."""
        chat_id = "test_chat_123"
        tenant_id = "test_tenant"
        malformed_integrations = "invalid json"
        last_seen = "2024-01-01T10:00:00"

        mock_redis_client.hmget.return_value = [
            tenant_id,
            malformed_integrations,
            last_seen,
        ]

        result = await conversation_manager.get_conversation_metadata(chat_id)

        # Should handle JSON decode error gracefully
        assert result is None
