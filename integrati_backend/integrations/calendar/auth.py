"""Calendar OAuth authentication handler."""

import logging
from typing import Dict, Any, Optional
from urllib.parse import urlencode

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from .oauth_config import CalendarOAuthConfig
from mcp_plexus.oauth.storage import get_user_external_token_store
from mcp_plexus.oauth.errors import PlexusExternalAuthRequiredError

logger = logging.getLogger(__name__)


class CalendarAuth:
    """Handles Calendar OAuth authentication flow."""

    def __init__(self, entity_id: str, user_id: str):
        """Initialize Calendar auth with entity and user context."""
        self.entity_id = entity_id
        self.user_id = user_id
        self.config = CalendarOAuthConfig()

    async def get_token_store(self):
        """Get the external token store for this user."""
        return await get_user_external_token_store()

    async def get_stored_tokens(self) -> Optional[Dict[str, Any]]:
        """Retrieve stored OAuth tokens for this user."""
        token_store = await self.get_token_store()
        return await token_store.load_user_external_token(
            self.entity_id, self.user_id, "calendar"
        )

    async def store_tokens(self, tokens: Dict[str, Any]) -> None:
        """Store OAuth tokens for this user."""
        token_store = await self.get_token_store()
        await token_store.save_user_external_token(
            self.entity_id, self.user_id, "calendar", tokens
        )

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
            raise PlexusExternalAuthRequiredError("No stored Calendar tokens found")

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
                    "Failed to refresh Calendar credentials"
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
        token_store = await self.get_token_store()
        await token_store.delete_user_external_token(
            self.entity_id, self.user_id, "calendar"
        )
