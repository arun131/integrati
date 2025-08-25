"""Utility functions for integration tools."""

import logging
from typing import Dict, Any, Optional
from mcp_plexus.permissions.models import ToolPermissionLevel

logger = logging.getLogger(__name__)


class PermissionHelper:
    """Helper class for handling permission checks and responses in integration tools."""

    @staticmethod
    async def check_and_handle_permissions(
        entity_id: str,
        user_id: str,
        tool_name: str,
        tool_params: Dict[str, Any],
        no_access_response: Dict[str, Any],
        restricted_access_response: Dict[str, Any],
        approval_message: str,
        integration_type: str = "unknown",
    ) -> Optional[Dict[str, Any]]:
        """
        Check permissions and return appropriate response if access is denied or restricted.
        Returns None if user has full access and should proceed with execution.

        Args:
            entity_id: The tenant entity ID
            user_id: The user/config ID
            tool_name: Name of the tool being called
            tool_params: Parameters passed to the tool
            no_access_response: Response to return when user has no access
            restricted_access_response: Base response to return when user needs approval
            approval_message: Message to show when approval is required
            integration_type: Type of integration (gmail, calendar, etc.)

        Returns:
            Dict if access is denied/restricted, None if user has full access
        """
        if user_id == "base":
            # Base config has full access - proceed with execution
            return None

        # Check permissions for non-base configs
        from mcp_plexus.permissions.service import PermissionService

        permission_service = PermissionService()
        permission_response = await permission_service.check_tool_permission(
            entity_id, user_id, tool_name
        )

        if not permission_response.allowed:
            # No access - return dummy response
            logger.info(f"User {user_id} does not have permission to use {tool_name}")
            return no_access_response

        elif (
            permission_response.permission_level
            == ToolPermissionLevel.RESTRICTED_ACCESS
        ):
            # Restricted access - create approval request and return dummy response
            try:
                approval_id = await permission_service.create_approval_request(
                    entity_id, user_id, tool_name, tool_params
                )
                logger.info(
                    f"Approval request created for {tool_name} with ID: {approval_id}"
                )

                # Note: Approval request is automatically available to frontend via polling
                # No separate notification needed since approval creation is sufficient

                # Update the restricted access response with the approval message
                response = restricted_access_response.copy()
                response["status_message"] = approval_message
                return response

            except Exception as e:
                logger.error(f"Failed to create approval request: {e}")
                # Update the restricted access response with failure message
                response = restricted_access_response.copy()
                response["status_message"] = (
                    f"Failed to create approval request for {tool_name}."
                )
                return response

        # Full access - proceed with execution
        return None
