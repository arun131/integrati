"""Unit tests for WebSocket Manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
import json

from events.websocket_manager import (
    WebSocketManager,
    WebSocketConnection,
    WebSocketMessage,
    websocket_manager,
)
from fastapi.websockets import WebSocketState


class TestWebSocketMessage:
    """Test WebSocketMessage dataclass."""

    def test_websocket_message_creation(self):
        """Test WebSocketMessage creation with default values."""
        message = WebSocketMessage(message_type="test", data={"key": "value"})

        assert message.message_type == "test"
        assert message.data == {"key": "value"}
        assert message.timestamp is not None
        assert message.message_id is not None
        assert isinstance(message.timestamp, datetime)
        assert message.timestamp.tzinfo == timezone.utc

    def test_websocket_message_custom_values(self):
        """Test WebSocketMessage creation with custom values."""
        custom_timestamp = datetime.now(timezone.utc)
        custom_id = "custom-id-123"

        message = WebSocketMessage(
            message_type="custom",
            data={"custom": "data"},
            timestamp=custom_timestamp,
            message_id=custom_id,
        )

        assert message.timestamp == custom_timestamp
        assert message.message_id == custom_id

    def test_websocket_message_to_dict(self):
        """Test WebSocketMessage to_dict method."""
        message = WebSocketMessage(message_type="test", data={"key": "value"})
        message_dict = message.to_dict()

        assert message_dict["message_type"] == "test"
        assert message_dict["data"] == {"key": "value"}
        assert "timestamp" in message_dict
        assert "message_id" in message_dict

    def test_websocket_message_to_json(self):
        """Test WebSocketMessage to_json method."""
        message = WebSocketMessage(message_type="test", data={"key": "value"})
        json_str = message.to_json()

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["message_type"] == "test"
        assert parsed["data"] == {"key": "value"}


class TestWebSocketConnection:
    """Test WebSocketConnection dataclass."""

    def test_websocket_connection_creation(self):
        """Test WebSocketConnection creation."""
        mock_websocket = MagicMock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            tenant_id="tenant-123",
            user_id="user-456",
            connection_id="conn-789",
            connected_at=datetime.now(timezone.utc),
        )

        assert connection.tenant_id == "tenant-123"
        assert connection.user_id == "user-456"
        assert connection.connection_id == "conn-789"
        assert connection.websocket == mock_websocket
        assert connection.last_ping is None

    def test_websocket_connection_to_dict(self):
        """Test WebSocketConnection to_dict method."""
        mock_websocket = MagicMock()
        connected_at = datetime.now(timezone.utc)
        last_ping = datetime.now(timezone.utc)

        connection = WebSocketConnection(
            websocket=mock_websocket,
            tenant_id="tenant-123",
            user_id="user-456",
            connection_id="conn-789",
            connected_at=connected_at,
            last_ping=last_ping,
        )

        connection_dict = connection.to_dict()

        assert connection_dict["tenant_id"] == "tenant-123"
        assert connection_dict["user_id"] == "user-456"
        assert connection_dict["connection_id"] == "conn-789"
        assert connection_dict["connected_at"] == connected_at.isoformat()
        assert connection_dict["last_ping"] == last_ping.isoformat()


class TestWebSocketManager:
    """Test WebSocketManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh WebSocketManager instance for each test."""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        mock_ws = AsyncMock()
        mock_ws.client_state = WebSocketState.CONNECTED
        mock_ws.send_text = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.accept = AsyncMock()
        return mock_ws

    @pytest.mark.asyncio
    async def test_connect_new_connection(self, manager, mock_websocket):
        """Test accepting a new WebSocket connection."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        connection = await manager.connect(mock_websocket, tenant_id, user_id)

        assert connection.tenant_id == tenant_id
        assert connection.user_id == user_id
        assert connection.connection_id is not None
        assert connection.websocket == mock_websocket

        # Verify connection is stored
        assert tenant_id in manager.connections
        assert user_id in manager.connections[tenant_id]
        assert connection.connection_id in manager.connections[tenant_id][user_id]

        # Verify the websocket.accept was called
        mock_websocket.accept.assert_called_once()

        # Verify reverse lookup
        assert connection.connection_id in manager.connection_lookup
        assert manager.connection_lookup[connection.connection_id] == (
            tenant_id,
            user_id,
        )

        # Verify statistics
        assert manager.total_connections == 1

    @pytest.mark.asyncio
    async def test_disconnect_existing_connection(self, manager, mock_websocket):
        """Test disconnecting an existing WebSocket connection."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        # Create connection
        connection = await manager.connect(mock_websocket, tenant_id, user_id)
        connection_id = connection.connection_id

        # Disconnect
        await manager.disconnect(connection_id)

        # Verify connection is removed
        assert connection_id not in manager.connection_lookup
        assert tenant_id not in manager.connections

        # Verify statistics
        assert manager.total_disconnections == 1

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self, manager):
        """Test disconnecting a non-existent connection."""
        # Should not raise an error
        await manager.disconnect("nonexistent-id")

        # Verify no changes to statistics
        assert manager.total_disconnections == 0

    @pytest.mark.asyncio
    async def test_send_to_connection_success(self, manager, mock_websocket):
        """Test successfully sending a message to a connection."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        connection = await manager.connect(mock_websocket, tenant_id, user_id)
        message = WebSocketMessage(message_type="test", data={"key": "value"})

        await manager.send_to_connection(connection, message)

        # Verify message was sent (connection confirmation + test message = 2 calls)
        assert mock_websocket.send_text.call_count == 2
        # Get the last call (the test message)
        last_call_args = mock_websocket.send_text.call_args_list[-1]
        assert last_call_args[0][0] == message.to_json()
        assert (
            manager.total_messages_sent == 2
        )  # Connection confirmation + test message

    @pytest.mark.asyncio
    async def test_send_to_disconnected_connection(self, manager, mock_websocket):
        """Test sending to a disconnected connection."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        connection = await manager.connect(mock_websocket, tenant_id, user_id)
        message = WebSocketMessage(message_type="test", data={"key": "value"})

        # Simulate disconnected state
        mock_websocket.client_state = "DISCONNECTED"

        await manager.send_to_connection(connection, message)

        # Verify connection was cleaned up
        assert connection.connection_id not in manager.connection_lookup

    @pytest.mark.asyncio
    async def test_broadcast_to_user_single_connection(self, manager, mock_websocket):
        """Test broadcasting a message to a user with one connection."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        await manager.connect(mock_websocket, tenant_id, user_id)
        message = WebSocketMessage(message_type="broadcast", data={"key": "value"})

        await manager.broadcast_to_user(tenant_id, user_id, message)

        # Verify message was sent (connection confirmation + broadcast = 2 calls)
        assert mock_websocket.send_text.call_count >= 2
        # Get the last call (the broadcast)
        last_call_args = mock_websocket.send_text.call_args_list[-1]
        assert last_call_args[0][0] == message.to_json()

    @pytest.mark.asyncio
    async def test_broadcast_to_user_multiple_connections(self, manager):
        """Test broadcasting a message to a user with multiple connections."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        # Create multiple connections for the same user
        mock_ws1 = AsyncMock()
        mock_ws1.client_state = WebSocketState.CONNECTED
        mock_ws1.send_text = AsyncMock()
        mock_ws1.accept = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.client_state = WebSocketState.CONNECTED
        mock_ws2.send_text = AsyncMock()
        mock_ws2.accept = AsyncMock()

        await manager.connect(mock_ws1, tenant_id, user_id)
        await manager.connect(mock_ws2, tenant_id, user_id)

        message = WebSocketMessage(message_type="broadcast", data={"key": "value"})

        await manager.broadcast_to_user(tenant_id, user_id, message)

        # Verify message was sent to both connections (connection confirmation + broadcast = 2 calls each)
        assert mock_ws1.send_text.call_count >= 2
        assert mock_ws2.send_text.call_count >= 2
        # Get the last call for each (the broadcast)
        last_call_ws1 = mock_ws1.send_text.call_args_list[-1]
        last_call_ws2 = mock_ws2.send_text.call_args_list[-1]
        assert last_call_ws1[0][0] == message.to_json()
        assert last_call_ws2[0][0] == message.to_json()

    @pytest.mark.asyncio
    async def test_broadcast_to_tenant(self, manager):
        """Test broadcasting a message to all users in a tenant."""
        tenant_id = "tenant-123"

        # Create connections for different users
        mock_ws1 = AsyncMock()
        mock_ws1.client_state = WebSocketState.CONNECTED
        mock_ws1.send_text = AsyncMock()
        mock_ws1.accept = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.client_state = WebSocketState.CONNECTED
        mock_ws2.send_text = AsyncMock()
        mock_ws2.accept = AsyncMock()

        await manager.connect(mock_ws1, tenant_id, "user-1")
        await manager.connect(mock_ws2, tenant_id, "user-2")

        message = WebSocketMessage(
            message_type="tenant_broadcast", data={"key": "value"}
        )

        await manager.broadcast_to_tenant(tenant_id, message)

        # Verify message was sent to both users (connection confirmation + broadcast = 2 calls each)
        assert mock_ws1.send_text.call_count >= 2
        assert mock_ws2.send_text.call_count >= 2
        # Get the last call for each (the broadcast)
        last_call_ws1 = mock_ws1.send_text.call_args_list[-1]
        last_call_ws2 = mock_ws2.send_text.call_args_list[-1]
        assert last_call_ws1[0][0] == message.to_json()
        assert last_call_ws2[0][0] == message.to_json()

    @pytest.mark.asyncio
    async def test_send_notification(self, manager, mock_websocket):
        """Test sending a notification to a user."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        await manager.connect(mock_websocket, tenant_id, user_id)

        notification_data = {
            "notification_id": "notif-123",
            "message": "Test notification",
        }

        await manager.send_notification(tenant_id, user_id, notification_data)

        # Verify notification message was sent (connection confirmation + notification = 2 calls)
        assert mock_websocket.send_text.call_count >= 2
        # Get the last call (the notification)
        last_call_args = mock_websocket.send_text.call_args_list[-1]
        sent_data = json.loads(last_call_args[0][0])
        assert sent_data["message_type"] == "notification"
        assert sent_data["data"] == notification_data

    @pytest.mark.asyncio
    async def test_send_approval_request(self, manager, mock_websocket):
        """Test sending an approval request to a user."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        await manager.connect(mock_websocket, tenant_id, user_id)

        approval_data = {"approval_id": "approval-123", "tool_name": "test_tool"}

        await manager.send_approval_request(tenant_id, user_id, approval_data)

        # Verify approval message was sent (connection confirmation + approval = 2 calls)
        assert mock_websocket.send_text.call_count >= 2
        # Get the last call (the approval)
        last_call_args = mock_websocket.send_text.call_args_list[-1]
        sent_data = json.loads(last_call_args[0][0])
        assert sent_data["message_type"] == "approval"
        assert sent_data["data"] == approval_data

    @pytest.mark.asyncio
    async def test_ping_connection(self, manager, mock_websocket):
        """Test pinging a connection."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        connection = await manager.connect(mock_websocket, tenant_id, user_id)

        await manager.ping_connection(connection)

        # Verify ping message was sent (connection confirmation + ping = 2 calls)
        assert mock_websocket.send_text.call_count >= 2
        # Get the last call (the ping)
        last_call_args = mock_websocket.send_text.call_args_list[-1]
        sent_data = json.loads(last_call_args[0][0])
        assert sent_data["message_type"] == "ping"
        assert "timestamp" in sent_data["data"]

    @pytest.mark.asyncio
    async def test_handle_pong(self, manager, mock_websocket):
        """Test handling a pong response."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        connection = await manager.connect(mock_websocket, tenant_id, user_id)
        connection_id = connection.connection_id

        # Simulate pong response
        await manager.handle_pong(connection_id)

        # Verify last_ping was updated
        assert connection.last_ping is not None
        assert isinstance(connection.last_ping, datetime)

        # Reset the mock to clear previous calls for next tests
        mock_websocket.send_text.reset_mock()

    def test_get_connection_stats_empty(self, manager):
        """Test getting connection stats when no connections exist."""
        stats = manager.get_connection_stats()

        assert stats["active_connections"] == 0
        assert stats["tenants_with_connections"] == 0
        assert stats["total_connections_ever"] == 0
        assert stats["total_messages_sent"] == 0
        assert stats["total_disconnections"] == 0
        assert stats["tenant_stats"] == {}

    def test_get_connection_stats_with_connections(self, manager):
        """Test getting connection stats with active connections."""
        # Add some mock connections
        manager.connections["tenant-1"] = {"user-1": {"conn-1": MagicMock()}}
        manager.connections["tenant-2"] = {
            "user-2": {"conn-2": MagicMock()},
            "user-3": {"conn-3": MagicMock()},
        }
        manager.connection_lookup = {
            "conn-1": ("tenant-1", "user-1"),
            "conn-2": ("tenant-2", "user-2"),
            "conn-3": ("tenant-2", "user-3"),
        }
        manager.total_connections = 3
        manager.total_messages_sent = 10
        manager.total_disconnections = 2

        stats = manager.get_connection_stats()

        assert stats["active_connections"] == 3
        assert stats["tenants_with_connections"] == 2
        assert stats["total_connections_ever"] == 3
        assert stats["total_messages_sent"] == 10
        assert stats["total_disconnections"] == 2
        assert "tenant-1" in stats["tenant_stats"]
        assert "tenant-2" in stats["tenant_stats"]
        assert stats["tenant_stats"]["tenant-1"]["users"] == 1
        assert stats["tenant_stats"]["tenant-1"]["connections"] == 1
        assert stats["tenant_stats"]["tenant-2"]["users"] == 2
        assert stats["tenant_stats"]["tenant-2"]["connections"] == 2

    def test_get_user_connections_existing(self, manager):
        """Test getting connections for an existing user."""
        # Add mock connections
        mock_conn1 = MagicMock()
        mock_conn2 = MagicMock()
        manager.connections["tenant-1"] = {
            "user-1": {"conn-1": mock_conn1, "conn-2": mock_conn2}
        }

        connections = manager.get_user_connections("tenant-1", "user-1")

        assert len(connections) == 2
        assert mock_conn1 in connections
        assert mock_conn2 in connections

    def test_get_user_connections_nonexistent(self, manager):
        """Test getting connections for a non-existent user."""
        connections = manager.get_user_connections("tenant-1", "user-1")

        assert connections == []

    @pytest.mark.asyncio
    async def test_cleanup_stale_connections(self, manager):
        """Test cleaning up stale connections."""
        # Create a mock connection that starts connected but becomes disconnected
        mock_websocket = AsyncMock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.accept = AsyncMock()

        connection = await manager.connect(mock_websocket, "tenant-1", "user-1")

        # Verify connection exists
        assert connection.connection_id in manager.connection_lookup

        # Now simulate the connection becoming disconnected
        mock_websocket.client_state = WebSocketState.DISCONNECTED

        # Clean up stale connections
        await manager.cleanup_stale_connections()

        # Verify stale connection was removed
        assert connection.connection_id not in manager.connection_lookup


class TestGlobalWebSocketManager:
    """Test the global websocket_manager instance."""

    def test_global_instance_exists(self):
        """Test that the global websocket_manager instance exists."""
        assert websocket_manager is not None
        assert isinstance(websocket_manager, WebSocketManager)

    def test_global_instance_singleton(self):
        """Test that the global instance is a singleton."""
        from events.websocket_manager import websocket_manager as manager2

        assert websocket_manager is manager2
