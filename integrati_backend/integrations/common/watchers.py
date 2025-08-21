"""Base interfaces and helpers for integration push watchers.

This module defines provider-agnostic contracts so new integrations (e.g.,
gmail, calendar, twitter, smart_tv) can plug in their own push-only detection
without exposing public APIs.
"""

from __future__ import annotations

import abc
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from mcp_plexus.storage.sqlite_base import get_sqlite_db_connection

logger = logging.getLogger(__name__)


@dataclass
class WatcherKey:
    """Uniquely identifies a watcher instance for an entity and identity.

    - provider_name: logical provider like 'gmail', 'calendar', 'twitter'
    - entity_id: tenant id in the system
    - identity_key: provider-specific identity (e.g., email address, "primary")
    """

    provider_name: str
    entity_id: str
    identity_key: str


class BaseIntegrationWatcher(abc.ABC):
    """Abstract base class for push-only integration watchers.

    Concrete implementations must handle registration/renewal and incoming push
    notifications, persisting state to `integration_watchers` and any reverse
    lookup keys to `integration_webhook_keys` as needed.
    """

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    @abc.abstractmethod
    async def ensure_registered(self, key: WatcherKey) -> None:
        """Ensure a push watcher is registered for the identity.

        Called post-OAuth and on app startup for all active users.
        """

    @abc.abstractmethod
    async def handle_push(self, *, headers: Dict[str, str], body: bytes) -> None:
        """Handle incoming provider push notification."""

    async def _save_state(self, key: WatcherKey, state: Dict[str, Any]) -> None:
        """Persist watcher state to SQLite in a provider-agnostic way."""
        db = await get_sqlite_db_connection()
        cursor = db.cursor()
        iso_now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO integration_watchers (entity_id, provider_name, identity_key, state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id, provider_name, identity_key) DO UPDATE SET
                state_json=excluded.state_json,
                updated_at=excluded.updated_at
            """,
            (
                key.entity_id,
                self.provider_name,
                key.identity_key,
                json.dumps(state),
                iso_now,
                iso_now,
            ),
        )
        db.commit()

    async def _load_state(self, key: WatcherKey) -> Dict[str, Any]:
        """Load watcher state from SQLite; returns empty dict if missing."""
        db = await get_sqlite_db_connection()
        cursor = db.cursor()
        row = cursor.execute(
            """
            SELECT state_json FROM integration_watchers
            WHERE entity_id=? AND provider_name=? AND identity_key=?
            """,
            (key.entity_id, self.provider_name, key.identity_key),
        ).fetchone()
        if not row:
            return {}
        try:
            return json.loads(row[0]) if row[0] else {}
        except Exception:
            return {}

    async def _save_webhook_key(self, *, external_key: str, key: WatcherKey) -> None:
        """Persist reverse lookup from provider external key to our identity."""
        db = await get_sqlite_db_connection()
        cursor = db.cursor()
        iso_now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO integration_webhook_keys (provider_name, external_key, entity_id, identity_key, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider_name, external_key) DO UPDATE SET
                entity_id=excluded.entity_id,
                identity_key=excluded.identity_key,
                updated_at=excluded.updated_at
            """,
            (
                self.provider_name,
                external_key,
                key.entity_id,
                key.identity_key,
                iso_now,
                iso_now,
            ),
        )
        db.commit()

    @staticmethod
    async def reverse_lookup(
        provider_name: str, external_key: str
    ) -> Optional[WatcherKey]:
        """Map provider external key to our WatcherKey via DB."""
        db = await get_sqlite_db_connection()
        cursor = db.cursor()
        row = cursor.execute(
            """
            SELECT entity_id, identity_key FROM integration_webhook_keys
            WHERE provider_name=? AND external_key=?
            """,
            (provider_name, external_key),
        ).fetchone()
        if not row:
            return None
        return WatcherKey(
            provider_name=provider_name, entity_id=row[0], identity_key=row[1]
        )
