"""Helper functions for background agent management and config creation."""

import logging
import uuid
from datetime import datetime, timezone


from mcp_plexus.tenants.models import TenantConfigCreate
from mcp_plexus.dependencies import get_tenant_config_store_dependency
from mcp_plexus.plexus_auth.sqlite_user_auth_token_store import (
    get_sqlite_plexus_user_auth_token_store,
)
from mcp_plexus.plexus_auth.token_manager import DefaultPlexusUserTokenManager
from mcp_plexus.plexus_auth.models import PlexusUserAuthTokenData
from integrations.gmail.constants import GMAIL_DEFAULT_BACKGROUND_PERMISSIONS
from integrations.calendar.constants import CALENDAR_DEFAULT_BACKGROUND_PERMISSIONS
from integrations.common.constants import COMMON_DEFAULT_BACKGROUND_PERMISSIONS

logger = logging.getLogger(__name__)


async def save_user_notification(
    tenant_id: str,
    user_id: str,
    notification_text: str,
    integration_type: str,
    agent_used: str,
    event_details: dict = None,
    tools_used: list = None,
    reasoning: str = None,
    priority: str = "normal",
) -> bool:
    """Save a user notification to the database and broadcast via WebSocket."""
    try:
        from analytics.database import AnalyticsDatabase
        from analytics.models import UserNotification

        db = AnalyticsDatabase()

        notification_id = str(uuid.uuid4())
        notification = UserNotification(
            entity_id=tenant_id,
            user_id=user_id,
            notification_id=notification_id,
            notification_text=notification_text,
            integration_type=integration_type,
            agent_used=agent_used,
            priority=priority,
            timestamp=datetime.now(timezone.utc),
            is_read=False,
            event_details=event_details,
            tools_used=tools_used,
            reasoning=reasoning,
        )

        success = await db.insert_user_notification(notification)
        if success:
            logger.info(f"Saved notification for user {user_id} in tenant {tenant_id}")

            # Broadcast via WebSocket
            try:
                from events.websocket_manager import websocket_manager

                notification_data = {
                    "notification_id": notification_id,
                    "notification_text": notification_text,
                    "integration_type": integration_type,
                    "agent_used": agent_used,
                    "priority": priority,
                    "timestamp": notification.timestamp.isoformat(),
                    "is_read": False,
                    "event_details": event_details,
                    "tools_used": tools_used,
                    "reasoning": reasoning,
                }

                await websocket_manager.send_notification(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    notification_data=notification_data,
                )
                logger.debug(
                    f"Broadcasted notification via WebSocket to user {user_id}"
                )
            except Exception as ws_error:
                logger.error(
                    f"Failed to broadcast notification via WebSocket: {ws_error}"
                )
                # Don't fail the whole operation if WebSocket broadcast fails
        else:
            logger.error(
                f"Failed to save notification for user {user_id} in tenant {tenant_id}"
            )

        return success
    except Exception as e:
        logger.error(f"Error saving user notification: {e}", exc_info=True)
        return False


async def ensure_background_agent_config(tenant_id: str) -> str:
    """Ensure background agent config exists with restricted permissions and return its token."""

    try:
        config_store = await get_tenant_config_store_dependency()
        background_config_id = "background_agent"

        existing_config = await config_store.get_config_by_id(
            tenant_id, background_config_id
        )

        if not existing_config:
            # Create with restrictive permissions using tool-defined defaults
            background_config = TenantConfigCreate(
                entity_id=tenant_id,
                config_id=background_config_id,
                config_name="Background Agent Profile",
                config_type="background_agent",
                is_default=False,
                settings_json={
                    "tool_permissions": {
                        **COMMON_DEFAULT_BACKGROUND_PERMISSIONS,
                        **GMAIL_DEFAULT_BACKGROUND_PERMISSIONS,
                        **CALENDAR_DEFAULT_BACKGROUND_PERMISSIONS,
                    },
                    "agent_behavior": {
                        "max_email_summary_length": 200,
                        "include_attachments": False,
                        "priority_keywords": ["urgent", "important", "asap"],
                    },
                },
            )

            await config_store.create_config(background_config)
            logger.info(f"Created background agent config for tenant {tenant_id}")

        # Get existing or create new token for background config
        return await get_or_create_config_token(tenant_id, background_config_id)

    except Exception as e:
        logger.error(f"Error ensuring background agent config: {e}", exc_info=True)
        raise


