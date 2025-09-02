"""Gmail API wrapper for email operations."""

import base64
import logging
import os
from typing import Dict, Any, List, Optional, Union
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from .unified_auth import UnifiedGmailAuth
from mcp_plexus.oauth.errors import PlexusExternalAuthRequiredError

logger = logging.getLogger(__name__)


class GmailAPI:
    """Gmail API wrapper for email operations."""

    def __init__(self, entity_id: str, user_id: str):
        """Initialize Gmail API wrapper."""
        self.entity_id = entity_id
        self.user_id = user_id
        self.auth = UnifiedGmailAuth(entity_id, user_id)
        self.service = None

    async def _get_service(self):
        """Get Gmail API service instance."""
        if self.service is None:
            credentials = await self.auth.get_valid_credentials()
            if not credentials:
                raise PlexusExternalAuthRequiredError(
                    authorization_url="https://accounts.google.com/o/oauth2/auth",
                    provider_name="gmail",
                    detail_message="Gmail integration not authenticated",
                )

            self.service = build("gmail", "v1", credentials=credentials)
        return self.service

    # ============================================================================
    # CORE EMAIL OPERATIONS
    # ============================================================================

    async def send_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        body_type: str = "text",
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Send an email with optional attachments."""
        try:
            service = await self._get_service()

            # Create message
            message = self._create_message_with_attachments(
                to, subject, body, body_type, cc, bcc, reply_to, attachments
            )

            # Send the message
            sent_message = (
                service.users().messages().send(userId="me", body=message).execute()
            )

            return {
                "id": sent_message["id"],
                "thread_id": sent_message.get("threadId"),
                "label_ids": sent_message.get("labelIds", []),
                "status": "sent",
                "message": "Email sent successfully",
            }
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError(
                    authorization_url="https://accounts.google.com/o/oauth2/auth",
                    provider_name="gmail",
                    detail_message="Gmail authentication expired",
                )
            raise Exception(f"Gmail API error: {e}")
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise

    async def draft_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        body_type: str = "text",
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create an email draft without sending."""
        try:
            service = await self._get_service()

            # Create message
            message = self._create_message_with_attachments(
                to, subject, body, body_type, cc, bcc, reply_to, attachments
            )

            # Create draft
            draft = (
                service.users()
                .drafts()
                .create(userId="me", body={"message": message})
                .execute()
            )

            return {
                "id": draft["id"],
                "message_id": draft["message"]["id"],
                "thread_id": draft["message"].get("threadId"),
                "status": "draft",
                "message": "Draft created successfully",
            }
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError(
                    authorization_url="https://accounts.google.com/o/oauth2/auth",
                    provider_name="gmail",
                    detail_message="Gmail authentication expired",
                )
            raise Exception(f"Gmail API error: {e}")
        except Exception as e:
            logger.error(f"Error creating draft: {e}")
            raise

    async def reply_to_email(
        self,
        message_id: str,
        body: str,
        body_type: str = "text",
        to: Optional[Union[str, List[str]]] = None,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Reply to an existing email."""
        try:
            service = await self._get_service()

            # Get the original message
            original_message = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            # Extract headers
            headers = original_message.get("payload", {}).get("headers", [])
            header_dict = {h["name"]: h["value"] for h in headers}

            # Create reply message
            subject = header_dict.get("Subject", "")
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"

            # Get the original sender as recipient if no "to" specified
            if to is None:
                from_header = header_dict.get("From", "")
                to_email = from_header
            else:
                to_email = to

            # Create and send reply
            return await self.send_email(
                to=to_email,
                subject=subject,
                body=body,
                body_type=body_type,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
            )
        except Exception as e:
            logger.error(f"Error replying to email: {e}")
            raise

    async def forward_email(
        self,
        message_id: str,
        to: Union[str, List[str]],
        body: str = "",
        body_type: str = "text",
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Forward an email to other recipients."""
        try:
            service = await self._get_service()

            # Get the original message
            original_message = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            # Extract headers
            headers = original_message.get("payload", {}).get("headers", [])
            header_dict = {h["name"]: h["value"] for h in headers}

            # Create forward subject
            subject = header_dict.get("Subject", "")
            if not subject.startswith("Fwd:"):
                subject = f"Fwd: {subject}"

            # Create forward body
            forward_body = f"{body}\n\n--- Forwarded message ---\n"
            forward_body += f"From: {header_dict.get('From', '')}\n"
            forward_body += f"Date: {header_dict.get('Date', '')}\n"
            forward_body += f"Subject: {header_dict.get('Subject', '')}\n"
            forward_body += f"To: {header_dict.get('To', '')}\n\n"

            # Extract original content
            original_content = self._extract_message_body(
                original_message.get("payload", {})
            )
            forward_body += original_content

            # Send forwarded email
            return await self.send_email(
                to=to,
                subject=subject,
                body=forward_body,
                body_type=body_type,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
            )
        except Exception as e:
            logger.error(f"Error forwarding email: {e}")
            raise

    # ============================================================================
    # EMAIL RETRIEVAL & SEARCH
    # ============================================================================

    async def get_email(self, message_id: str) -> Dict[str, Any]:
        """Get a specific Gmail message by ID."""
        try:
            service = await self._get_service()
            message = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            return self._parse_message(message)
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError(
                    authorization_url="https://accounts.google.com/o/oauth2/auth",
                    provider_name="gmail",
                    detail_message="Gmail authentication expired",
                )
            raise Exception(f"Gmail API error: {e}")
        except Exception as e:
            logger.error(f"Error getting email: {e}")
            raise

    async def search_emails(
        self,
        query: str = "",
        max_results: int = 10,
        page_token: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search Gmail messages with advanced query support."""
        try:
            service = await self._get_service()

            # Build request
            request = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=max_results,
                    labelIds=label_ids or [],
                )
            )

            if page_token:
                request.pageToken = page_token

            results = request.execute()

            messages = results.get("messages", [])
            if not messages:
                return {
                    "messages": [],
                    "count": 0,
                    "next_page_token": results.get("nextPageToken"),
                    "query": query,
                }

            # Get detailed message information
            detailed_messages = []
            for message in messages:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=message["id"], format="full")
                    .execute()
                )
                detailed_messages.append(self._parse_message(msg))

            return {
                # Ensure newest-first ordering consistently across all callers
                "messages": sorted(
                    detailed_messages,
                    key=lambda m: int(m.get("internal_date") or 0),
                    reverse=True,
                ),
                "count": len(detailed_messages),
                "next_page_token": results.get("nextPageToken"),
                "query": query,
            }
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError(
                    authorization_url="https://accounts.google.com/o/oauth2/auth",
                    provider_name="gmail",
                    detail_message="Gmail authentication expired",
                )
            raise Exception(f"Gmail API error: {e}")
        except Exception as e:
            logger.error(f"Error searching Gmail messages: {e}")
            raise

    async def get_inbox_emails(
        self,
        max_results: int = 10,
        page_token: Optional[str] = None,
        unread_only: bool = False,
    ) -> Dict[str, Any]:
        """Get emails from inbox."""
        label_ids = ["INBOX"]
        if unread_only:
            label_ids.append("UNREAD")

        return await self.search_emails(
            max_results=max_results, page_token=page_token, label_ids=label_ids
        )

    async def get_sent_emails(
        self,
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get sent emails."""
        return await self.search_emails(
            max_results=max_results, page_token=page_token, label_ids=["SENT"]
        )

    async def get_draft_emails(
        self,
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get draft emails."""
        return await self.search_emails(
            max_results=max_results, page_token=page_token, label_ids=["DRAFT"]
        )

    async def get_starred_emails(
        self,
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get starred emails."""
        return await self.search_emails(
            max_results=max_results, page_token=page_token, label_ids=["STARRED"]
        )

    async def get_important_emails(
        self,
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get important emails."""
        return await self.search_emails(
            max_results=max_results, page_token=page_token, label_ids=["IMPORTANT"]
        )

    async def get_email_threads(
        self,
        thread_id: str,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Get all emails in a conversation thread."""
        try:
            service = await self._get_service()

            thread = service.users().threads().get(userId="me", id=thread_id).execute()

            messages = thread.get("messages", [])
            if not messages:
                return {"messages": [], "count": 0, "thread_id": thread_id}

            # Parse all messages in thread and order newest-first
            detailed_messages = []
            for message in messages:
                detailed_messages.append(self._parse_message(message))
            detailed_messages.sort(
                key=lambda m: int(m.get("internal_date") or 0), reverse=True
            )

            return {
                "messages": detailed_messages,
                "count": len(detailed_messages),
                "thread_id": thread_id,
                "snippet": thread.get("snippet", ""),
            }
        except Exception as e:
            logger.error(f"Error getting email thread: {e}")
            raise

    # ============================================================================
    # UNREAD COUNT & STATISTICS
    # ============================================================================

    async def get_unread_count(self) -> int:
        """Get the exact count of unread messages using labels API."""
        try:
            service = await self._get_service()

            # Get the UNREAD label details which includes the exact count
            labels = service.users().labels().get(userId="me", id="UNREAD").execute()

            # Return the exact unread count
            return labels.get("messagesUnread", 0)
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError(
                    authorization_url="https://accounts.google.com/o/oauth2/auth",
                    provider_name="gmail",
                    detail_message="Gmail authentication expired",
                )
            raise Exception(f"Gmail API error: {e}")
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            raise

    async def get_email_stats(self) -> Dict[str, Any]:
        """Get comprehensive email statistics."""
        try:
            service = await self._get_service()

            # Get profile info
            profile = service.users().getProfile(userId="me").execute()

            # Get labels for counts
            labels = service.users().labels().list(userId="me").execute()

            stats = {
                "email_address": profile.get("emailAddress", ""),
                "messages_total": profile.get("messagesTotal", 0),
                "threads_total": profile.get("threadsTotal", 0),
                "history_id": profile.get("historyId", 0),
            }

            # Count messages by label
            for label in labels.get("labels", []):
                label_id = label.get("id")
                if label_id == "INBOX":
                    stats["inbox_count"] = label.get("messagesTotal", 0)
                    stats["inbox_unread"] = label.get("messagesUnread", 0)
                elif label_id == "SENT":
                    stats["sent_count"] = label.get("messagesTotal", 0)
                elif label_id == "DRAFT":
                    stats["draft_count"] = label.get("messagesTotal", 0)
                elif label_id == "SPAM":
                    stats["spam_count"] = label.get("messagesTotal", 0)
                elif label_id == "TRASH":
                    stats["trash_count"] = label.get("messagesTotal", 0)
                elif label_id == "STARRED":
                    stats["starred_count"] = label.get("messagesTotal", 0)
                elif label_id == "IMPORTANT":
                    stats["important_count"] = label.get("messagesTotal", 0)
                elif label_id == "UNREAD":
                    stats["unread_count"] = label.get("messagesTotal", 0)

            return stats
        except Exception as e:
            logger.error(f"Error getting email stats: {e}")
            raise

    # ============================================================================
    # EMAIL MODIFICATIONS
    # ============================================================================

    async def mark_as_read(self, message_ids: Union[str, List[str]]) -> Dict[str, Any]:
        """Mark emails as read."""
        return await self._modify_labels(
            message_ids, add_label_ids=[], remove_label_ids=["UNREAD"]
        )

    async def mark_as_unread(
        self, message_ids: Union[str, List[str]]
    ) -> Dict[str, Any]:
        """Mark emails as unread."""
        return await self._modify_labels(
            message_ids, add_label_ids=["UNREAD"], remove_label_ids=[]
        )

    async def mark_as_important(
        self, message_ids: Union[str, List[str]]
    ) -> Dict[str, Any]:
        """Mark emails as important."""
        return await self._modify_labels(
            message_ids, add_label_ids=["IMPORTANT"], remove_label_ids=[]
        )

    async def mark_as_not_important(
        self, message_ids: Union[str, List[str]]
    ) -> Dict[str, Any]:
        """Remove important flag from emails."""
        return await self._modify_labels(
            message_ids, add_label_ids=[], remove_label_ids=["IMPORTANT"]
        )

    async def star_email(self, message_ids: Union[str, List[str]]) -> Dict[str, Any]:
        """Star emails."""
        return await self._modify_labels(
            message_ids, add_label_ids=["STARRED"], remove_label_ids=[]
        )

    async def unstar_email(self, message_ids: Union[str, List[str]]) -> Dict[str, Any]:
        """Remove star from emails."""
        return await self._modify_labels(
            message_ids, add_label_ids=[], remove_label_ids=["STARRED"]
        )

    async def archive_email(self, message_ids: Union[str, List[str]]) -> Dict[str, Any]:
        """Archive emails (remove from inbox)."""
        return await self._modify_labels(
            message_ids, add_label_ids=[], remove_label_ids=["INBOX"]
        )

    async def move_to_inbox(self, message_ids: Union[str, List[str]]) -> Dict[str, Any]:
        """Move emails back to inbox."""
        return await self._modify_labels(
            message_ids, add_label_ids=["INBOX"], remove_label_ids=[]
        )

    async def delete_email(self, message_ids: Union[str, List[str]]) -> Dict[str, Any]:
        """Delete emails (move to trash)."""
        return await self._modify_labels(
            message_ids, add_label_ids=["TRASH"], remove_label_ids=["INBOX"]
        )

    async def move_to_spam(self, message_ids: Union[str, List[str]]) -> Dict[str, Any]:
        """Move emails to spam."""
        return await self._modify_labels(
            message_ids, add_label_ids=["SPAM"], remove_label_ids=["INBOX"]
        )

    # ============================================================================
    # LABEL MANAGEMENT
    # ============================================================================

    async def create_label(
        self,
        name: str,
        message_list_visibility: str = "show",
        label_list_visibility: str = "labelShow",
    ) -> Dict[str, Any]:
        """Create a new Gmail label."""
        try:
            service = await self._get_service()

            label_object = {
                "name": name,
                "messageListVisibility": message_list_visibility,
                "labelListVisibility": label_list_visibility,
            }

            label = (
                service.users()
                .labels()
                .create(userId="me", body=label_object)
                .execute()
            )

            return {
                "id": label["id"],
                "name": label["name"],
                "message_list_visibility": label.get("messageListVisibility"),
                "label_list_visibility": label.get("labelListVisibility"),
                "type": label.get("type"),
                "messages_total": label.get("messagesTotal", 0),
                "messages_unread": label.get("messagesUnread", 0),
            }
        except Exception as e:
            logger.error(f"Error creating label: {e}")
            raise

    async def update_label(
        self,
        label_id: str,
        name: Optional[str] = None,
        message_list_visibility: Optional[str] = None,
        label_list_visibility: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing Gmail label."""
        try:
            service = await self._get_service()

            # Get current label
            current_label = (
                service.users().labels().get(userId="me", id=label_id).execute()
            )

            # Update fields
            if name:
                current_label["name"] = name
            if message_list_visibility:
                current_label["messageListVisibility"] = message_list_visibility
            if label_list_visibility:
                current_label["labelListVisibility"] = label_list_visibility

            # Update label
            updated_label = (
                service.users()
                .labels()
                .patch(userId="me", id=label_id, body=current_label)
                .execute()
            )

            return {
                "id": updated_label["id"],
                "name": updated_label["name"],
                "message_list_visibility": updated_label.get("messageListVisibility"),
                "label_list_visibility": updated_label.get("labelListVisibility"),
                "type": updated_label.get("type"),
                "messages_total": updated_label.get("messagesTotal", 0),
                "messages_unread": updated_label.get("messagesUnread", 0),
            }
        except Exception as e:
            logger.error(f"Error updating label: {e}")
            raise

    async def delete_label(self, label_id: str) -> Dict[str, Any]:
        """Delete a user-created Gmail label."""
        try:
            service = await self._get_service()

            # Check if label exists and is user-created
            label = service.users().labels().get(userId="me", id=label_id).execute()

            if label.get("type") == "system":
                raise Exception("Cannot delete system labels")

            # Delete label
            service.users().labels().delete(userId="me", id=label_id).execute()

            return {
                "id": label_id,
                "name": label.get("name", ""),
                "status": "deleted",
                "message": "Label deleted successfully",
            }
        except Exception as e:
            logger.error(f"Error deleting label: {e}")
            raise

    async def get_label(self, label_id: str) -> Dict[str, Any]:
        """Get a specific label by ID."""
        try:
            service = await self._get_service()

            label = service.users().labels().get(userId="me", id=label_id).execute()

            return {
                "id": label["id"],
                "name": label["name"],
                "message_list_visibility": label.get("messageListVisibility"),
                "label_list_visibility": label.get("labelListVisibility"),
                "type": label.get("type"),
                "messages_total": label.get("messagesTotal", 0),
                "messages_unread": label.get("messagesUnread", 0),
            }
        except Exception as e:
            logger.error(f"Error getting label: {e}")
            raise

    async def find_or_create_label(
        self,
        name: str,
        message_list_visibility: str = "show",
        label_list_visibility: str = "labelShow",
    ) -> Dict[str, Any]:
        """Find a label by name or create it if it doesn't exist."""
        try:
            service = await self._get_service()

            # List all labels
            labels = service.users().labels().list(userId="me").execute()

            # Find existing label
            for label in labels.get("labels", []):
                if label["name"].lower() == name.lower():
                    return await self.get_label(label["id"])

            # Create new label if not found
            return await self.create_label(
                name, message_list_visibility, label_list_visibility
            )
        except Exception as e:
            logger.error(f"Error finding or creating label: {e}")
            raise

    async def list_labels(self) -> List[Dict[str, Any]]:
        """List all Gmail labels."""
        try:
            service = await self._get_service()

            labels = service.users().labels().list(userId="me").execute()

            detailed_labels = []
            for label in labels.get("labels", []):
                detailed_labels.append(
                    {
                        "id": label["id"],
                        "name": label["name"],
                        "message_list_visibility": label.get("messageListVisibility"),
                        "label_list_visibility": label.get("labelListVisibility"),
                        "type": label.get("type"),
                        "messages_total": label.get("messagesTotal", 0),
                        "messages_unread": label.get("messagesUnread", 0),
                    }
                )

            return detailed_labels
        except Exception as e:
            logger.error(f"Error listing labels: {e}")
            raise

    async def add_label_to_email(
        self,
        message_ids: Union[str, List[str]],
        label_ids: Union[str, List[str]],
    ) -> Dict[str, Any]:
        """Add labels to emails."""
        if isinstance(label_ids, str):
            label_ids = [label_ids]
        return await self._modify_labels(
            message_ids, add_label_ids=label_ids, remove_label_ids=[]
        )

    async def remove_label_from_email(
        self,
        message_ids: Union[str, List[str]],
        label_ids: Union[str, List[str]],
    ) -> Dict[str, Any]:
        """Remove labels from emails."""
        if isinstance(label_ids, str):
            label_ids = [label_ids]
        return await self._modify_labels(
            message_ids, add_label_ids=[], remove_label_ids=label_ids
        )

    # ============================================================================
    # ATTACHMENT HANDLING
    # ============================================================================

    async def download_attachment(
        self,
        message_id: str,
        attachment_id: str,
        save_path: str,
    ) -> Dict[str, Any]:
        """Download an email attachment to local filesystem."""
        try:
            service = await self._get_service()

            # Get attachment
            attachment = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )

            # Decode attachment data
            attachment_data = base64.urlsafe_b64decode(attachment["data"])

            # Save to file
            with open(save_path, "wb") as f:
                f.write(attachment_data)

            return {
                "message_id": message_id,
                "attachment_id": attachment_id,
                "save_path": save_path,
                "size": len(attachment_data),
                "status": "downloaded",
            }
        except Exception as e:
            logger.error(f"Error downloading attachment: {e}")
            raise

    async def get_attachment_info(
        self,
        message_id: str,
        attachment_id: str,
    ) -> Dict[str, Any]:
        """Get attachment metadata."""
        try:
            service = await self._get_service()

            # Get attachment
            attachment = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )

            return {
                "message_id": message_id,
                "attachment_id": attachment_id,
                "size": len(base64.urlsafe_b64decode(attachment["data"])),
                "data": attachment["data"],  # Base64 encoded
            }
        except Exception as e:
            logger.error(f"Error getting attachment info: {e}")
            raise

    # ============================================================================
    # BATCH OPERATIONS
    # ============================================================================

    async def batch_mark_read(self, message_ids: List[str]) -> Dict[str, Any]:
        """Mark multiple emails as read."""
        return await self._modify_labels(
            message_ids, add_label_ids=[], remove_label_ids=["UNREAD"]
        )

    async def batch_mark_unread(self, message_ids: List[str]) -> Dict[str, Any]:
        """Mark multiple emails as unread."""
        return await self._modify_labels(
            message_ids, add_label_ids=["UNREAD"], remove_label_ids=[]
        )

    async def batch_archive(self, message_ids: List[str]) -> Dict[str, Any]:
        """Archive multiple emails."""
        return await self._modify_labels(
            message_ids, add_label_ids=[], remove_label_ids=["INBOX"]
        )

    async def batch_delete(self, message_ids: List[str]) -> Dict[str, Any]:
        """Delete multiple emails."""
        return await self._modify_labels(
            message_ids, add_label_ids=["TRASH"], remove_label_ids=["INBOX"]
        )

    async def batch_add_labels(
        self, message_ids: List[str], label_ids: List[str]
    ) -> Dict[str, Any]:
        """Add labels to multiple emails."""
        return await self._modify_labels(
            message_ids, add_label_ids=label_ids, remove_label_ids=[]
        )

    async def batch_remove_labels(
        self, message_ids: List[str], label_ids: List[str]
    ) -> Dict[str, Any]:
        """Remove labels from multiple emails."""
        return await self._modify_labels(
            message_ids, add_label_ids=[], remove_label_ids=label_ids
        )

    # ============================================================================
    # FILTER MANAGEMENT
    # ============================================================================

    async def create_filter(
        self,
        criteria: Dict[str, Any],
        action: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a Gmail filter."""
        try:
            service = await self._get_service()

            filter_object = {"criteria": criteria, "action": action}

            gmail_filter = (
                service.users()
                .settings()
                .filters()
                .create(userId="me", body=filter_object)
                .execute()
            )

            return {
                "id": gmail_filter["id"],
                "criteria": gmail_filter["criteria"],
                "action": gmail_filter["action"],
                "status": "created",
            }
        except Exception as e:
            logger.error(f"Error creating filter: {e}")
            raise

    async def list_filters(self) -> List[Dict[str, Any]]:
        """List all Gmail filters."""
        try:
            service = await self._get_service()

            filters = service.users().settings().filters().list(userId="me").execute()

            return filters.get("filter", [])
        except Exception as e:
            logger.error(f"Error listing filters: {e}")
            raise

    async def delete_filter(self, filter_id: str) -> Dict[str, Any]:
        """Delete a Gmail filter."""
        try:
            service = await self._get_service()

            service.users().settings().filters().delete(
                userId="me", id=filter_id
            ).execute()

            return {
                "id": filter_id,
                "status": "deleted",
                "message": "Filter deleted successfully",
            }
        except Exception as e:
            logger.error(f"Error deleting filter: {e}")
            raise

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    async def get_profile(self) -> Dict[str, Any]:
        """Get Gmail profile information."""
        try:
            service = await self._get_service()

            profile = service.users().getProfile(userId="me").execute()

            return {
                "email_address": profile.get("emailAddress", ""),
                "messages_total": profile.get("messagesTotal", 0),
                "threads_total": profile.get("threadsTotal", 0),
                "history_id": profile.get("historyId", 0),
            }
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            raise

    def validate_email(self, email_address: str) -> bool:
        """Validate email address format."""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email_address) is not None

    # ============================================================================
    # PRIVATE HELPER METHODS
    # ============================================================================

    async def _modify_labels(
        self,
        message_ids: Union[str, List[str]],
        add_label_ids: List[str],
        remove_label_ids: List[str],
    ) -> Dict[str, Any]:
        """Modify labels on emails (internal method)."""
        try:
            service = await self._get_service()

            if isinstance(message_ids, str):
                message_ids = [message_ids]

            # Process each message
            results = []
            for msg_id in message_ids:
                try:
                    # Get current labels
                    # Note: We intentionally avoid storing the returned message
                    # object in a variable to prevent unused-variable lint errors.
                    service.users().messages().get(
                        userId="me",
                        id=msg_id,
                        format="metadata",
                        metadataHeaders=[],
                    ).execute()

                    # Update message
                    updated_message = (
                        service.users()
                        .messages()
                        .modify(
                            userId="me",
                            id=msg_id,
                            body={
                                "addLabelIds": add_label_ids,
                                "removeLabelIds": remove_label_ids,
                            },
                        )
                        .execute()
                    )

                    results.append(
                        {
                            "message_id": msg_id,
                            "status": "success",
                            "new_labels": updated_message.get("labelIds", []),
                        }
                    )
                except Exception as e:
                    results.append(
                        {"message_id": msg_id, "status": "error", "error": str(e)}
                    )

            return {
                "results": results,
                "total_processed": len(message_ids),
                "successful": len([r for r in results if r["status"] == "success"]),
                "failed": len([r for r in results if r["status"] == "error"]),
            }
        except Exception as e:
            logger.error(f"Error modifying labels: {e}")
            raise

    def _create_message_with_attachments(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        body_type: str = "text",
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a message with optional attachments."""
        # Convert to lists
        if isinstance(to, str):
            to = [to]
        if cc and isinstance(cc, str):
            cc = [cc]
        if bcc and isinstance(bcc, str):
            bcc = [bcc]

        # Create message
        if attachments and len(attachments) > 0:
            message = MIMEMultipart()
            message["to"] = ", ".join(to)
            message["subject"] = subject
            if cc:
                message["cc"] = ", ".join(cc)
            if bcc:
                message["bcc"] = ", ".join(bcc)
            if reply_to:
                message["reply-to"] = reply_to

            # Add body
            if body_type.lower() == "html":
                text_part = MIMEText(body, "html")
            else:
                text_part = MIMEText(body, "plain")
            message.attach(text_part)

            # Add attachments
            for attachment_path in attachments:
                if os.path.exists(attachment_path):
                    with open(attachment_path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())

                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename= {os.path.basename(attachment_path)}",
                    )
                    message.attach(part)
        else:
            # Simple text message
            if body_type.lower() == "html":
                message = MIMEText(body, "html")
            else:
                message = MIMEText(body, "plain")
            message["to"] = ", ".join(to)
            message["subject"] = subject
            if cc:
                message["cc"] = ", ".join(cc)
            if bcc:
                message["bcc"] = ", ".join(bcc)
            if reply_to:
                message["reply-to"] = reply_to

        # Encode and return
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return {"raw": raw_message}

    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail message into a structured format."""
        headers = message.get("payload", {}).get("headers", [])
        header_dict = {h["name"]: h["value"] for h in headers}

        # Extract body
        body = self._extract_message_body(message.get("payload", {}))

        # Extract attachments info
        attachments = self._extract_attachments_info(message.get("payload", {}))

        return {
            "id": message["id"],
            "thread_id": message.get("threadId"),
            "subject": header_dict.get("Subject", ""),
            "from": header_dict.get("From", ""),
            "to": header_dict.get("To", ""),
            "cc": header_dict.get("Cc", ""),
            "bcc": header_dict.get("Bcc", ""),
            "date": header_dict.get("Date", ""),
            "snippet": message.get("snippet", ""),
            "body": body,
            "attachments": attachments,
            "label_ids": message.get("labelIds", []),
            "internal_date": message.get("internalDate", ""),
            "size_estimate": message.get("sizeEstimate", 0),
        }

    def _extract_message_body(self, payload: Dict[str, Any]) -> str:
        """Extract message body from payload."""
        if "body" in payload and payload["body"].get("data"):
            try:
                return base64.urlsafe_b64decode(
                    payload["body"]["data"].encode("ASCII")
                ).decode("utf-8")
            except Exception as e:
                logger.error(f"Error decoding message body: {e}")
                return ""

        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    if part["body"].get("data"):
                        try:
                            return base64.urlsafe_b64decode(
                                part["body"]["data"].encode("ASCII")
                            ).decode("utf-8")
                        except Exception as e:
                            logger.error(f"Error decoding message body: {e}")
                            continue
                elif part["mimeType"] == "text/html":
                    if part["body"].get("data"):
                        try:
                            return base64.urlsafe_b64decode(
                                part["body"]["data"].encode("ASCII")
                            ).decode("utf-8")
                        except Exception:
                            continue

        return ""

    def _extract_attachments_info(
        self, payload: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract attachment information from payload."""
        attachments = []

        def process_part(part):
            if part.get("filename"):
                attachment_info = {
                    "attachment_id": part["body"].get("attachmentId"),
                    "filename": part["filename"],
                    "mime_type": part["mimeType"],
                    "size": part["body"].get("size", 0),
                }
                attachments.append(attachment_info)

            if "parts" in part:
                for sub_part in part["parts"]:
                    process_part(sub_part)

        process_part(payload)
        return attachments

    # ============================================================================
    # LEGACY METHODS (keeping for backward compatibility)
    # ============================================================================

    async def search_messages(
        self, query: str = "", max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Legacy method - use search_emails instead."""
        result = await self.search_emails(query, max_results)
        return result.get("messages", [])

    async def get_last_received_email(self) -> Optional[Dict[str, Any]]:
        """Get the most recent received email."""
        try:
            service = await self._get_service()

            results = (
                service.users().messages().list(userId="me", maxResults=1).execute()
            )

            messages = results.get("messages", [])
            if not messages:
                return None

            # Get the first (most recent) message
            message = (
                service.users()
                .messages()
                .get(userId="me", id=messages[0]["id"], format="full")
                .execute()
            )

            return self._parse_message(message)
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError(
                    authorization_url="https://accounts.google.com/o/oauth2/auth",
                    provider_name="gmail",
                    detail_message="Gmail authentication expired",
                )
            raise Exception(f"Gmail API error: {e}")
        except Exception as e:
            logger.error(f"Error getting last received email: {e}")
            raise
