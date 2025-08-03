"""Gmail API wrapper for email operations."""

import base64
import email
import logging
from typing import Dict, Any, List, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .unified_auth import UnifiedGmailAuth
from mcp_plexus.oauth.errors import PlexusExternalAuthRequiredError

logger = logging.getLogger(__name__)


class GmailAPI:
    """Gmail API wrapper for email operations."""

    def __init__(self, entity_id: str, user_id: str):
        """Initialize Gmail API wrapper."""
        self.entity_id = entity_id
        self.user_id = user_id
        self.auth = UnifiedGmailAuth(entity_id, user_id, prefer_tenant_level=True)
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

    async def search_messages(
        self, query: str = "", max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search Gmail messages with the given query."""
        try:
            service = await self._get_service()

            # Search for messages
            results = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])
            if not messages:
                return []

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

            return detailed_messages
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

    async def get_message(self, message_id: str) -> Dict[str, Any]:
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
            logger.error(f"Error getting Gmail message: {e}")
            raise

    async def send_message(
        self,
        to_email: str,
        subject: str,
        message_text: str,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a Gmail message."""
        try:
            service = await self._get_service()

            # Create message
            message = self._create_message(to_email, subject, message_text)

            # Send message
            if thread_id:
                sent_message = (
                    service.users()
                    .messages()
                    .send(userId="me", body=message, threadId=thread_id)
                    .execute()
                )
            else:
                sent_message = (
                    service.users().messages().send(userId="me", body=message).execute()
                )

            return {
                "message_id": sent_message["id"],
                "thread_id": sent_message.get("threadId"),
                "label_ids": sent_message.get("labelIds", []),
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
            logger.error(f"Error sending Gmail message: {e}")
            raise

    async def get_last_received_email(self) -> Optional[Dict[str, Any]]:
        """Get the most recent received email."""
        try:
            service = await self._get_service()

            # Search for recent messages
            results = (
                service.users()
                .messages()
                .list(userId="me", maxResults=1, labelIds=["INBOX"])
                .execute()
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

    async def get_unread_count(self) -> int:
        """Get the count of unread messages."""
        try:
            service = await self._get_service()

            results = (
                service.users()
                .messages()
                .list(userId="me", labelIds=["UNREAD"], maxResults=1)
                .execute()
            )

            return results.get("resultSizeEstimate", 0)
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

    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail message into a structured format."""
        headers = message.get("payload", {}).get("headers", [])
        header_dict = {h["name"]: h["value"] for h in headers}

        # Extract body
        body = self._extract_message_body(message.get("payload", {}))

        return {
            "id": message["id"],
            "thread_id": message.get("threadId"),
            "subject": header_dict.get("Subject", ""),
            "from": header_dict.get("From", ""),
            "to": header_dict.get("To", ""),
            "date": header_dict.get("Date", ""),
            "snippet": message.get("snippet", ""),
            "body": body,
            "label_ids": message.get("labelIds", []),
            "internal_date": message.get("internalDate", ""),
        }

    def _extract_message_body(self, payload: Dict[str, Any]) -> str:
        """Extract message body from payload."""
        if "body" in payload and payload["body"].get("data"):
            return base64.urlsafe_b64decode(
                payload["body"]["data"].encode("ASCII")
            ).decode("utf-8")

        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    if part["body"].get("data"):
                        return base64.urlsafe_b64decode(
                            part["body"]["data"].encode("ASCII")
                        ).decode("utf-8")

        return ""

    def _create_message(
        self, to_email: str, subject: str, message_text: str
    ) -> Dict[str, Any]:
        """Create a Gmail message."""
        message = email.mime.text.MIMEText(message_text)
        message["to"] = to_email
        message["subject"] = subject

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return {"raw": raw_message}
