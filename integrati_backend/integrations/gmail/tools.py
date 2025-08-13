"""Gmail MCP tools for email operations."""

import logging
from typing import Dict, Any, Optional
from fastmcp import Context as FastMCPBaseContext
from fastmcp.exceptions import ToolError
from mcp_plexus.core.global_registry import PLEXUS_SERVER_INSTANCE
from mcp_plexus.plexus_context import PlexusContext
from mcp_plexus.oauth.errors import PlexusExternalAuthRequiredError

from .api import GmailAPI

logger = logging.getLogger(__name__)


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

            gmail_api = GmailAPI(entity_id, user_id)
            messages = await gmail_api.search_messages(query, max_results)

            return {
                "messages": messages,
                "count": len(messages),
                "query": query,
                "max_results": max_results,
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

            gmail_api = GmailAPI(entity_id, user_id)
            email = await gmail_api.get_last_received_email()

            if email:
                return {"email": email, "found": True}
            else:
                return {
                    "email": None,
                    "found": False,
                    "message": "No emails found in inbox",
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

            gmail_api = GmailAPI(entity_id, user_id)
            message = await gmail_api.get_message(message_id)

            return {"message": message, "found": True}
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

            gmail_api = GmailAPI(entity_id, user_id)
            count = await gmail_api.get_unread_count()

            return {"unread_count": count, "status": "success"}
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

            query = f"from:{sender_email}"
            gmail_api = GmailAPI(entity_id, user_id)
            messages = await gmail_api.search_messages(query, max_results)

            return {
                "messages": messages,
                "count": len(messages),
                "sender_email": sender_email,
                "max_results": max_results,
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

            query = f"subject:{subject_keywords}"
            gmail_api = GmailAPI(entity_id, user_id)
            messages = await gmail_api.search_messages(query, max_results)

            return {
                "messages": messages,
                "count": len(messages),
                "subject_keywords": subject_keywords,
                "max_results": max_results,
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error searching Gmail by subject: {e}")
            raise ToolError(f"Error searching Gmail by subject: {str(e)}")
