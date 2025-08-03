# integrati_backend/integrations/calendar/unified_auth.py
"""
Unified Calendar OAuth authentication handler.

This version supports both legacy user-level tokens and new tenant-level tokens,
providing backward compatibility while enabling the new architecture.
"""

import logging
from typing import Dict, Any, Optional
from urllib.parse import urlencode

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from .oauth_config import CalendarOAuthConfig
from mcp_plexus.oauth.unified_token_service import get_unified_oauth_token_service
from mcp_plexus.oauth.errors import PlexusExternalAuthRequiredError

logger = logging.getLogger(__name__)


class UnifiedCalendarAuth:
    """
    Handles Calendar OAuth authentication flow with support for both
    user-level and tenant-level token storage.
    """

    def __init__(
        self,
        entity_id: str,
        user_id: str,
        prefer_tenant_level: bool = True,
        use_tenant_storage: bool = True,
    ):
        """
        Initialize Calendar auth with entity and user context.

        Args:
            entity_id: The tenant's entity ID
            user_id: The user/config ID within the tenant
            prefer_tenant_level: If True, prefer tenant-level tokens when reading
            use_tenant_storage: If True, save new tokens to tenant-level storage
        """
        self.entity_id = entity_id
        self.user_id = user_id
        self.prefer_tenant_level = prefer_tenant_level
        self.use_tenant_storage = use_tenant_storage
        self.config = CalendarOAuthConfig()
        self._unified_service = None

    async def get_unified_service(self):
        """Get the unified token service."""
        if self._unified_service is None:
            self._unified_service = await get_unified_oauth_token_service()
        return self._unified_service

    async def get_stored_tokens(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored OAuth tokens for this user/tenant.

        Uses the unified service to check both tenant-level and user-level storage.
        """
        service = await self.get_unified_service()
        return await service.get_oauth_tokens(
            self.entity_id,
            self.user_id,
            "calendar",
            prefer_tenant_level=self.prefer_tenant_level,
        )

    async def store_tokens(self, tokens: Dict[str, Any]) -> None:
        """
        Store OAuth tokens using the configured storage preference.
        """
        service = await self.get_unified_service()
        success = await service.save_oauth_tokens(
            self.entity_id,
            self.user_id,
            "calendar",
            tokens,
            use_tenant_level=self.use_tenant_storage,
        )
        if not success:
            raise Exception("Failed to store Calendar tokens")

    async def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL."""
        base_url = "https://accounts.google.com/o/oauth2/auth"
        params = self.config.get_oauth_url_params()
        params["state"] = state
        return f"{base_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access tokens."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data=self.config.get_token_request_data(code),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    tokens = response.json()
                    await self.store_tokens(tokens)
                    logger.info(
                        f"Successfully obtained Calendar tokens for user {self.user_id}"
                    )
                    return tokens
                else:
                    logger.error(
                        f"Failed to exchange code for tokens: {response.status_code} - {response.text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            return None

    async def refresh_access_token(
        self, refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.config.CLIENT_ID,
                        "client_secret": self.config.CLIENT_SECRET,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    tokens = response.json()
                    # Merge with existing tokens to preserve refresh token
                    stored_tokens = await self.get_stored_tokens()
                    if stored_tokens:
                        tokens["refresh_token"] = stored_tokens.get(
                            "refresh_token", refresh_token
                        )
                    await self.store_tokens(tokens)
                    return tokens
                else:
                    logger.error(
                        f"Failed to refresh token: {response.status_code} - {response.text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return None

    async def get_valid_credentials(self) -> Optional[Credentials]:
        """Get valid Google credentials for API calls."""
        stored_tokens = await self.get_stored_tokens()
        if not stored_tokens:
            raise PlexusExternalAuthRequiredError(
                authorization_url="https://accounts.google.com/o/oauth2/auth",
                provider_name="calendar",
                detail_message="No stored Calendar tokens found",
            )

        credentials = Credentials(
            token=stored_tokens.get("access_token"),
            refresh_token=stored_tokens.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.config.CLIENT_ID,
            client_secret=self.config.CLIENT_SECRET,
            scopes=self.config.SCOPES,
        )

        # Check if token is expired and refresh if needed
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                # Store updated tokens
                updated_tokens = {
                    "access_token": credentials.token,
                    "refresh_token": credentials.refresh_token,
                    "token_type": "Bearer",
                    "expires_in": credentials.expiry.timestamp()
                    if credentials.expiry
                    else None,
                }
                await self.store_tokens(updated_tokens)
            except Exception as e:
                logger.error(f"Failed to refresh Calendar credentials: {e}")
                raise PlexusExternalAuthRequiredError(
                    authorization_url="https://accounts.google.com/o/oauth2/auth",
                    provider_name="calendar",
                    detail_message="Failed to refresh Calendar credentials",
                )

        return credentials

    async def revoke_tokens(self) -> None:
        """Revoke stored OAuth tokens."""
        stored_tokens = await self.get_stored_tokens()
        if stored_tokens and stored_tokens.get("access_token"):
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://oauth2.googleapis.com/revoke",
                        data={"token": stored_tokens["access_token"]},
                    )
            except Exception as e:
                logger.error(f"Error revoking Calendar tokens: {e}")

        # Remove from storage
        service = await self.get_unified_service()
        await service.delete_oauth_tokens(
            self.entity_id,
            self.user_id,
            "calendar",
            delete_tenant_level=True,
            delete_user_level=True,
        )

    async def migrate_to_tenant_storage(self) -> bool:
        """
        Migrate user-level tokens to tenant-level storage.

        Returns:
            True if migration was successful, False otherwise
        """
        try:
            service = await self.get_unified_service()
            return await service.migrate_user_tokens_to_tenant(
                self.entity_id, self.user_id, "calendar"
            )
        except Exception as e:
            logger.error(f"Error migrating Calendar tokens: {e}")
            return False


# Factory functions for different authentication modes
async def create_calendar_auth_legacy(
    entity_id: str, user_id: str
) -> UnifiedCalendarAuth:
    """Create Calendar auth with legacy user-level storage preference."""
    return UnifiedCalendarAuth(
        entity_id, user_id, prefer_tenant_level=False, use_tenant_storage=False
    )


async def create_calendar_auth_tenant_level(
    entity_id: str, user_id: str
) -> UnifiedCalendarAuth:
    """Create Calendar auth with tenant-level storage preference."""
    return UnifiedCalendarAuth(
        entity_id, user_id, prefer_tenant_level=True, use_tenant_storage=True
    )


async def create_calendar_auth_unified(
    entity_id: str, user_id: str
) -> UnifiedCalendarAuth:
    """Create Calendar auth with unified storage (prefers tenant-level, falls back to user-level)."""
    return UnifiedCalendarAuth(
        entity_id, user_id, prefer_tenant_level=True, use_tenant_storage=True
    )
