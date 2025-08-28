"""WebSocket Manager for real-time notifications and approvals."""

import json
import logging
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import defaultdict

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """Represents a single WebSocket connection."""

    websocket: WebSocket
    tenant_id: str
    user_id: str
    connection_id: str
    connected_at: datetime
    last_ping: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "connection_id": self.connection_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat() if self.last_ping else None,
        }


@dataclass
class WebSocketMessage:
    """Represents a WebSocket message."""

    message_type: str  # 'notification', 'approval', 'ping', 'pong', 'connection_status'
    data: Dict[str, Any]
    timestamp: datetime = None
    message_id: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class WebSocketManager:
    """
    Manages WebSocket connections for real-time notifications and approvals.
    Provides tenant-based isolation and connection lifecycle management.
    """

    def __init__(self):
        # Tenant-based connection storage: {tenant_id: {user_id: {connection_id: WebSocketConnection}}}
        self.connections: Dict[str, Dict[str, Dict[str, WebSocketConnection]]] = (
            defaultdict(lambda: defaultdict(dict))
        )
        # Reverse lookup: {connection_id: (tenant_id, user_id)}
        self.connection_lookup: Dict[str, tuple[str, str]] = {}

        # Statistics
        self.total_connections = 0
        self.total_messages_sent = 0
        self.total_disconnections = 0

    async def connect(
        self, websocket: WebSocket, tenant_id: str, user_id: str
    ) -> WebSocketConnection:
        """
        Accept a new WebSocket connection and register it.

        Args:
            websocket: The WebSocket connection
            tenant_id: Tenant identifier
            user_id: User identifier

        Returns:
            WebSocketConnection: The registered connection object
        """
        try:
            await websocket.accept()
            logger.info(f"WebSocket accepted for tenant: {tenant_id}, user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection: {e}")
            raise

        connection_id = str(uuid.uuid4())
        connection = WebSocketConnection(
            websocket=websocket,
            tenant_id=tenant_id,
            user_id=user_id,
            connection_id=connection_id,
            connected_at=datetime.now(timezone.utc),
        )

        # Store connection
        self.connections[tenant_id][user_id][connection_id] = connection
        self.connection_lookup[connection_id] = (tenant_id, user_id)
        self.total_connections += 1

        logger.info(
            f"WebSocket connected: tenant={tenant_id}, user={user_id}, "
            f"connection_id={connection_id[:8]}..."
        )

        # Send connection confirmation
        await self.send_to_connection(
            connection,
            WebSocketMessage(
                message_type="connection_status",
                data={
                    "status": "connected",
                    "connection_id": connection_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                },
            ),
        )

        return connection

    async def disconnect(self, connection_id: str):
        """
        Disconnect and remove a WebSocket connection.

        Args:
            connection_id: Unique connection identifier
        """
        if connection_id not in self.connection_lookup:
            logger.warning(
                f"Attempted to disconnect unknown connection: {connection_id}"
            )
            return

        tenant_id, user_id = self.connection_lookup[connection_id]

        # Remove from connections
        if (
            tenant_id in self.connections
            and user_id in self.connections[tenant_id]
            and connection_id in self.connections[tenant_id][user_id]
        ):
            connection = self.connections[tenant_id][user_id][connection_id]

            # Close WebSocket if still open
            if connection.websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.websocket.close()
                except Exception as e:
                    logger.error(f"Error closing WebSocket: {e}")

            # Remove from storage
            del self.connections[tenant_id][user_id][connection_id]

            # Clean up empty dictionaries
            if not self.connections[tenant_id][user_id]:
                del self.connections[tenant_id][user_id]
            if not self.connections[tenant_id]:
                del self.connections[tenant_id]

        # Remove from reverse lookup
        del self.connection_lookup[connection_id]
        self.total_disconnections += 1

        logger.info(
            f"WebSocket disconnected: tenant={tenant_id}, user={user_id}, "
            f"connection_id={connection_id[:8]}..."
        )

    async def send_to_connection(
        self, connection: WebSocketConnection, message: WebSocketMessage
    ):
        """
        Send a message to a specific connection.

        Args:
            connection: The WebSocket connection
            message: The message to send
        """
        if connection.websocket.client_state != WebSocketState.CONNECTED:
            logger.warning(
                f"Attempted to send message to disconnected WebSocket: "
                f"{connection.connection_id[:8]}..."
            )
            await self.disconnect(connection.connection_id)
            return

        try:
            await connection.websocket.send_text(message.to_json())
            self.total_messages_sent += 1
            logger.debug(
                f"Message sent to {connection.connection_id[:8]}...: "
                f"{message.message_type}"
            )
        except Exception as e:
            logger.error(
                f"Error sending message to {connection.connection_id[:8]}...: {e}"
            )
            await self.disconnect(connection.connection_id)

    async def broadcast_to_user(
        self, tenant_id: str, user_id: str, message: WebSocketMessage
    ):
        """
        Broadcast a message to all connections for a specific user.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            message: The message to broadcast
        """
        if (
            tenant_id not in self.connections
            or user_id not in self.connections[tenant_id]
        ):
            logger.debug(
                f"No connections found for user {user_id} in tenant {tenant_id}"
            )
            return

        connections = list(self.connections[tenant_id][user_id].values())
        disconnected_connections = []

        for connection in connections:
            try:
                await self.send_to_connection(connection, message)
            except Exception as e:
                logger.error(
                    f"Error broadcasting to connection {connection.connection_id[:8]}...: {e}"
                )
                disconnected_connections.append(connection.connection_id)

        # Clean up disconnected connections
        for connection_id in disconnected_connections:
            await self.disconnect(connection_id)

    async def broadcast_to_tenant(
        self,
        tenant_id: str,
        message: WebSocketMessage,
        exclude_user_id: Optional[str] = None,
    ):
        """
        Broadcast a message to all users in a tenant.

        Args:
            tenant_id: Tenant identifier
            message: The message to broadcast
            exclude_user_id: Optional user ID to exclude from broadcast
        """
        if tenant_id not in self.connections:
            logger.debug(f"No connections found for tenant {tenant_id}")
            return

        user_ids = list(self.connections[tenant_id].keys())
        if exclude_user_id:
            user_ids = [uid for uid in user_ids if uid != exclude_user_id]

        for user_id in user_ids:
            await self.broadcast_to_user(tenant_id, user_id, message)

    async def send_notification(
        self, tenant_id: str, user_id: str, notification_data: Dict[str, Any]
    ):
        """
        Send a notification to a specific user.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            notification_data: Notification data
        """
        message = WebSocketMessage(message_type="notification", data=notification_data)
        await self.broadcast_to_user(tenant_id, user_id, message)

    async def send_approval_request(
        self, tenant_id: str, user_id: str, approval_data: Dict[str, Any]
    ):
        """
        Send an approval request to a specific user.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            approval_data: Approval request data
        """
        message = WebSocketMessage(message_type="approval", data=approval_data)
        await self.broadcast_to_user(tenant_id, user_id, message)

    async def ping_connection(self, connection: WebSocketConnection):
        """
        Send a ping message to a connection to check if it's alive.

        Args:
            connection: The WebSocket connection to ping
        """
        ping_message = WebSocketMessage(
            message_type="ping",
            data={"timestamp": datetime.now(timezone.utc).isoformat()},
        )
        await self.send_to_connection(connection, ping_message)

    async def handle_pong(self, connection_id: str):
        """
        Handle a pong response from a connection.

        Args:
            connection_id: The connection that sent the pong
        """
        if connection_id in self.connection_lookup:
            tenant_id, user_id = self.connection_lookup[connection_id]
            if (
                tenant_id in self.connections
                and user_id in self.connections[tenant_id]
                and connection_id in self.connections[tenant_id][user_id]
            ):
                connection = self.connections[tenant_id][user_id][connection_id]
                connection.last_ping = datetime.now(timezone.utc)
                logger.debug(f"Pong received from {connection_id[:8]}...")

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics.

        Returns:
            Dict containing connection statistics
        """
        active_connections = len(self.connection_lookup)
        tenants_with_connections = len(self.connections)

        tenant_stats = {}
        for tenant_id, tenant_connections in self.connections.items():
            user_count = len(tenant_connections)
            connection_count = sum(
                len(user_conns) for user_conns in tenant_connections.values()
            )
            tenant_stats[tenant_id] = {
                "users": user_count,
                "connections": connection_count,
            }

        return {
            "active_connections": active_connections,
            "tenants_with_connections": tenants_with_connections,
            "total_connections_ever": self.total_connections,
            "total_messages_sent": self.total_messages_sent,
            "total_disconnections": self.total_disconnections,
            "tenant_stats": tenant_stats,
        }

    def get_user_connections(
        self, tenant_id: str, user_id: str
    ) -> List[WebSocketConnection]:
        """
        Get all connections for a specific user.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier

        Returns:
            List of WebSocketConnection objects
        """
        if (
            tenant_id not in self.connections
            or user_id not in self.connections[tenant_id]
        ):
            return []

        return list(self.connections[tenant_id][user_id].values())

    async def cleanup_stale_connections(self):
        """
        Clean up stale connections that are no longer responsive.
        This should be called periodically by a background task.
        """
        stale_connections = []

        for tenant_id, tenant_connections in self.connections.items():
            for user_id, user_connections in tenant_connections.items():
                for connection_id, connection in user_connections.items():
                    if connection.websocket.client_state != WebSocketState.CONNECTED:
                        stale_connections.append(connection_id)

        for connection_id in stale_connections:
            await self.disconnect(connection_id)

        if stale_connections:
            logger.info(f"Cleaned up {len(stale_connections)} stale connections")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
