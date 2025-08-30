"""Gmail MCP tools for email operations."""

import logging
from typing import Dict, Any, Optional, List
from fastmcp import Context as FastMCPBaseContext
from fastmcp.exceptions import ToolError
from mcp_plexus.core.global_registry import PLEXUS_SERVER_INSTANCE
from mcp_plexus.plexus_context import PlexusContext
from mcp_plexus.oauth.errors import PlexusExternalAuthRequiredError

from .api import GmailAPI
from ..utils import PermissionHelper

logger = logging.getLogger(__name__)

# Import constants from separate file to avoid circular imports


# ============================================================================
# HELPER FUNCTIONS (copied from test_gmail_api.py)
# ============================================================================


def _normalize_keywords(keywords: Optional[List[str]]) -> List[str]:
    """Normalize keywords list by trimming whitespace and dropping empties."""
    if not keywords:
        return []
    normalized = []
    for term in keywords:
        if not term:
            continue
        t = str(term).strip()
        if t:
            normalized.append(t)
    return normalized


def _quote_if_needed(term: str) -> str:
    """Quote the term if it contains whitespace."""
    return f'"{term}"' if any(c.isspace() for c in term) else term


def _build_gmail_query_from_keywords(
    keywords: Optional[List[str]],
    email_addresses: Optional[List[str]] = None,
    timerange_days: Optional[int] = None,
) -> str:
    """Build a Gmail query that searches subject, body, from, to, cc for any keywords.

    - Tokens that look like operators (contain ':') are passed through as-is.
    - Plain tokens are expanded across subject/body/from/to/cc using OR groups.
    - Email addresses are added as from:address filters.
    - Date filter uses newer_than:Nd when provided.
    """
    parts: List[str] = []

    # Keyword expansion
    for raw in _normalize_keywords(keywords):
        # Treat operator-like tokens as-is (e.g., has:attachment, from:google)
        if ":" in raw and not any(ch.isspace() for ch in raw):
            parts.append(raw)
            continue

        term = _quote_if_needed(raw)
        group = [
            f"subject:{term}",
            term,  # bare term -> subject/body
            f"from:{term}",
            f"to:{term}",
            f"cc:{term}",
        ]
        parts.append("(" + " OR ".join(group) + ")")

    # Email address filters
    if email_addresses:
        for addr in email_addresses:
            a = str(addr).strip()
            if a:
                parts.append(f"from:{a}")

    # Date range
    if timerange_days and timerange_days > 0:
        parts.append(f"newer_than:{timerange_days}d")

    return " ".join(parts).strip()


def _extract_relevant_section(
    subject: str, body: str, keywords: List[str], context_chars: int = 200
) -> str:
    """Extract a relevant section around the first occurrence of any keyword.

    Searches body first, then subject if body doesn't contain any keyword.
    Returns up to context_chars before and after the match. If no keywords are
    found, returns the first 2*context_chars of body (or subject fallback).
    """
    haystack_primary = body or ""
    haystack_secondary = subject or ""

    # Helper to find first match index and length
    def find_first(hay: str) -> Optional[tuple]:
        if not hay:
            return None
        low = hay.lower()
        best_idx = None
        best_len = 0
        for kw in _normalize_keywords(keywords):
            k = kw.lower().strip()
            if not k:
                continue
            idx = low.find(k)
            if idx != -1 and (best_idx is None or idx < best_idx):
                best_idx = idx
                best_len = len(k)
        return (best_idx, best_len) if best_idx is not None else None

    target_text = haystack_primary
    match = find_first(haystack_primary)
    if match is None:
        match = find_first(haystack_secondary)
        target_text = haystack_secondary

    if match is None:
        # Fallback
        text = haystack_primary or haystack_secondary
        text = text.strip()
        if not text:
            return ""
        max_len = context_chars * 2
        return text[:max_len] + ("..." if len(text) > max_len else "")

    idx, match_len = match
    start = max(0, idx - context_chars)
    end = min(len(target_text), idx + match_len + context_chars)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(target_text) else ""
    return prefix + target_text[start:end] + suffix


