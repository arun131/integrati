"""WebSocket endpoints for real-time notifications and approvals."""

import json
import logging
from typing import Dict, Any, Optional

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    HTTPException,
    Query,
)
from fastapi.responses import JSONResponse

from mcp_plexus.plexus_auth.dependencies import get_current_plexus_user_from_token
from .websocket_manager import websocket_manager, WebSocketMessage
from chatbot_api.background_agent_helper import save_user_notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["WebSocket Events"])


async def authenticate_websocket_user(
    tenant_id: str, token: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user for WebSocket connection.

    Args:
        tenant_id: Tenant identifier
        token: Authentication token

    Returns:
        User data if authenticated, None otherwise
    """
    if not token:
        return None

    try:
        # Use the existing Plexus authentication system
        from mcp_plexus.plexus_auth.sqlite_user_auth_token_store import (
            get_sqlite_plexus_user_auth_token_store,
        )
        from mcp_plexus.plexus_auth.token_manager import DefaultPlexusUserTokenManager

        token_store = await get_sqlite_plexus_user_auth_token_store()
        token_manager = DefaultPlexusUserTokenManager()

        token_hash = token_manager.hash_token(token)
        token_data = await token_store.get_token_data_by_hash(token_hash)

        if token_data and token_data.entity_id == tenant_id:
            await token_store.update_token_last_used(token_hash)
            return {
                "entity_id": token_data.entity_id,
                "persistent_user_id": token_data.persistent_user_id,
            }

        return None
    except Exception as e:
        logger.error(f"Error authenticating WebSocket user: {e}")
        return None


@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    tenant_id: str,
    token: Optional[str] = Query(None, description="Authentication token"),
):
    """
    WebSocket endpoint for real-time notifications and approvals.

    Args:
        websocket: WebSocket connection
        tenant_id: Tenant identifier
        token: Authentication token (required)
    """
    connection = None

    try:
        # Authenticate user
        user_data = await authenticate_websocket_user(tenant_id, token)
        if not user_data:
            await websocket.close(code=4001, reason="Authentication required")
            return

        user_id = user_data["persistent_user_id"]

        # Connect to WebSocket manager
        connection = await websocket_manager.connect(websocket, tenant_id, user_id)

        logger.info(
            f"WebSocket connection established for user {user_id} in tenant {tenant_id}"
        )

        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()

                try:
                    message_data = json.loads(data)
                except json.JSONDecodeError:
                    logger.warning(
                        f"Invalid JSON received from {connection.connection_id[:8]}..."
                    )
                    continue

                # Handle different message types
                message_type = message_data.get("message_type", "unknown")

                if message_type == "ping":
                    # Respond to ping with pong
                    pong_message = WebSocketMessage(
                        message_type="pong",
                        data={
                            "timestamp": message_data.get("data", {}).get("timestamp")
                        },
                    )
                    await websocket_manager.send_to_connection(connection, pong_message)

                elif message_type == "pong":
                    # Update connection's last ping time
                    await websocket_manager.handle_pong(connection.connection_id)

                elif message_type == "subscribe":
                    # Handle subscription to specific event types
                    event_types = message_data.get("data", {}).get("event_types", [])
                    logger.info(f"User {user_id} subscribed to events: {event_types}")

                    # Send subscription confirmation
                    confirm_message = WebSocketMessage(
                        message_type="subscription_confirmed",
                        data={"event_types": event_types},
                    )
                    await websocket_manager.send_to_connection(
                        connection, confirm_message
                    )

                else:
                    logger.warning(f"Unknown message type received: {message_type}")

            except WebSocketDisconnect:
                logger.info(
                    f"WebSocket disconnected for user {user_id} in tenant {tenant_id}"
                )
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected during setup for tenant {tenant_id}")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=4000, reason="Internal server error")
        except Exception:
            pass
    finally:
        # Clean up connection
        if connection:
            await websocket_manager.disconnect(connection.connection_id)


@router.get("/connections")
async def get_connection_status(
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
):
    """
    Get WebSocket connection statistics.

    Returns:
        Connection statistics and status
    """
    try:
        stats = websocket_manager.get_connection_stats()
        tenant_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        # Get user-specific connection info
        user_connections = websocket_manager.get_user_connections(tenant_id, user_id)
        user_connection_info = [conn.to_dict() for conn in user_connections]

        return {
            "status": "success",
            "global_stats": stats,
            "user_connections": user_connection_info,
            "user_connection_count": len(user_connections),
        }
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/test/notification")
async def test_notification_broadcast(
    tenant_id: str = Query(..., description="Tenant ID"),
    user_id: str = Query(
        None, description="User ID (optional, uses current user if not provided)"
    ),
    message: str = Query(..., description="Test notification message"),
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
):
    """
    Test endpoint to send a notification via WebSocket.

    Args:
        tenant_id: Target tenant ID
        user_id: Target user ID (optional)
        message: Test message content
        current_user: Authenticated user
    """
    try:
        # Use provided user_id or default to current user
        target_user_id = user_id or current_user["persistent_user_id"]

        # Validate tenant access
        if tenant_id != current_user["entity_id"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Can only send notifications within your tenant",
            )

        # Create notification data
        notification_data = {
            "notification_id": f"test-{websocket_manager.total_messages_sent + 1}",
            "notification_text": message,
            "integration_type": "test",
            "agent_used": "test_endpoint",
            "priority": "normal",
            "timestamp": WebSocketMessage(
                message_type="test", data={}
            ).timestamp.isoformat(),
            "is_read": False,
            "event_details": {
                "source": "test_endpoint",
                "tenant_id": tenant_id,
                "target_user_id": target_user_id,
            },
        }

        # Save to database
        await save_user_notification(
            tenant_id=tenant_id,
            user_id=target_user_id,
            notification_text=message,
            integration_type="test",
            agent_used="test_endpoint",
            priority="normal",
        )

        # Send via WebSocket
        await websocket_manager.send_notification(
            tenant_id=tenant_id,
            user_id=target_user_id,
            notification_data=notification_data,
        )

        # Get connection stats for response
        user_connections = websocket_manager.get_user_connections(
            tenant_id, target_user_id
        )

        return {
            "status": "success",
            "message": "Test notification sent",
            "notification_data": notification_data,
            "websocket_connections": len(user_connections),
            "target_tenant": tenant_id,
            "target_user": target_user_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/test/approval")
async def test_approval_broadcast(
    tenant_id: str = Query(..., description="Tenant ID"),
    user_id: str = Query(
        None, description="User ID (optional, uses current user if not provided)"
    ),
    tool_name: str = Query(default="test_tool", description="Tool name for approval"),
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
):
    """
    Test endpoint to send an approval request via WebSocket.

    Args:
        tenant_id: Target tenant ID
        user_id: Target user ID (optional)
        tool_name: Tool name for the approval request
        current_user: Authenticated user
    """
    try:
        # Use provided user_id or default to current user
        target_user_id = user_id or current_user["persistent_user_id"]

        # Validate tenant access
        if tenant_id != current_user["entity_id"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Can only send approvals within your tenant",
            )

        # Create approval data
        approval_data = {
            "approval_id": f"test-approval-{websocket_manager.total_messages_sent + 1}",
            "tool_name": tool_name,
            "tool_description": f"Test approval request for {tool_name}",
            "parameters": {"test_param": "test_value"},
            "reasoning": "This is a test approval request sent via WebSocket",
            "priority": "normal",
            "timestamp": WebSocketMessage(
                message_type="test", data={}
            ).timestamp.isoformat(),
            "status": "pending",
            "tenant_id": tenant_id,
            "user_id": target_user_id,
        }

        # Send via WebSocket
        await websocket_manager.send_approval_request(
            tenant_id=tenant_id, user_id=target_user_id, approval_data=approval_data
        )

        # Get connection stats for response
        user_connections = websocket_manager.get_user_connections(
            tenant_id, target_user_id
        )

        return {
            "status": "success",
            "message": "Test approval request sent",
            "approval_data": approval_data,
            "websocket_connections": len(user_connections),
            "target_tenant": tenant_id,
            "target_user": target_user_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test approval: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/health")
async def websocket_health():
    """
    Health check endpoint for WebSocket service.

    Returns:
        WebSocket service health status
    """
    try:
        stats = websocket_manager.get_connection_stats()

        return {
            "status": "healthy",
            "service": "websocket_events",
            "connections": stats,
            "timestamp": WebSocketMessage(
                message_type="health", data={}
            ).timestamp.isoformat(),
        }
    except Exception as e:
        logger.error(f"WebSocket health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "websocket_events",
                "error": str(e),
                "timestamp": WebSocketMessage(
                    message_type="health", data={}
                ).timestamp.isoformat(),
            },
        )
