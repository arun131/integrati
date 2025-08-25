"""Gmail MCP tools for email operations."""

import logging
from typing import Dict, Any, Optional
from fastmcp import Context as FastMCPBaseContext
from fastmcp.exceptions import ToolError
from mcp_plexus.core.global_registry import PLEXUS_SERVER_INSTANCE
from mcp_plexus.plexus_context import PlexusContext
from mcp_plexus.oauth.errors import PlexusExternalAuthRequiredError

from .api import GmailAPI
from ..utils import PermissionHelper

logger = logging.getLogger(__name__)

# Import constants from separate file to avoid circular imports


class GmailTools:
    """Class containing Gmail operations as MCP tools."""

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def search_gmail_messages(
        ctx: FastMCPBaseContext, query: str = "", max_results: int = 10
    ) -> Dict[str, Any]:
        """Search Gmail messages with the given query."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            # Get user ID from context (this would be set during MCP session initialization)
            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="search_gmail_messages",
                tool_params={"query": query, "max_results": max_results},
                no_access_response={
                    "messages": [],
                    "count": 0,
                    "query": query,
                    "max_results": max_results,
                    "status_message": "You don't have permission to search emails with this configuration.",
                },
                restricted_access_response={
                    "messages": [],
                    "count": 0,
                    "query": query,
                    "max_results": max_results,
                },
                approval_message=f"Your request to search emails with query '{query}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            gmail_api = GmailAPI(entity_id, user_id)
            messages = await gmail_api.search_messages(query, max_results)

            return {
                "messages": messages,
                "count": len(messages),
                "query": query,
                "max_results": max_results,
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error searching Gmail messages: {e}")
            raise ToolError(f"Error searching Gmail: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def get_last_received_email(ctx: FastMCPBaseContext) -> Dict[str, Any]:
        """Get the most recent received email."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="get_last_received_email",
                tool_params={},
                no_access_response={
                    "email": None,
                    "found": False,
                    "status_message": "You don't have permission to read emails with this configuration.",
                },
                restricted_access_response={
                    "email": None,
                    "found": False,
                },
                approval_message="Your request to get the last received email was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            gmail_api = GmailAPI(entity_id, user_id)
            email = await gmail_api.get_last_received_email()

            if email:
                return {"email": email, "found": True, "status_message": "success"}
            else:
                return {
                    "email": None,
                    "found": False,
                    "message": "No emails found in inbox",
                    "status_message": "success",
                }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error getting last received email: {e}")
            raise ToolError(f"Error getting last email: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def send_gmail_message(
        ctx: FastMCPBaseContext,
        to_email: str,
        subject: str,
        message_text: str,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a Gmail message."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            # Check permissions based on config_id (user_id)
            if user_id == "base":
                # Base config has full access - proceed with execution
                pass
            else:
                # Check permissions for non-base configs
                from mcp_plexus.permissions.service import PermissionService
                from mcp_plexus.permissions.models import ToolPermissionLevel

                permission_service = PermissionService()
                permission_response = await permission_service.check_tool_permission(
                    entity_id, user_id, "send_gmail_message"
                )

                if not permission_response.allowed:
                    # No access - return dummy response in same format
                    logger.info(
                        f"User {user_id} does not have permission to send emails"
                    )
                    return {
                        "status": "access_denied",
                        "message_id": None,
                        "thread_id": None,
                        "to_email": to_email,
                        "subject": subject,
                        "status_message": "You don't have permission to send emails with this configuration.",
                    }

                elif (
                    permission_response.permission_level
                    == ToolPermissionLevel.RESTRICTED_ACCESS
                ):
                    # Restricted access - create approval request and return dummy response
                    try:
                        approval_id = await permission_service.create_approval_request(
                            entity_id,
                            user_id,
                            "send_gmail_message",
                            {
                                "to_email": to_email,
                                "subject": subject,
                                "message_text": message_text,
                                "thread_id": thread_id,
                            },
                        )
                        logger.info(
                            f"Approval request created for send_gmail_message with ID: {approval_id}"
                        )

                        # Note: Approval request is automatically available to frontend via polling
                        # No separate notification needed since approval creation is sufficient

                        return {
                            "status": "approval_required",
                            "message_id": None,
                            "thread_id": None,
                            "to_email": to_email,
                            "subject": subject,
                            "status_message": f"Your request to send email '{subject}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                        }
                    except Exception as e:
                        logger.error(f"Failed to create approval request: {e}")
                        return {
                            "status": "approval_failed",
                            "message_id": None,
                            "thread_id": None,
                            "to_email": to_email,
                            "subject": subject,
                            "status_message": "Failed to create approval request for email sending.",
                        }

            # If we reach here, we have permission to execute
            gmail_api = GmailAPI(entity_id, user_id)
            result = await gmail_api.send_message(
                to_email, subject, message_text, thread_id
            )

            return {
                "status": "sent",
                "message_id": result["message_id"],
                "thread_id": result.get("thread_id"),
                "to_email": to_email,
                "subject": subject,
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error sending Gmail message: {e}")
            raise ToolError(f"Error sending Gmail: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def get_gmail_message(
        ctx: FastMCPBaseContext, message_id: str
    ) -> Dict[str, Any]:
        """Get a specific Gmail message by ID."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            # Check permissions based on config_id (user_id)
            if user_id == "base":
                # Base config has full access - proceed with execution
                pass
            else:
                # Check permissions for non-base configs
                from mcp_plexus.permissions.service import PermissionService

                permission_service = PermissionService()
                permission_response = await permission_service.check_tool_permission(
                    entity_id, user_id, "get_gmail_message"
                )

                if not permission_response.allowed:
                    # No access - return dummy response in same format
                    logger.info(
                        f"User {user_id} does not have permission to read emails"
                    )
                    return {
                        "message": None,
                        "found": False,
                        "status_message": "You don't have permission to read emails with this configuration.",
                    }

            gmail_api = GmailAPI(entity_id, user_id)
            message = await gmail_api.get_message(message_id)

            return {"message": message, "found": True, "status_message": "success"}
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error getting Gmail message: {e}")
            raise ToolError(f"Error getting Gmail message: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def get_unread_email_count(ctx: FastMCPBaseContext) -> Dict[str, Any]:
        """Get the count of unread emails."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            # Check permissions based on config_id (user_id)
            if user_id == "base":
                # Base config has full access - proceed with execution
                pass
            else:
                # Check permissions for non-base configs
                from mcp_plexus.permissions.service import PermissionService

                permission_service = PermissionService()
                permission_response = await permission_service.check_tool_permission(
                    entity_id, user_id, "get_unread_email_count"
                )

                if not permission_response.allowed:
                    # No access - return dummy response in same format
                    logger.info(
                        f"User {user_id} does not have permission to read email counts"
                    )
                    return {
                        "unread_count": 0,
                        "status": "access_denied",
                        "status_message": "You don't have permission to read email counts with this configuration.",
                    }

            gmail_api = GmailAPI(entity_id, user_id)
            count = await gmail_api.get_unread_count()

            return {
                "unread_count": count,
                "status": "success",
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            raise ToolError(f"Error getting unread count: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def search_gmail_by_sender(
        ctx: FastMCPBaseContext, sender_email: str, max_results: int = 10
    ) -> Dict[str, Any]:
        """Search Gmail messages from a specific sender."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            # Check permissions based on config_id (user_id)
            if user_id == "base":
                # Base config has full access - proceed with execution
                pass
            else:
                # Check permissions for non-base configs
                from mcp_plexus.permissions.service import PermissionService

                permission_service = PermissionService()
                permission_response = await permission_service.check_tool_permission(
                    entity_id, user_id, "search_gmail_by_sender"
                )

                if not permission_response.allowed:
                    # No access - return dummy response in same format
                    logger.info(
                        f"User {user_id} does not have permission to search emails by sender {sender_email}"
                    )
                    return {
                        "messages": [],
                        "count": 0,
                        "sender_email": sender_email,
                        "max_results": max_results,
                        "status_message": f"Request to search emails from {sender_email} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                    }

            query = f"from:{sender_email}"
            gmail_api = GmailAPI(entity_id, user_id)
            messages = await gmail_api.search_messages(query, max_results)

            return {
                "messages": messages,
                "count": len(messages),
                "sender_email": sender_email,
                "max_results": max_results,
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error searching Gmail by sender: {e}")
            raise ToolError(f"Error searching Gmail by sender: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def search_gmail_by_subject(
        ctx: FastMCPBaseContext, subject_keywords: str, max_results: int = 10
    ) -> Dict[str, Any]:
        """Search Gmail messages by subject keywords."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            # Check permissions based on config_id (user_id)
            if user_id == "base":
                # Base config has full access - proceed with execution
                pass
            else:
                # Check permissions for non-base configs
                from mcp_plexus.permissions.service import PermissionService

                permission_service = PermissionService()
                permission_response = await permission_service.check_tool_permission(
                    entity_id, user_id, "search_gmail_by_subject"
                )

                if not permission_response.allowed:
                    # No access - return dummy response in same format
                    logger.info(
                        f"User {user_id} does not have permission to search emails by subject {subject_keywords}"
                    )
                    return {
                        "messages": [],
                        "count": 0,
                        "subject_keywords": subject_keywords,
                        "max_results": max_results,
                        "status_message": f"Request to search emails by subject {subject_keywords} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                    }

            query = f"subject:{subject_keywords}"
            gmail_api = GmailAPI(entity_id, user_id)
            messages = await gmail_api.search_messages(query, max_results)

            return {
                "messages": messages,
                "count": len(messages),
                "subject_keywords": subject_keywords,
                "max_results": max_results,
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error searching Gmail by subject: {e}")
            raise ToolError(f"Error searching Gmail by subject: {str(e)}")
