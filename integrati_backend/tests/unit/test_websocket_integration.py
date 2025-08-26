"""Integration tests for WebSocket functionality."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from events.websocket_manager import WebSocketManager, WebSocketMessage
from events.websocket_endpoints import authenticate_websocket_user
from fastapi.websockets import WebSocketState


class TestWebSocketIntegrationFlow:
    """Test complete WebSocket integration flows."""

    @pytest.fixture
    def websocket_manager(self):
        """Create a fresh WebSocket manager for each test."""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.receive_text = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.client_state = WebSocketState.CONNECTED
        return mock_ws

    @pytest.mark.asyncio
    async def test_complete_notification_flow(self, websocket_manager, mock_websocket):
        """Test complete notification flow from connection to message delivery."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        # Step 1: Establish connection
        connection = await websocket_manager.connect(mock_websocket, tenant_id, user_id)

        # Verify connection was established
        assert connection.tenant_id == tenant_id
        assert connection.user_id == user_id
        assert connection.connection_id in websocket_manager.connection_lookup

        # Step 2: Send notification
        notification_data = {
            "notification_id": "notif-123",
            "message": "Test notification",
            "priority": "high",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await websocket_manager.send_notification(tenant_id, user_id, notification_data)

        # Verify notification was sent (connection confirmation + notification = 2 calls)
        assert mock_websocket.send_text.call_count >= 2
        # Get the last call (the notification)
        last_call_args = mock_websocket.send_text.call_args_list[-1]
        sent_message = json.loads(last_call_args[0][0])
        assert sent_message["message_type"] == "notification"
        assert sent_message["data"] == notification_data

        # Step 3: Verify connection stats
        stats = websocket_manager.get_connection_stats()
        assert stats["active_connections"] == 1
        assert stats["tenants_with_connections"] == 1
        assert (
            stats["total_messages_sent"] == 2
        )  # Connection confirmation + notification

        # Step 4: Clean up
        await websocket_manager.disconnect(connection.connection_id)

        # Verify connection was removed
        assert connection.connection_id not in websocket_manager.connection_lookup

        # Get updated stats after disconnection
        updated_stats = websocket_manager.get_connection_stats()
        assert updated_stats["total_disconnections"] == 1

    @pytest.mark.asyncio
    async def test_complete_approval_flow(self, websocket_manager, mock_websocket):
        """Test complete approval request flow."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        # Step 1: Establish connection
        connection = await websocket_manager.connect(mock_websocket, tenant_id, user_id)

        # Step 2: Send approval request
        approval_data = {
            "approval_id": "approval-123",
            "tool_name": "email_sender",
            "parameters": {"recipient": "user@example.com", "subject": "Test"},
            "priority": "urgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await websocket_manager.send_approval_request(tenant_id, user_id, approval_data)

        # Verify approval was sent (connection confirmation + approval = 2 calls)
        assert mock_websocket.send_text.call_count >= 2
        # Get the last call (the approval)
        last_call_args = mock_websocket.send_text.call_args_list[-1]
        sent_message = json.loads(last_call_args[0][0])
        assert sent_message["message_type"] == "approval"
        assert sent_message["data"] == approval_data

        # Step 3: Clean up
        await websocket_manager.disconnect(connection.connection_id)

    @pytest.mark.asyncio
    async def test_multi_user_tenant_broadcasting(self, websocket_manager):
        """Test broadcasting messages to multiple users in a tenant."""
        tenant_id = "tenant-123"

        # Create multiple users with connections
        mock_ws1 = AsyncMock()
        mock_ws1.client_state = WebSocketState.CONNECTED
        mock_ws1.send_text = AsyncMock()
        mock_ws1.accept = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.client_state = WebSocketState.CONNECTED
        mock_ws2.send_text = AsyncMock()
        mock_ws2.accept = AsyncMock()

        mock_ws3 = AsyncMock()
        mock_ws3.client_state = WebSocketState.CONNECTED
        mock_ws3.send_text = AsyncMock()
        mock_ws3.accept = AsyncMock()

        # Connect users
        await websocket_manager.connect(mock_ws1, tenant_id, "user-1")
        await websocket_manager.connect(mock_ws2, tenant_id, "user-2")
        await websocket_manager.connect(mock_ws3, tenant_id, "user-3")

        # Broadcast to entire tenant
        broadcast_message = WebSocketMessage(
            message_type="tenant_announcement",
            data={"message": "System maintenance scheduled"},
        )

        await websocket_manager.broadcast_to_tenant(tenant_id, broadcast_message)

        # Verify all users received the message (connection confirmation + broadcast = 2 calls each)
        assert mock_ws1.send_text.call_count >= 2
        assert mock_ws2.send_text.call_count >= 2
        assert mock_ws3.send_text.call_count >= 2
        # Get the last call for each (the broadcast)
        last_call_ws1 = mock_ws1.send_text.call_args_list[-1]
        last_call_ws2 = mock_ws2.send_text.call_args_list[-1]
        last_call_ws3 = mock_ws3.send_text.call_args_list[-1]
        assert last_call_ws1[0][0] == broadcast_message.to_json()
        assert last_call_ws2[0][0] == broadcast_message.to_json()
        assert last_call_ws3[0][0] == broadcast_message.to_json()

        # Verify stats
        stats = websocket_manager.get_connection_stats()
        assert stats["active_connections"] == 3
        assert stats["tenants_with_connections"] == 1
        assert stats["tenant_stats"][tenant_id]["users"] == 3
        assert stats["tenant_stats"][tenant_id]["connections"] == 3

    @pytest.mark.asyncio
    async def test_connection_lifecycle_with_ping_pong(
        self, websocket_manager, mock_websocket
    ):
        """Test connection lifecycle including ping/pong mechanism."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        # Step 1: Connect
        connection = await websocket_manager.connect(mock_websocket, tenant_id, user_id)

        # Step 2: Send ping
        await websocket_manager.ping_connection(connection)

        # Verify ping was sent (connection confirmation + ping = 2 calls)
        assert mock_websocket.send_text.call_count >= 2
        # Get the last call (the ping)
        last_call_args = mock_websocket.send_text.call_args_list[-1]
        ping_message = json.loads(last_call_args[0][0])
        assert ping_message["message_type"] == "ping"
        assert "timestamp" in ping_message["data"]

        # Step 3: Simulate pong response
        await websocket_manager.handle_pong(connection.connection_id)

        # Verify last_ping was updated
        assert connection.last_ping is not None
        assert isinstance(connection.last_ping, datetime)

        # Step 4: Disconnect
        await websocket_manager.disconnect(connection.connection_id)

        # Verify cleanup
        assert connection.connection_id not in websocket_manager.connection_lookup

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, websocket_manager):
        """Test that tenants are properly isolated from each other."""
        tenant_1 = "tenant-1"
        tenant_2 = "tenant-2"
        user_id = "user-123"

        # Create connections in different tenants
        mock_ws1 = AsyncMock()
        mock_ws1.client_state = WebSocketState.CONNECTED
        mock_ws1.send_text = AsyncMock()
        mock_ws1.accept = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.client_state = WebSocketState.CONNECTED
        mock_ws2.send_text = AsyncMock()
        mock_ws2.accept = AsyncMock()

        await websocket_manager.connect(mock_ws1, tenant_1, user_id)
        await websocket_manager.connect(mock_ws2, tenant_2, user_id)

        # Send message to tenant 1 only
        message = WebSocketMessage(message_type="test", data={"tenant": "tenant-1"})
        await websocket_manager.broadcast_to_user(tenant_1, user_id, message)

        # Verify only tenant 1 user received the message (connection confirmation + message = 2 calls)
        assert mock_ws1.send_text.call_count >= 2
        assert mock_ws2.send_text.call_count >= 1  # Only the connection confirmation
        # Get the last call for tenant 1 (the message)
        last_call_ws1 = mock_ws1.send_text.call_args_list[-1]
        assert last_call_ws1[0][0] == message.to_json()

        # Verify tenant isolation in stats
        stats = websocket_manager.get_connection_stats()
        assert stats["tenants_with_connections"] == 2
        assert tenant_1 in stats["tenant_stats"]
        assert tenant_2 in stats["tenant_stats"]
        assert stats["tenant_stats"][tenant_1]["users"] == 1
        assert stats["tenant_stats"][tenant_2]["users"] == 1

    @pytest.mark.asyncio
    async def test_connection_cleanup_on_disconnect(
        self, websocket_manager, mock_websocket
    ):
        """Test proper cleanup when connections are disconnected."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        # Connect
        connection = await websocket_manager.connect(mock_websocket, tenant_id, user_id)
        connection_id = connection.connection_id

        # Verify connection exists
        assert connection_id in websocket_manager.connection_lookup
        assert tenant_id in websocket_manager.connections
        assert user_id in websocket_manager.connections[tenant_id]
        assert connection_id in websocket_manager.connections[tenant_id][user_id]

        # Disconnect
        await websocket_manager.disconnect(connection_id)

        # Verify complete cleanup
        assert connection_id not in websocket_manager.connection_lookup
        assert tenant_id not in websocket_manager.connections

        # Verify stats updated
        stats = websocket_manager.get_connection_stats()
        assert stats["active_connections"] == 0
        assert stats["tenants_with_connections"] == 0

    @pytest.mark.asyncio
    async def test_multiple_connections_per_user(self, websocket_manager):
        """Test that a user can have multiple active connections."""
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

        mock_ws3 = AsyncMock()
        mock_ws3.client_state = WebSocketState.CONNECTED
        mock_ws3.send_text = AsyncMock()
        mock_ws3.accept = AsyncMock()

        # Connect all
        await websocket_manager.connect(mock_ws1, tenant_id, user_id)
        await websocket_manager.connect(mock_ws2, tenant_id, user_id)
        await websocket_manager.connect(mock_ws3, tenant_id, user_id)

        # Verify all connections exist
        user_connections = websocket_manager.get_user_connections(tenant_id, user_id)
        assert len(user_connections) == 3

        # Send message to user (should go to all connections)
        message = WebSocketMessage(message_type="test", data={"message": "Hello"})
        await websocket_manager.broadcast_to_user(tenant_id, user_id, message)

        # Verify all connections received the message (connection confirmation + message = 2 calls each)
        assert mock_ws1.send_text.call_count >= 2
        assert mock_ws2.send_text.call_count >= 2
        assert mock_ws3.send_text.call_count >= 2

        # Verify stats
        stats = websocket_manager.get_connection_stats()
        assert stats["tenant_stats"][tenant_id]["users"] == 1
        assert stats["tenant_stats"][tenant_id]["connections"] == 3

    @pytest.mark.asyncio
    async def test_error_handling_in_message_sending(
        self, websocket_manager, mock_websocket
    ):
        """Test error handling when sending messages fails."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        # Connect
        connection = await websocket_manager.connect(mock_websocket, tenant_id, user_id)

        # Simulate send failure
        mock_websocket.send_text.side_effect = Exception("Send failed")

        # Try to send message
        message = WebSocketMessage(message_type="test", data={"key": "value"})
        await websocket_manager.send_to_connection(connection, message)

        # Verify connection was cleaned up due to error
        assert connection.connection_id not in websocket_manager.connection_lookup

        # Verify stats updated
        stats = websocket_manager.get_connection_stats()
        assert stats["active_connections"] == 0
        assert stats["total_disconnections"] == 1

    @pytest.mark.asyncio
    async def test_websocket_state_validation(self, websocket_manager):
        """Test WebSocket state validation during operations."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        # Create connection with disconnected state
        mock_ws = AsyncMock()
        mock_ws.client_state = "DISCONNECTED"
        mock_ws.send_text = AsyncMock()

        connection = await websocket_manager.connect(mock_ws, tenant_id, user_id)

        # Try to send message to disconnected connection
        message = WebSocketMessage(message_type="test", data={"key": "value"})
        await websocket_manager.send_to_connection(connection, message)

        # Verify connection was cleaned up
        assert connection.connection_id not in websocket_manager.connection_lookup


class TestWebSocketAuthenticationIntegration:
    """Test WebSocket authentication integration."""

    @pytest.mark.asyncio
    async def test_authentication_with_valid_credentials(self):
        """Test authentication flow with valid credentials."""
        tenant_id = "tenant-123"
        token = "valid-token-123"

        # Mock successful authentication
        mock_token_data = MagicMock()
        mock_token_data.entity_id = tenant_id
        mock_token_data.persistent_user_id = "user-456"

        mock_token_store = AsyncMock()
        mock_token_store.get_token_data_by_hash.return_value = mock_token_data
        mock_token_store.update_token_last_used = AsyncMock()

        mock_token_manager = MagicMock()
        mock_token_manager.hash_token.return_value = "hashed-token"

        with (
            patch(
                "mcp_plexus.plexus_auth.sqlite_user_auth_token_store.get_sqlite_plexus_user_auth_token_store",
                return_value=mock_token_store,
            ),
            patch(
                "mcp_plexus.plexus_auth.token_manager.DefaultPlexusUserTokenManager",
                return_value=mock_token_manager,
            ),
        ):
            result = await authenticate_websocket_user(tenant_id, token)

            # Verify authentication succeeded
            assert result is not None
            assert result["entity_id"] == tenant_id
            assert result["persistent_user_id"] == "user-456"

            # Verify token was validated and updated
            mock_token_store.get_token_data_by_hash.assert_called_once_with(
                "hashed-token"
            )
            mock_token_store.update_token_last_used.assert_called_once_with(
                "hashed-token"
            )

    @pytest.mark.asyncio
    async def test_authentication_tenant_validation(self):
        """Test that authentication validates tenant access."""
        tenant_id = "tenant-123"
        token = "valid-token-456"

        # Mock token for different tenant
        mock_token_data = MagicMock()
        mock_token_data.entity_id = "different-tenant"
        mock_token_data.persistent_user_id = "user-456"

        mock_token_store = AsyncMock()
        mock_token_store.get_token_data_by_hash.return_value = mock_token_data

        mock_token_manager = MagicMock()
        mock_token_manager.hash_token.return_value = "hashed-token"

        with (
            patch(
                "mcp_plexus.plexus_auth.sqlite_user_auth_token_store.get_sqlite_plexus_user_auth_token_store",
                return_value=mock_token_store,
            ),
            patch(
                "mcp_plexus.plexus_auth.token_manager.DefaultPlexusUserTokenManager",
                return_value=mock_token_manager,
            ),
        ):
            result = await authenticate_websocket_user(tenant_id, token)

            # Verify authentication failed due to tenant mismatch
            assert result is None

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self):
        """Test authentication error handling."""
        tenant_id = "tenant-123"
        token = "valid-token-123"

        # Mock authentication failure
        mock_token_store = AsyncMock()
        mock_token_store.get_token_data_by_hash.side_effect = Exception(
            "Database connection failed"
        )

        mock_token_manager = MagicMock()
        mock_token_manager.hash_token.return_value = "hashed-token"

        with (
            patch(
                "mcp_plexus.plexus_auth.sqlite_user_auth_token_store.get_sqlite_plexus_user_auth_token_store",
                return_value=mock_token_store,
            ),
            patch(
                "mcp_plexus.plexus_auth.token_manager.DefaultPlexusUserTokenManager",
                return_value=mock_token_manager,
            ),
        ):
            result = await authenticate_websocket_user(tenant_id, token)

            # Verify authentication failed gracefully
            assert result is None
