"""Permission service for MCP Plexus tool access control."""

import uuid
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .models import ToolPermissionLevel, ToolPermissionResponse
from ..storage.sqlite_base import get_sqlite_db_connection
from ..tenants.storage_interfaces import AbstractTenantConfigStore
from ..dependencies import get_tenant_config_store_dependency

logger = logging.getLogger(__name__)


class PermissionService:
    """Service for managing tool permissions and approval requests."""

    def __init__(self):
        self._config_store: Optional[AbstractTenantConfigStore] = None

    async def _get_config_store(self) -> AbstractTenantConfigStore:
        """Get tenant config store instance."""
        if self._config_store is None:
            self._config_store = await get_tenant_config_store_dependency()
        return self._config_store

    async def check_tool_permission(
        self,
        entity_id: str,
        config_id: str,
        tool_name: str,
        tool_params: Dict[str, Any] = None,
    ) -> ToolPermissionResponse:
        """Check if config has permission to execute tool."""

        try:
            # Special handling for base config - full access to everything (even if not in database)
            if config_id == "base":
                return ToolPermissionResponse(
                    allowed=True,
                    permission_level=ToolPermissionLevel.FULL_ACCESS,
                    message="Full access granted",
                )

            # Get config permissions for non-base configs
            config_store = await self._get_config_store()
            config = await config_store.get_config_by_id(entity_id, config_id)

            if not config:
                return ToolPermissionResponse(
                    allowed=False,
                    permission_level=ToolPermissionLevel.NO_ACCESS,
                    message="Config not found",
                )

            # Get tool permissions from config settings
            tool_permissions = config.settings_json.get("tool_permissions", {})
            permission_level = tool_permissions.get(
                tool_name, ToolPermissionLevel.NO_ACCESS
            )

            if permission_level == ToolPermissionLevel.NO_ACCESS:
                return ToolPermissionResponse(
                    allowed=False,
                    permission_level=permission_level,
                    message="Tool access denied by config",
                )

            elif permission_level == ToolPermissionLevel.RESTRICTED_ACCESS:
                # Do not create approval during permission checks; only signal requirement.
                return ToolPermissionResponse(
                    allowed=True,
                    permission_level=permission_level,
                    approval_id=None,
                    message="This action requires user approval.",
                    requires_user_approval=True,
                )

            else:  # FULL_ACCESS
                return ToolPermissionResponse(
                    allowed=True,
                    permission_level=permission_level,
                    message="Full access granted",
                )

        except Exception as e:
            logger.error(f"Error checking tool permission: {e}", exc_info=True)
            return ToolPermissionResponse(
                allowed=False,
                permission_level=ToolPermissionLevel.NO_ACCESS,
                message=f"Permission check failed: {str(e)}",
            )

    async def create_approval_request(
        self,
        entity_id: str,
        requesting_config_id: str,
        tool_name: str,
        tool_params: Dict[str, Any],
    ) -> str:
        """Create approval request record."""

        try:
            db = await get_sqlite_db_connection()
            cursor = db.cursor()

            # Dedupe: reuse existing pending approval for same tool + params
            cursor.execute(
                """
                SELECT approval_id FROM tool_approval_requests
                WHERE entity_id = ? AND requesting_config_id = ? AND tool_name = ?
                  AND status = 'pending' AND tool_params = ?
                ORDER BY created_at DESC LIMIT 1
            """,
                (entity_id, requesting_config_id, tool_name, json.dumps(tool_params)),
            )
            row = cursor.fetchone()
            if row and row[0]:
                logger.info(f"Reusing pending approval {row[0]} for tool {tool_name}")
                return row[0]

            approval_id = str(uuid.uuid4())

            # Save to database
            cursor.execute(
                """
                INSERT INTO tool_approval_requests
                (approval_id, entity_id, requesting_config_id, approving_config_id,
                 tool_name, tool_params, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    approval_id,
                    entity_id,
                    requesting_config_id,
                    "base",  # Default approving config
                    tool_name,
                    json.dumps(tool_params),
                    "pending",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            db.commit()

            logger.info(f"Created approval request {approval_id} for tool {tool_name}")
            return approval_id

        except Exception as e:
            logger.error(f"Error creating approval request: {e}", exc_info=True)
            raise

    async def get_pending_approvals(
        self, entity_id: str, approving_config_id: str = "base"
    ) -> list:
        """Get pending approval requests for a config."""

        try:
            db = await get_sqlite_db_connection()
            cursor = db.cursor()

            cursor.execute(
                """
                SELECT * FROM tool_approval_requests
                WHERE entity_id = ? AND approving_config_id = ? AND status = 'pending'
                ORDER BY created_at DESC
            """,
                (entity_id, approving_config_id),
            )

            requests = cursor.fetchall()
            return [dict(row) for row in requests]

        except Exception as e:
            logger.error(f"Error getting pending approvals: {e}", exc_info=True)
            return []

    async def approve_request(
        self,
        approval_id: str,
        approver_entity_id: str,
        base_config_token: str,
        reason: str = "",
    ) -> bool:
        """Approve a tool request, execute it with base config token, and update status."""

        try:
            db = await get_sqlite_db_connection()
            cursor = db.cursor()

            # Get approval details first
            cursor.execute(
                """
                SELECT entity_id, requesting_config_id, tool_name, tool_params, tool_context
                FROM tool_approval_requests
                WHERE approval_id = ? AND entity_id = ? AND status = 'pending'
            """,
                (approval_id, approver_entity_id),
            )

            result = cursor.fetchone()
            if not result:
                logger.warning(f"No pending request found for approval {approval_id}")
                return False

            entity_id, requesting_config_id, tool_name, tool_params, tool_context = (
                result
            )

            # Update to approved status
            cursor.execute(
                """
                UPDATE tool_approval_requests
                SET status = 'approved', responded_at = ?, response_reason = ?
                WHERE approval_id = ?
            """,
                (datetime.now(timezone.utc).isoformat(), reason, approval_id),
            )

            db.commit()

            # Execute the approved tool with the provided base config token
            execution_success = await self._execute_approved_tool(
                entity_id, tool_name, tool_params, tool_context, base_config_token
            )

            # Update status to executed if successful
            if execution_success:
                cursor.execute(
                    """
                    UPDATE tool_approval_requests
                    SET status = 'executed'
                    WHERE approval_id = ?
                """,
                    (approval_id,),
                )
                db.commit()
                logger.info(f"Successfully executed approved request {approval_id}")
            else:
                logger.warning(f"Approved request {approval_id} execution failed")

            return True

        except Exception as e:
            logger.error(f"Error approving request: {e}", exc_info=True)
            return False

    async def _execute_approved_tool(
        self,
        entity_id: str,
        tool_name: str,
        tool_params: str,
        tool_context: Optional[str] = None,
        base_config_token: str = None,
    ) -> bool:
        """Execute an approved tool using the provided base config token."""
        try:
            # Import here to avoid circular imports
            from ...chatbot_api.main_processor import create_fresh_mcp_connection

            if not base_config_token:
                logger.error("No base config token provided for execution")
                return False

            # Parse tool parameters
            params = (
                json.loads(tool_params) if isinstance(tool_params, str) else tool_params
            )

            # Create MCP connection with base config token
            tools, session, stream = await create_fresh_mcp_connection(
                entity_id, base_config_token, "base"
            )

            try:
                # Execute the tool
                tool_result = await session.call_tool(tool_name, params)
                logger.info(
                    f"Successfully executed approved tool {tool_name} for {entity_id}: {tool_result}"
                )
                return True

            finally:
                # Clean up the connection
                if session:
                    await session.__aexit__(None, None, None)
                if stream:
                    await stream.__aexit__(None, None, None)

        except Exception as e:
            logger.error(f"Error executing approved tool {tool_name}: {e}")
            return False

    async def deny_request(
        self, approval_id: str, approver_entity_id: str, reason: str = None
    ) -> bool:
        """Deny a tool request."""

        try:
            db = await get_sqlite_db_connection()
            cursor = db.cursor()

            cursor.execute(
                """
                UPDATE tool_approval_requests
                SET status = 'denied', responded_at = ?, response_reason = ?
                WHERE approval_id = ? AND entity_id = ? AND status = 'pending'
            """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    reason,
                    approval_id,
                    approver_entity_id,
                ),
            )

            db.commit()

            if cursor.rowcount > 0:
                logger.info(f"Denied request {approval_id}: {reason}")
                return True
            else:
                logger.warning(f"No pending request found for approval {approval_id}")
                return False

        except Exception as e:
            logger.error(f"Error denying request: {e}", exc_info=True)
            return False

    async def get_approval_history(
        self, entity_id: str, approving_config_id: str = "base"
    ) -> list:
        """Get approval history for a config."""

        try:
            db = await get_sqlite_db_connection()
            cursor = db.cursor()

            cursor.execute(
                """
                SELECT * FROM tool_approval_requests
                WHERE entity_id = ? AND approving_config_id = ? AND status != 'pending'
                ORDER BY responded_at DESC
            """,
                (entity_id, approving_config_id),
            )

            requests = cursor.fetchall()
            return [dict(row) for row in requests]

        except Exception as e:
            logger.error(f"Error getting approval history: {e}", exc_info=True)
            return []