class GmailTools:
    """Class containing Gmail operations as MCP tools."""

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def search_emails(
        ctx: FastMCPBaseContext,
        keywords: Optional[List[str]] = None,
        email_addresses: Optional[List[str]] = None,
        timerange_days: Optional[int] = 30,
        max_results: int = 10,
        detailed: bool = False,
    ) -> List[Dict[str, Any]]:
        """Search emails and return results in snapshot or detailed format. Always use snapshot mode unless you need the full email content. Default is snapshot mode.

        This function provides flexible email search capabilities across Gmail. In snapshot mode (default),
        it returns lightweight summaries with relevant sections extracted from email content. In detailed mode,
        it returns full email content with complete metadata.

        Usage:
        - Provide simple keywords like ["gemini", "google"]; the wrapper will search subject, body, from, to, and cc.
        - You can also pass Gmail operators directly (e.g., ["has:attachment", "from:gmail.com"]).
        - Optionally filter by specific sender addresses via email_addresses, and/or by a relative date range.

        Args:
            keywords: List of terms and/or Gmail operators. Plain terms are expanded across subject/body/from/to/cc fields.
            email_addresses: Optional list of sender email addresses to include (added as from:address filters).
            timerange_days: Optional integer for Gmail newer_than:Nd filter (e.g., 7 for last 7 days) default is 30 days.
            max_results: Maximum number of results to return (default: 10).
            detailed: If True, return full email content with metadata. If False (default), return lightweight snapshots with relevant sections.

        Returns:
            List of email dictionaries. Format depends on the 'detailed' parameter:

            Snapshot mode (detailed=False):
            - id: Email message ID
            - subject: Email subject line
            - datetime: Email date/timestamp
            - from: Sender email address
            - relevant_section: Extracted relevant content section (up to 400 chars around keyword matches)

            Detailed mode (detailed=True):
            - id: Email message ID
            - subject: Email subject line
            - from: Sender email address
            - to: Recipient email addresses
            - date: Email date/timestamp
            - body: Full email body content
            - attachments: Number of attachments
            - labels: Gmail labels applied to the email
        """
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
                tool_name="search_emails",
                tool_params={
                    "keywords": keywords,
                    "email_addresses": email_addresses,
                    "timerange_days": timerange_days,
                    "max_results": max_results,
                    "detailed": detailed,
                },
                no_access_response=[],
                restricted_access_response=[],
                approval_message=f"Your request to search emails with keywords '{keywords}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            gmail_api = GmailAPI(entity_id, user_id)

            # Build search query
            query = _build_gmail_query_from_keywords(
                keywords, email_addresses, timerange_days
            )

            # If no query specified, get recent emails without search
            if not query.strip():
                result = await gmail_api.get_inbox_emails(max_results=max_results)
            else:
                # Search emails
                result = await gmail_api.search_emails(query, max_results)

            messages = result.get("messages", [])

            # Ensure newest-first ordering (also enforced in API layer)
            messages = sorted(
                messages, key=lambda m: int(m.get("internal_date") or 0), reverse=True
            )

            if detailed:
                # Return full emails with metadata using parsed message data
                detailed_emails = []
                for msg in messages:
                    subject = msg.get("subject", "").strip() or "No Subject"

                    detailed_emails.append(
                        {
                            "id": msg.get("id"),
                            "subject": subject,
                            "from": msg.get("from", "Unknown"),
                            "to": msg.get("to", "Unknown"),
                            "date": msg.get("date", "Unknown"),
                            "body": msg.get("body", ""),
                            "attachments": len(msg.get("attachments", [])),
                            "labels": msg.get("label_ids", []),
                        }
                    )
                return detailed_emails
            else:
                # Create lightweight snapshot using the parsed message data
                snapshot = []
                for msg in messages:
                    # The Gmail API already parses the message, so we can access the fields directly
                    subject = msg.get("subject", "").strip() or "No Subject"
                    body = msg.get("body", "").strip()
                    relevant = _extract_relevant_section(
                        subject, body, _normalize_keywords(keywords), context_chars=200
                    )

                    snapshot.append(
                        {
                            "id": msg.get("id"),
                            "subject": subject,
                            "datetime": msg.get("date", "Unknown"),
                            "from": msg.get("from", "Unknown"),
                            "relevant_section": relevant,
                        }
                    )
                return snapshot
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            raise ToolError(f"Error searching emails: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def get_last_received_email_with_attachments(
        ctx: FastMCPBaseContext, label: str = "INBOX"
    ) -> Dict[str, Any]:
        """Get the most recent email (by label) including attachments list.

        Args:
        - label: One of "INBOX", "SENT", or any custom label.

        Returns: Dict with id, subject, from, date, body, attachments (list), labels.
        """
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
                tool_name="get_last_received_email_with_attachments",
                tool_params={"label": label},
                no_access_response={
                    "id": None,
                    "subject": "Access Denied",
                    "from": "Unknown",
                    "date": "Unknown",
                    "body": "",
                    "attachments": [],
                    "labels": [],
                    "status_message": "You don't have permission to read emails with this configuration.",
                },
                restricted_access_response={
                    "id": None,
                    "subject": "Approval Required",
                    "from": "Unknown",
                    "date": "Unknown",
                    "body": "",
                    "attachments": [],
                    "labels": [],
                    "status_message": f"The tool request with details {{'label': '{label}'}} is sent to the user and they can approve it on the app.",
                },
                approval_message=f"Your request to get the last email from '{label}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            gmail_api = GmailAPI(entity_id, user_id)

            if label == "INBOX":
                result = await gmail_api.get_inbox_emails(max_results=1)
            elif label == "SENT":
                result = await gmail_api.get_sent_emails(max_results=1)
            else:
                result = await gmail_api.search_emails(f"label:{label}", max_results=1)

            messages = result.get("messages", [])
            if not messages:
                return {}

            message = messages[0]
            return {
                "id": message.get("id"),
                "subject": message.get("subject", "No Subject"),
                "from": message.get("from", "Unknown"),
                "date": message.get("date", "Unknown"),
                "body": message.get("body", ""),
                "attachments": message.get("attachments", []),
                "labels": message.get("label_ids", []),
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error getting last received email with attachments: {e}")
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
        """Send a Gmail message to specified recipient.

        This function allows sending emails through Gmail with optional thread support.
        Requires appropriate permissions for email sending operations.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            message_text: Email body content (plain text)
            thread_id: Optional Gmail thread ID to reply to existing conversation
        """
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
                tool_name="send_gmail_message",
                tool_params={
                    "to_email": to_email,
                    "subject": subject,
                    "message_text": message_text,
                    "thread_id": thread_id,
                },
                no_access_response={
                    "status": "access_denied",
                    "message_id": None,
                    "thread_id": None,
                    "to_email": to_email,
                    "subject": subject,
                    "status_message": "You don't have permission to send emails with this configuration.",
                },
                restricted_access_response={
                    "status": "approval_required",
                    "message_id": None,
                    "thread_id": None,
                    "to_email": to_email,
                    "subject": subject,
                    "status_message": f"The tool request with details {{'to_email': '{to_email}', 'subject': '{subject}'}} is sent to the user and they can approve it on the app.",
                },
                approval_message=f"Your request to send email '{subject}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

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
        """Retrieve a specific Gmail message by its ID.

        This function fetches a complete email message including all its metadata,
        content, and attachments. Requires read permissions for Gmail access.

        Args:
            message_id: Gmail message ID to retrieve

        Returns:
            Dict containing:
            - message: Full message object with content and metadata
            - found: Boolean indicating if message was found
            - status_message: Operation status ("success", "access_denied", etc.)
        """
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
                tool_name="get_gmail_message",
                tool_params={"message_id": message_id},
                no_access_response={
                    "message": None,
                    "found": False,
                    "status_message": "You don't have permission to read emails with this configuration.",
                },
                restricted_access_response={
                    "message": None,
                    "found": False,
                    "status_message": f"The tool request with details {{'message_id': '{message_id}'}} is sent to the user and they can approve it on the app.",
                },
                approval_message=f"Your request to retrieve email '{message_id}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            gmail_api = GmailAPI(entity_id, user_id)
            message = await gmail_api.get_email(message_id)

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
    async def reply_to_email(
        ctx: FastMCPBaseContext,
        message_id: str,
        text: str,
        attachments: Optional[List[str]] = None,
        to: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
    ) -> str:
        """Reply to a message, optionally adding attachments and overriding recipients.

        Args:
        - message_id: The Gmail message ID to reply to.
        - text: Plaintext body to include in reply.
        - attachments: Optional list of file paths.
        - to: Optional list of recipient addresses (override default reply-to).
        - cc: Optional list of CC addresses.

        Returns: New reply message ID (str) on success, empty string otherwise.
        """
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
                tool_name="reply_to_email",
                tool_params={
                    "message_id": message_id,
                    "text": text,
                    "attachments": attachments,
                    "to": to,
                    "cc": cc,
                },
                no_access_response="",
                restricted_access_response="",
                approval_message=f"Your request to reply to email '{message_id}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            gmail_api = GmailAPI(entity_id, user_id)
            result = await gmail_api.reply_to_email(
                message_id=message_id,
                body=text,
                body_type="text",
                to=to,
                cc=cc,
                attachments=attachments,
            )
            return result.get("id", "")
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error in reply_to_email: {e}")
            raise ToolError(f"Error replying to email: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def forward_email_and_reply(
        ctx: FastMCPBaseContext,
        message_id: str,
        text: str,
        attachments: Optional[List[str]] = None,
        to: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
    ) -> str:
        """Forward an email to the authenticated user, with additional text and optional recipients.

        Args:
        - message_id: Gmail message ID to forward.
        - text: Plaintext body to include in forward.
        - attachments: Optional list of file paths to attach.
        - to: Optional list of additional To recipients.
        - cc: Optional list of CC recipients.
        """
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
                tool_name="forward_email_and_reply",
                tool_params={
                    "message_id": message_id,
                    "text": text,
                    "attachments": attachments,
                    "to": to,
                    "cc": cc,
                },
                no_access_response="",
                restricted_access_response="",
                approval_message=f"Your request to forward email '{message_id}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            gmail_api = GmailAPI(entity_id, user_id)

            # Get user's email for self-forwarding
            profile = await gmail_api.get_profile()
            user_email = profile.get("email_address", "")

            result = await gmail_api.forward_email(
                message_id=message_id,
                to=user_email if not to else to,
                body=text,
                body_type="text",
                cc=cc,
                attachments=attachments,
            )
            return result.get("id", "")
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error in forward_email_and_reply: {e}")
            raise ToolError(f"Error forwarding email: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def retrieve_specific_email_thread(
        ctx: FastMCPBaseContext, message_id: str
    ) -> Dict[str, Any]:
        """Retrieve an email or thread with detailed information including attachments."""
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
                tool_name="retrieve_specific_email_thread",
                tool_params={"message_id": message_id},
                no_access_response={
                    "message": None,
                    "thread_messages": [],
                    "thread_id": None,
                    "has_attachments": False,
                    "status_message": "You don't have permission to retrieve email threads with this configuration.",
                },
                restricted_access_response={
                    "message": None,
                    "thread_messages": [],
                    "thread_id": None,
                    "has_attachments": False,
                    "status_message": f"The tool request with details {{'message_id': '{message_id}'}} is sent to the user and they can approve it on the app.",
                },
                approval_message=f"Your request to retrieve email thread '{message_id}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            gmail_api = GmailAPI(entity_id, user_id)

            # Get the message
            message = await gmail_api.get_email(message_id)

            # Get thread if available
            thread_id = message.get("thread_id")
            thread_messages = []
            if thread_id:
                thread_result = await gmail_api.get_email_threads(thread_id)
                thread_messages = thread_result.get("messages", [])

            return {
                "message": message,
                "thread_messages": thread_messages,
                "thread_id": thread_id,
                "has_attachments": len(message.get("attachments", [])) > 0,
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error in retrieve_specific_email_thread: {e}")
            raise ToolError(f"Error retrieving email thread: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def get_unread_email_count(ctx: FastMCPBaseContext) -> Dict[str, Any]:
        """Get the count of unread emails in the Gmail inbox.

        This function returns the total number of unread emails across all labels.
        Requires read permissions for Gmail access.
        """
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
                tool_name="get_unread_email_count",
                tool_params={},
                no_access_response={
                    "unread_count": 0,
                    "status": "access_denied",
                    "status_message": "You don't have permission to read email counts with this configuration.",
                },
                restricted_access_response={
                    "unread_count": 0,
                    "status": "approval_required",
                    "status_message": "The tool request with details {'action': 'get_unread_email_count'} is sent to the user and they can approve it on the app.",
                },
                approval_message="Your request to get unread email count was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

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
    async def retrieve_emails_by_label_snapshot(
        ctx: FastMCPBaseContext,
        label_name: str,
        daterange: str = "1d",
        keywords: Optional[List[str]] = None,
        email_address_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve emails by labels. Labels could be a custom label. If you are not sure about the label name, you can use the label_emails tool to find or create the label.

        Usage:
        - Example: retrieve_emails_by_label_snapshot("AI_relabeled", "1w", ["gemini"]).
        - Example: retrieve_emails_by_label_snapshot("AI_relabeled", "1m", ["gemini"], ["noreply@google.com"]).
        Args:
        - label_name: Gmail label name (e.g., "INBOX", custom label).
        - daterange: One of {"1d", "1w", "1m"}; converted to newer_than. Default is 1 day.
        - keywords: List of terms/operators. Plain terms are expanded across subject/body/from/to/cc. Default is None.
        - email_address_filter: Optional list of sender addresses. Default is None.

        Returns: List of snapshot dicts with id, subject, datetime, from, relevant_section.
        """
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
                tool_name="retrieve_emails_by_label_snapshot",
                tool_params={
                    "label_name": label_name,
                    "daterange": daterange,
                    "keywords": keywords,
                    "email_address_filter": email_address_filter,
                },
                no_access_response=[],
                restricted_access_response=[],
                approval_message=f"Your request to retrieve emails by label '{label_name}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            gmail_api = GmailAPI(entity_id, user_id)

            # Base label and date filters
            parts = [f"label:{label_name}"]
            if daterange:
                if daterange in {"1d", "1w", "1m"}:
                    parts.append(f"newer_than:{daterange}")
            # Keywords and address filters
            query_expanded = _build_gmail_query_from_keywords(
                keywords, email_address_filter, None
            )
            if query_expanded:
                parts.append(query_expanded)
            query = " ".join(parts)

            # Search emails
            result = await gmail_api.search_emails(query, max_results=20)
            messages = result.get("messages", [])

            # Create snapshot aligned to new shape
            snapshot = []
            for msg in messages:
                subject = msg.get("subject", "No Subject")
                body = msg.get("body", "")
                relevant = _extract_relevant_section(
                    subject,
                    body,
                    _normalize_keywords(keywords or []),
                    context_chars=200,
                )
                snapshot.append(
                    {
                        "id": msg.get("id"),
                        "subject": subject,
                        "datetime": msg.get("date", "Unknown"),
                        "from": msg.get("from", "Unknown"),
                        "relevant_section": relevant,
                    }
                )

            return snapshot
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error in retrieve_emails_by_label_snapshot: {e}")
            raise ToolError(f"Error retrieving emails by label: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def search_emails_by_field(
        ctx: FastMCPBaseContext,
        search_type: str,
        search_value: str,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Search Gmail messages by specific field criteria.

        This function allows searching emails by different field types such as sender, subject, etc.

        Args:
            search_type: Type of search field. Supported values:
                - "sender": Search by sender email address
                - "subject": Search by subject keywords
            search_value: Value to search for (email address for sender, keywords for subject)
            max_results: Maximum number of results to return (default: 10)
        """
        try:
            # Validate search type
            supported_types = ["sender", "subject"]
            if search_type not in supported_types:
                raise ToolError(
                    f"Unsupported search_type: {search_type}. Supported types: {supported_types}"
                )

            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            # Build search query based on type
            if search_type == "sender":
                query = f"from:{search_value}"
                field_name = "sender email"
            elif search_type == "subject":
                query = f"subject:{search_value}"
                field_name = "subject"

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="search_emails_by_field",
                tool_params={
                    "search_type": search_type,
                    "search_value": search_value,
                    "max_results": max_results,
                },
                no_access_response={
                    "messages": [],
                    "count": 0,
                    "search_type": search_type,
                    "search_value": search_value,
                    "max_results": max_results,
                    "status_message": f"You don't have permission to search emails by {field_name} with this configuration.",
                },
                restricted_access_response={
                    "messages": [],
                    "count": 0,
                    "search_type": search_type,
                    "search_value": search_value,
                    "max_results": max_results,
                    "status_message": f"The tool request with details {{'search_type': '{search_type}', 'search_value': '{search_value}'}} is sent to the user and they can approve it on the app.",
                },
                approval_message=f"Your request to search emails by {field_name} '{search_value}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            # Execute search
            gmail_api = GmailAPI(entity_id, user_id)
            result = await gmail_api.search_emails(query, max_results)

            return {
                "messages": result.get("messages", []),
                "count": result.get("count", 0),
                "search_type": search_type,
                "search_value": search_value,
                "max_results": max_results,
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error searching Gmail by {search_type}: {e}")
            raise ToolError(f"Error searching Gmail by {search_type}: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def label_emails(
        ctx: FastMCPBaseContext, label_name: str, message_ids: List[str]
    ) -> Dict[str, Any]:
        """Create (if needed) or find a label, and apply it to given message IDs.

        Args:
        - label_name: Label to apply (created if missing).
        - message_ids: List of Gmail message IDs.

        Returns: Dict with label_name, label_id, and per-message results.
        """
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
                tool_name="label_emails",
                tool_params={"label_name": label_name, "message_ids": message_ids},
                no_access_response={"error": "Permission denied"},
                restricted_access_response={"error": "Permission denied"},
                approval_message=f"Your request to label emails with '{label_name}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            gmail_api = GmailAPI(entity_id, user_id)

            # Find or create label
            label_result = await gmail_api.find_or_create_label(label_name)
            label_id = label_result.get("id")

            if not label_id:
                return {"error": "Could not create/find label"}

            # Apply label to all messages
            results = []
            for msg_id in message_ids:
                try:
                    await gmail_api.add_label_to_email(msg_id, [label_id])
                    results.append({"message_id": msg_id, "status": "success"})
                except Exception as e:
                    results.append(
                        {"message_id": msg_id, "status": "error", "error": str(e)}
                    )

            return {"label_name": label_name, "label_id": label_id, "results": results}
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error in label_emails: {e}")
            raise ToolError(f"Error labeling emails: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def star_email(
        ctx: FastMCPBaseContext, message_ids: List[str], star: bool = True
    ) -> Dict[str, Any]:
        """Star or unstar the given emails.

        Args:
        - message_ids: List of Gmail message IDs.
        - star: True to star, False to unstar.

        Returns: Dict with action, message_ids, result (API response).
        """
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
                tool_name="star_email",
                tool_params={"message_ids": message_ids, "star": star},
                no_access_response={"error": "Permission denied"},
                restricted_access_response={"error": "Permission denied"},
                approval_message=f"Your request to {'star' if star else 'unstar'} emails was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            gmail_api = GmailAPI(entity_id, user_id)

            if star:
                result = await gmail_api.star_email(message_ids)
            else:
                result = await gmail_api.unstar_email(message_ids)

            return {
                "action": "star" if star else "unstar",
                "message_ids": message_ids,
                "result": result,
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error in star_email: {e}")
            raise ToolError(f"Error starring emails: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def mark_emails_as_read(
        ctx: FastMCPBaseContext, message_ids: List[str]
    ) -> Dict[str, Any]:
        """Mark the given messages as read.

        Args:
        - message_ids: List of Gmail message IDs.
        """
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
                tool_name="mark_emails_as_read",
                tool_params={"message_ids": message_ids},
                no_access_response={"error": "Permission denied"},
                restricted_access_response={"error": "Permission denied"},
                approval_message="Your request to mark emails as read was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="gmail",
            )

            if permission_result is not None:
                return permission_result

            gmail_api = GmailAPI(entity_id, user_id)
            result = await gmail_api.mark_as_read(message_ids)
            return {
                "action": "mark_as_read",
                "message_ids": message_ids,
                "result": result,
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Gmail integration not authenticated. Please add Gmail integration first."
            )
        except Exception as e:
            logger.error(f"Error in mark_emails_as_read: {e}")
            raise ToolError(f"Error marking emails as read: {str(e)}")
