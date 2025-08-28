"""Gmail push watcher using Pub/Sub and History API (push-only)."""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from integrations.common.watchers import BaseIntegrationWatcher, WatcherKey
from .unified_auth import UnifiedGmailAuth
from mcp_plexus.settings import settings

logger = logging.getLogger(__name__)


class GmailWatcher(BaseIntegrationWatcher):
    """Registers Gmail mailbox watch and handles Pub/Sub push notifications."""

    def __init__(self) -> None:
        super().__init__(provider_name="gmail")

    async def ensure_registered(self, key: WatcherKey) -> None:
        """Ensure Gmail watch is active for the identity (email address or 'me')."""
        if not settings.gmail_pubsub_topic or not settings.webhook_public_base_url:
            raise RuntimeError(
                "Gmail watcher requires gmail_pubsub_topic and webhook_public_base_url in settings"
            )

        state = await self._load_state(key)
        last_registered_at = state.get("last_registered_at")
        should_register = True
        if last_registered_at:
            try:
                prev = datetime.fromisoformat(last_registered_at)
                if prev > datetime.now(timezone.utc) - timedelta(hours=20):
                    should_register = False
            except Exception:
                pass

        if not should_register:
            return

        auth = UnifiedGmailAuth(key.entity_id, key.identity_key)
        credentials = await auth.get_valid_credentials()
        service = build("gmail", "v1", credentials=credentials)

        # Request push watch on the user's mailbox
        watch_req = {
            "topicName": settings.gmail_pubsub_topic,
            # labelIds or labelFilterAction could be added later for scoping
        }
        resp = service.users().watch(userId="me", body=watch_req).execute()
        new_history_id = resp.get("historyId")

        # Map the authenticated mailbox to this watcher key for reverse lookups
        try:
            prof = service.users().getProfile(userId="me").execute()
            email_address = prof.get("emailAddress")
            if email_address:
                await self._save_webhook_key(external_key=email_address, key=key)
                logger.info(
                    f"Successfully mapped Gmail email {email_address} to watcher key for E:{key.entity_id} U:{key.identity_key}"
                )
            else:
                logger.warning(
                    f"No email address found in Gmail profile for E:{key.entity_id} U:{key.identity_key}"
                )
        except Exception as e:
            logger.error(
                f"Failed to map Gmail email to watcher key for E:{key.entity_id} U:{key.identity_key}: {e}"
            )
            # Try alternative approach - use the entity_id as fallback
            try:
                fallback_key = f"fallback_{key.entity_id}"
                await self._save_webhook_key(external_key=fallback_key, key=key)
                logger.info(
                    f"Used fallback key {fallback_key} for Gmail watcher E:{key.entity_id} U:{key.identity_key}"
                )
            except Exception as fallback_e:
                logger.error(
                    f"Failed to save fallback webhook key for Gmail: {fallback_e}"
                )

        await self._save_state(
            key,
            {
                **state,
                "last_registered_at": datetime.now(timezone.utc).isoformat(),
                "last_history_id": new_history_id or state.get("last_history_id"),
            },
        )
        # Gmail Pub/Sub push is verified via Google-signed JWT at webhook layer
        logger.info(
            "Gmail watcher registered for E:%s U:%s", key.entity_id, key.identity_key
        )

    async def handle_push(self, *, headers: Dict[str, str], body: bytes) -> None:
        """Handle Pub/Sub push: decode message, fetch history deltas, log new emails."""
        # Pub/Sub message body is JSON with message.data base64
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            logger.error("Invalid Pub/Sub JSON: %s", e)
            return

        msg: Optional[Dict[str, Any]] = payload.get("message")
        if not msg:
            return
        data_b64 = msg.get("data")
        if not data_b64:
            return
        try:
            decoded = base64.b64decode(data_b64).decode("utf-8")
            event = json.loads(decoded)
        except Exception as e:
            logger.error("Failed to decode Pub/Sub data: %s", e)
            return

        email_address = event.get("emailAddress")
        pushed_history_id = event.get("historyId")
        if not email_address or not pushed_history_id:
            return

        # Reverse lookup entity and identity using email address saved at registration
        key = await BaseIntegrationWatcher.reverse_lookup("gmail", email_address)
        if not key:
            # Try fallback key if email lookup fails
            logger.warning(
                f"Gmail push for unknown email={email_address}, trying fallback key"
            )
            # Try to find any Gmail watcher for this entity (fallback approach)
            try:
                from mcp_plexus.storage.sqlite_base import get_sqlite_db_connection

                db_conn = await get_sqlite_db_connection()
                cursor = db_conn.cursor()
                # Look for any Gmail watcher in the webhook keys table
                cursor.execute(
                    "SELECT entity_id, identity_key FROM integration_webhook_keys WHERE provider_name='gmail' AND external_key LIKE 'fallback_%'"
                )
                fallback_rows = cursor.fetchall()
                if fallback_rows:
                    # Use the first fallback key found
                    entity_id, identity_key = fallback_rows[0]
                    key = WatcherKey(
                        provider_name="gmail",
                        entity_id=entity_id,
                        identity_key=identity_key,
                    )
                    logger.info(
                        f"Using fallback Gmail watcher for entity={entity_id}, identity_key={identity_key}"
                    )
                else:
                    logger.warning(
                        f"No fallback Gmail watcher found for email={email_address}"
                    )
                    return
            except Exception as fallback_e:
                logger.error(f"Failed to find fallback Gmail watcher: {fallback_e}")
                return

        state = await self._load_state(key)
        last_history_id = state.get("last_history_id")

        try:
            auth = UnifiedGmailAuth(key.entity_id, key.identity_key)
            credentials = await auth.get_valid_credentials()
            service = build("gmail", "v1", credentials=credentials)
        except Exception as auth_error:
            logger.error(
                "Gmail authentication failed for E:%s U:%s email:%s - %s",
                key.entity_id,
                key.identity_key,
                email_address,
                auth_error,
            )
            # Don't return here - try to continue with the operation if possible
            # The error will be logged and the user can see what went wrong
            return

        # Determine start history id
        start_history_id = last_history_id or pushed_history_id
        try:
            history_resp = (
                service.users()
                .history()
                .list(userId="me", startHistoryId=start_history_id, labelId="INBOX")
                .execute()
            )
        except HttpError as e:
            if e.resp.status == 401:
                logger.error(
                    "Gmail API authentication error for E:%s U:%s email:%s - token may need refresh: %s",
                    key.entity_id,
                    key.identity_key,
                    email_address,
                    e,
                )
            else:
                logger.error(
                    "Gmail history fetch error for E:%s U:%s email:%s: %s",
                    key.entity_id,
                    key.identity_key,
                    email_address,
                    e,
                )
            return
        except Exception as e:
            logger.error(
                "Unexpected error fetching Gmail history for E:%s U:%s email:%s: %s",
                key.entity_id,
                key.identity_key,
                email_address,
                e,
            )
            return

        history: List[Dict[str, Any]] = history_resp.get("history", [])
        new_emails_count = 0

        for h in history:
            for added in h.get("messagesAdded", []) or []:
                msg_meta = added.get("message", {})
                msg_id = msg_meta.get("id")
                label_ids = msg_meta.get("labelIds", [])
                if (
                    msg_id
                    and ("INBOX" in label_ids)
                    and ("SENT" not in label_ids)
                    and ("DRAFT" not in label_ids)
                ):
                    try:
                        full_msg = (
                            service.users()
                            .messages()
                            .get(userId="me", id=msg_id, format="metadata")
                            .execute()
                        )
                        headers = {
                            h["name"].lower(): h["value"]
                            for h in full_msg.get("payload", {}).get("headers", [])
                        }
                        logger.info(
                            "Gmail: new email detected for E:%s U:%s | subject=%s | from=%s | id=%s",
                            key.entity_id,
                            key.identity_key,
                            headers.get("subject", ""),
                            headers.get("from", ""),
                            msg_id,
                        )
                        new_emails_count += 1

                        # Trigger background agent processing
                        try:
                            import asyncio
                            from chatbot_api.background_agent_helper import (
                                process_background_request,
                            )

                            # Prepare event details for the background agent
                            event_details = {
                                "type": "new_email",
                                "message_id": msg_id,
                                "subject": headers.get("subject", ""),
                                "from": headers.get("from", ""),
                                "date": headers.get("date", ""),
                                "labels": label_ids,
                            }

                            # Get user context
                            user_context = {
                                "email_address": email_address,
                                "tenant_id": key.entity_id,
                                "user_id": key.identity_key,
                            }

                            # Process in background (don't wait for result to avoid blocking webhook)
                            asyncio.create_task(
                                process_background_request(
                                    tenant_id=key.entity_id,
                                    user_id=key.identity_key,
                                    integration_type="gmail",
                                    event_details=event_details,
                                    user_context=user_context,
                                )
                            )
                            logger.info(
                                f"Background agent processing triggered for new email: {msg_id}"
                            )

                        except Exception as bg_error:
                            logger.error(
                                f"Failed to trigger background agent for email {msg_id}: {bg_error}"
                            )
                    except HttpError as e:
                        if e.resp.status == 401:
                            logger.error(
                                "Gmail message fetch authentication error for E:%s U:%s msg_id:%s - token may need refresh: %s",
                                key.entity_id,
                                key.identity_key,
                                msg_id,
                                e,
                            )
                        else:
                            logger.error(
                                "Gmail message fetch error for E:%s U:%s msg_id:%s: %s",
                                key.entity_id,
                                key.identity_key,
                                msg_id,
                                e,
                            )
                    except Exception as e:
                        logger.error(
                            "Unexpected error fetching Gmail message for E:%s U:%s msg_id:%s: %s",
                            key.entity_id,
                            key.identity_key,
                            msg_id,
                            e,
                        )

        if new_emails_count > 0:
            logger.info(
                "Gmail: processed %d new emails for E:%s U:%s email:%s",
                new_emails_count,
                key.entity_id,
                key.identity_key,
                email_address,
            )

        # Update last_history_id to the latest seen
        new_history_id = history_resp.get("historyId") or pushed_history_id
        await self._save_state(key, {**state, "last_history_id": new_history_id})