async def get_or_create_config_token(tenant_id: str, config_id: str) -> str:
    """Get existing token for a config or create a new one if it doesn't exist."""

    try:
        token_manager = DefaultPlexusUserTokenManager()
        token_store = await get_sqlite_plexus_user_auth_token_store()

        # Check if token already exists for this config
        existing_token_data = await token_store.get_token_data_by_user_id(
            tenant_id, config_id
        )

        if existing_token_data:
            # Update last used timestamp for existing token
            await token_store.update_token_last_used(existing_token_data.token_hash)
            logger.info(
                f"Retrieved existing token for config {config_id} in tenant {tenant_id}"
            )

            # Since we can't reverse the hash, we need to generate a new token
            # but keep the same config association for consistency
            new_token, new_hash = token_manager.generate_token_and_hash()
            existing_token_data.token_hash = new_hash
            existing_token_data.last_used_at = datetime.now(timezone.utc).isoformat()
            await token_store.save_token_data(existing_token_data)

            return new_token
        else:
            # Create new token for this config
            new_token, new_hash = token_manager.generate_token_and_hash()

            token_data = PlexusUserAuthTokenData(
                entity_id=tenant_id,
                persistent_user_id=config_id,
                token_hash=new_hash,
                created_at=datetime.now(timezone.utc).isoformat(),
                last_used_at=datetime.now(timezone.utc).isoformat(),
            )

            await token_store.save_token_data(token_data)
            logger.info(
                f"Created new token for config {config_id} in tenant {tenant_id}"
            )

            return new_token

    except Exception as e:
        logger.error(f"Error getting/creating config token: {e}", exc_info=True)
        raise


async def process_background_request(
    tenant_id: str,
    user_id: str,
    integration_type: str,
    event_details: dict,
    user_context: dict = None,
):
    """Process background events using background agent config."""
    from .main_processor import configure_dspy_once, create_fresh_mcp_connection
    from integrations.gmail.agents_def import get_gmail_agent
    from integrations.calendar.agents_def import get_calendar_agent
    import dspy

    try:
        if not configure_dspy_once():
            return {"success": False, "error": "LLM not configured"}

        with dspy.context():
            # Ensure background agent config exists and get token
            background_token = await ensure_background_agent_config(tenant_id)

            # Create MCP connection with background config
            mcp_tools, mcp_session, mcp_stream = await create_fresh_mcp_connection(
                tenant_id, background_token, config_id="background_agent"
            )

            if not mcp_tools or not mcp_session:
                return {"success": False, "error": "Failed to establish MCP connection"}

            # Convert MCP tools to DSPy tools
            import dspy

            dspy_tools = [
                dspy.Tool.from_mcp_tool(mcp_session, tool) for tool in mcp_tools
            ]

            # Create the appropriate background agent
            if integration_type == "gmail":
                agent = get_gmail_agent(dspy_tools, trigger="background")
            elif integration_type == "calendar":
                agent = get_calendar_agent(dspy_tools, trigger="background")
            else:
                return {
                    "success": False,
                    "error": f"Unsupported integration: {integration_type}",
                }

            # Execute the background agent
            response = await agent.aforward(
                event_details=event_details, user_context=user_context or {}
            )

            # Log the full background agent response for debugging
            logger.info("=== BACKGROUND AGENT RESPONSE ===")
            logger.info(f"Full response: {response}")
            logger.info("=== END BACKGROUND AGENT RESPONSE ===")

            # Save notification if the agent generated one
            notification_text = (
                response.personalized_notification
                if hasattr(response, "personalized_notification")
                else ""
            )
            if notification_text and notification_text.strip():
                logger.info(f"📧 NOTIFICATION GENERATED: {notification_text}")
                await save_user_notification(
                    tenant_id=tenant_id,
                    # Save under the 'base' user so frontend (which authenticates as 'base') can see it
                    user_id="base",
                    notification_text=notification_text,
                    integration_type=integration_type,
                    agent_used=f"{integration_type}_background_agent",
                    event_details=event_details,
                    tools_used=getattr(response, "tools_used", []),
                    reasoning=getattr(response, "reasoning", ""),
                )
            else:
                logger.warning(
                    f"⚠️ NO NOTIFICATION GENERATED: response.personalized_notification = '{notification_text}'"
                )

            logger.info(
                f"Background agent processed {integration_type} event for tenant {tenant_id}"
            )

            return {
                "success": True,
                "personalized_notification": notification_text,
                "agent_used": f"{integration_type}_background_agent",
                "tools_used": getattr(response, "tools_used", []),
                "reasoning": getattr(response, "reasoning", ""),
            }

    except Exception as e:
        logger.error(f"Failed to process background request: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

    finally:
        # Clean up MCP connections
        if "mcp_session" in locals() and mcp_session:
            try:
                await mcp_session.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing MCP session: {e}")

        if "mcp_stream" in locals() and mcp_stream:
            try:
                await mcp_stream.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing MCP stream: {e}")
