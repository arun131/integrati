"""Google Calendar push watcher using Channels and syncToken (push-only)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from integrations.common.watchers import BaseIntegrationWatcher, WatcherKey
from .unified_auth import UnifiedCalendarAuth
from mcp_plexus.settings import settings

logger = logging.getLogger(__name__)


class CalendarWatcher(BaseIntegrationWatcher):
    """Registers Calendar events.watch and handles webhook notifications."""

    def __init__(self) -> None:
        super().__init__(provider_name="calendar")

    async def _process_calendar_changes(
        self, service, key: WatcherKey, state: Dict, sync_token: str
    ) -> None:
        """Process calendar changes using the provided sync token."""
        try:
            # Get events that have changed since the last sync
            page_token = None
            while True:
                req = service.events().list(
                    calendarId="primary",
                    singleEvents=True,
                    showDeleted=True,
                    orderBy="startTime",
                    syncToken=sync_token,
                    pageToken=page_token,
                    fields="nextPageToken,nextSyncToken,items(id,summary,status,updated,start,end,htmlLink,organizer,attendees,hangoutLink)",
                )

                resp = req.execute()

                # Process the changes
                for event in resp.get("items", []):
                    # Skip deleted/cancelled events unless we're tracking them
                    if event.get("status") == "cancelled":
                        logger.info(
                            f"Event cancelled: {event.get('id')} - {event.get('summary')}"
                        )
                        continue

                    # Log the event details
                    logger.info(
                        f"Calendar event: {event.get('summary')} | "
                        f"Start: {event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'N/A'))} | "
                        f"End: {event.get('end', {}).get('dateTime', event.get('end', {}).get('date', 'N/A'))} | "
                        f"Link: {event.get('htmlLink')}"
                    )

                # Update the sync token if we get a new one
                if "nextSyncToken" in resp:
                    new_sync_token = resp["nextSyncToken"]
                    if new_sync_token != sync_token:
                        await self._save_state(
                            key, {**state, "sync_token": new_sync_token}
                        )
                        sync_token = new_sync_token

                # Check for more pages
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break

        except Exception as e:
            if "syncToken is no longer valid" in str(e):
                logger.warning(
                    f"Sync token expired for E:{key.entity_id} U:{key.identity_key}, will reset on next push"
                )
                # Clear the sync token so we'll do a fresh sync next time
                await self._save_state(key, {**state, "sync_token": ""})
            else:
                logger.error(
                    f"Error processing calendar changes for E:{key.entity_id} U:{key.identity_key}: {str(e)}"
                )

    async def _get_sync_token(self, service, key: WatcherKey) -> Optional[str]:
        """Try multiple approaches to get a sync token from Google Calendar."""
        logger.info(
            f"Attempting to seed nextSyncToken for E:{key.entity_id} U:{key.identity_key}"
        )
        try:
            # First try to get a sync token by doing a full sync with syncToken parameter
            start_from = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()

            # First request to get the first page
            req = service.events().list(
                calendarId="primary",
                singleEvents=True,
                showDeleted=True,
                orderBy="startTime",
                timeMin=start_from,
                maxResults=1,  # Only need one event to get the sync token
                fields="nextPageToken,nextSyncToken",
            )

            # Execute the request
            resp = req.execute()

            # If we got a sync token on first page, return it
            if "nextSyncToken" in resp:
                logger.info(
                    f"Got sync token on first page for E:{key.entity_id} U:{key.identity_key}"
                )
                return resp["nextSyncToken"]

            # If not, continue paging until we get a sync token
            page_token = resp.get("nextPageToken")
            while page_token:
                req = service.events().list(
                    calendarId="primary",
                    singleEvents=True,
                    showDeleted=True,
                    orderBy="startTime",
                    timeMin=start_from,
                    maxResults=1,
                    pageToken=page_token,
                    fields="nextPageToken,nextSyncToken",
                )
                resp = req.execute()

                if "nextSyncToken" in resp:
                    logger.info(
                        f"Got sync token during pagination for E:{key.entity_id} U:{key.identity_key}"
                    )
                    return resp["nextSyncToken"]

                page_token = resp.get("nextPageToken")

            # If we get here, no sync token was found
            logger.warning(
                f"No sync token found after pagination for E:{key.entity_id} U:{key.identity_key}"
            )
            return None

        except Exception as e:
            logger.error(
                f"Error getting sync token for E:{key.entity_id} U:{key.identity_key}: {str(e)}"
            )
            return None
            logger.warning(
                f"Failed to seed nextSyncToken (unexpected) for E:{key.entity_id} U:{key.identity_key}: {e}"
            )

        # As a last resort, verify calendar accessibility (no token yet)
        try:
            service.calendars().get(calendarId="primary").execute()
            logger.info(
                f"Primary calendar accessible but nextSyncToken not available yet for E:{key.entity_id} U:{key.identity_key}"
            )
        except Exception:
            logger.warning(
                f"Could not access primary calendar for E:{key.entity_id} U:{key.identity_key}"
            )

        return None

    async def ensure_registered(self, key: WatcherKey) -> None:
        """Ensure Calendar channel is active and syncToken is seeded."""
        if not settings.webhook_public_base_url:
            raise RuntimeError(
                "Calendar watcher requires webhook_public_base_url in settings"
            )

        state = await self._load_state(key)
        now = datetime.now(timezone.utc)
        expiration_iso = state.get("expiration")
        needs_watch = True
        if expiration_iso:
            try:
                exp = datetime.fromisoformat(expiration_iso)
                if exp - now > timedelta(minutes=15):
                    needs_watch = False
            except Exception:
                pass

        try:
            auth = UnifiedCalendarAuth(
                key.entity_id, key.identity_key, prefer_tenant_level=True
            )
            credentials = await auth.get_valid_credentials()
            service = build("calendar", "v3", credentials=credentials)
        except Exception as auth_error:
            logger.error(
                "Calendar authentication failed for E:%s U:%s during registration - %s",
                key.entity_id,
                key.identity_key,
                auth_error,
            )
            raise

        # Ensure syncToken - this should always happen regardless of whether we need to renew the channel
        sync_token = state.get("sync_token")
        # Clear legacy no-sync marker so we can seed a real nextSyncToken
        if sync_token == "no_sync_available":
            logger.info(
                f"Clearing legacy 'no_sync_available' for E:{key.entity_id} U:{key.identity_key}"
            )
            sync_token = None
            await self._save_state(key, {**state, "sync_token": ""})
        if not sync_token:
            try:
                logger.info(
                    f"Seeding sync_token for E:{key.entity_id} U:{key.identity_key}"
                )

                # Try multiple approaches to get a sync token
                sync_token = await self._get_sync_token(service, key)

                if sync_token:
                    await self._save_state(key, {**state, "sync_token": sync_token})
                    logger.info(
                        f"Successfully seeded sync_token for E:{key.entity_id} U:{key.identity_key}"
                    )
                else:
                    # Do not mark no-sync here. Leave sync_token unset so the first webhook push
                    # will seed nextSyncToken without processing historical items.
                    logger.info(
                        f"No nextSyncToken available during registration for E:{key.entity_id} U:{key.identity_key}; will seed on first push"
                    )

            except HttpError as e:
                if e.resp.status == 401:
                    logger.error(
                        "Calendar API authentication error for E:%s U:%s during syncToken seeding - token may need refresh: %s",
                        key.entity_id,
                        key.identity_key,
                        e,
                    )
                    raise
                else:
                    logger.error(
                        "Calendar syncToken seeding error for E:%s U:%s: %s",
                        key.entity_id,
                        key.identity_key,
                        e,
                    )
                    raise
            except Exception as e:
                logger.error(
                    "Unexpected error during Calendar syncToken seeding for E:%s U:%s: %s",
                    key.entity_id,
                    key.identity_key,
                    e,
                )
                raise

        # If we don't need to renew the channel, still ensure we have the sync_token saved
        if not needs_watch:
            # Make sure sync_token is saved even if we don't need to renew the channel
            if sync_token and sync_token != state.get("sync_token"):
                await self._save_state(key, {**state, "sync_token": sync_token})
                logger.info(
                    f"Updated sync_token for existing channel E:{key.entity_id} U:{key.identity_key}"
                )
            return

        # Register/renew channel
        try:
            channel_id = str(uuid.uuid4())
            callback = (
                f"{settings.webhook_public_base_url}{settings.calendar_webhook_path}"
            )
            body = {
                "id": channel_id,
                "type": "web_hook",
                "address": callback,
            }
            resp = service.events().watch(calendarId="primary", body=body).execute()
            resource_id = resp.get("resourceId")
            expiration_ms = resp.get("expiration")
            expiration = None
            if expiration_ms:
                try:
                    # Google returns milliseconds since epoch as string
                    ms_int = int(expiration_ms)
                    expiration = datetime.fromtimestamp(
                        ms_int / 1000.0, tz=timezone.utc
                    ).isoformat()
                except Exception:
                    pass

            await self._save_state(
                key,
                {
                    **state,
                    "channel_id": channel_id,
                    "resource_id": resource_id or state.get("resource_id"),
                    "expiration": expiration or state.get("expiration"),
                    "sync_token": sync_token or state.get("sync_token", ""),
                },
            )
            # Save reverse mapping for webhook lookup by channel_id
            await self._save_webhook_key(external_key=channel_id, key=key)
            logger.info(
                "Calendar watcher registered for E:%s U:%s",
                key.entity_id,
                key.identity_key,
            )

        except HttpError as e:
            if e.resp.status == 401:
                logger.error(
                    "Calendar API authentication error for E:%s U:%s during channel registration - token may need refresh: %s",
                    key.entity_id,
                    key.identity_key,
                    e,
                )
                raise
            else:
                logger.error(
                    "Calendar channel registration error for E:%s U:%s: %s",
                    key.entity_id,
                    key.identity_key,
                    e,
                )
                raise
        except Exception as e:
            logger.error(
                "Unexpected error during Calendar channel registration for E:%s U:%s: %s",
                key.entity_id,
                key.identity_key,
                e,
            )
            raise

    async def handle_push(self, *, headers: Dict[str, str], body: bytes) -> None:
        """Handle Calendar push notification."""
        # Parse the push notification
        try:
            data = json.loads(body.decode())
            channel_id = data.get("id")
            resource_id = data.get("resourceId")
        except Exception as e:
            logger.error(f"Invalid push notification: {e}")
            return

        logger.info(
            f"Calendar push received: channel_id={channel_id} resource_id={resource_id}"
        )

        # Find the watcher state for this channel
        key = await self._get_watcher_key_by_channel(channel_id)
        if not key:
            logger.warning(f"No watcher found for channel {channel_id}")
            return

        # Load state and service
        state = await self._load_state(key)
        if not state:
            logger.warning(f"No state found for watcher {key}")
            return

        service = await self._get_service(key)
        if not service:
            logger.warning(f"Failed to get service for {key}")
            return

        # Check if we have a sync token
        sync_token = state.get("sync_token")
        if not sync_token:
            logger.info(
                f"Initial sync needed for E:{key.entity_id} U:{key.identity_key}, performing full sync to get token"
            )
            try:
                # Perform a full sync to get a sync token
                start_from = (
                    datetime.now(timezone.utc) - timedelta(minutes=1)
                ).isoformat()
                page_token = None
                next_sync_token = None

                while True:
                    req = service.events().list(
                        calendarId="primary",
                        singleEvents=True,
                        showDeleted=True,
                        orderBy="startTime",
                        timeMin=start_from,
                        maxResults=2500,
                        pageToken=page_token,
                        fields="nextPageToken,nextSyncToken,items(id,updated,status)",
                    )
                    resp = req.execute()

                    # Update the sync token if we get one
                    if "nextSyncToken" in resp:
                        next_sync_token = resp["nextSyncToken"]

                    # Check if there are more pages
                    page_token = resp.get("nextPageToken")
                    if not page_token:
                        break

                if next_sync_token:
                    # Save the sync token for next time
                    await self._save_state(
                        key, {**state, "sync_token": next_sync_token}
                    )
                    logger.info(
                        f"Initial sync complete, saved sync token for E:{key.entity_id} U:{key.identity_key}"
                    )

                    # Now that we have a sync token, process the current changes
                    await self._process_calendar_changes(
                        service, key, state, next_sync_token
                    )
                else:
                    logger.warning(
                        f"No sync token available after full sync for E:{key.entity_id} U:{key.identity_key}"
                    )

                return

            except Exception as e:
                logger.error(
                    f"Failed to perform initial sync for E:{key.entity_id} U:{key.identity_key}: {e}"
                )
                return

        # We have a sync token, process the changes
        try:
            await self._process_calendar_changes(service, key, state, sync_token)
        except Exception as e:
            logger.error(f"Error processing calendar changes: {e}")
