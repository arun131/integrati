# integrati_backend/integrations/gmail/unified_auth.py
"""
Unified Gmail OAuth authentication handler.

This version supports both legacy user-level tokens and new tenant-level tokens,
providing backward compatibility while enabling the new architecture.
"""

import logging
from typing import Dict, Any, Optional
from urllib.parse import urlencode

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from .oauth_config import GmailOAuthConfig
from mcp_plexus.oauth.unified_token_service import get_unified_oauth_token_service
from mcp_plexus.oauth.errors import PlexusExternalAuthRequiredError

logger = logging.getLogger(__name__)


class UnifiedGmailAuth:
    """
    Handles Gmail OAuth authentication flow with support for both
    user-level and tenant-level token storage.
    """

    def __init__(
        self,
        entity_id: str,
        user_id: str,
        use_tenant_storage: bool = True,
    ):
        """
        Initialize Gmail auth with entity and user context.

        Args:
            entity_id: The tenant's entity ID
            user_id: The user/config ID within the tenant
            use_tenant_storage: If True, save new tokens to tenant-level storage
        """
        self.entity_id = entity_id
        self.user_id = user_id
        self.use_tenant_storage = use_tenant_storage
        self.config = GmailOAuthConfig()
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
            "gmail",
        )

    async def store_tokens(self, tokens: Dict[str, Any]) -> None:
        """
        Store OAuth tokens using the configured storage preference.
        """
        service = await self.get_unified_service()
        success = await service.save_oauth_tokens(
            self.entity_id,
            self.user_id,
            "gmail",
            tokens,
        )
        if not success:
            raise Exception("Failed to store Gmail tokens")

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
                    storage_type = (
                        "tenant-level" if self.use_tenant_storage else "user-level"
                    )
                    logger.info(
                        f"Successfully obtained Gmail tokens for {self.entity_id}:{self.user_id} ({storage_type})"
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
        """Refresh access token using refresh token with improved error handling."""
        try:
            logger.info(
                f"Refreshing Gmail access token for {self.entity_id}:{self.user_id}"
            )

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
                    timeout=30.0,  # Add timeout
                )

                if response.status_code == 200:
                    tokens = response.json()
                    logger.info(
                        f"Gmail token refresh successful for {self.entity_id}:{self.user_id}"
                    )

                    # Merge with existing tokens to preserve refresh token and other fields
                    stored_tokens = await self.get_stored_tokens()
                    if stored_tokens:
                        # Preserve refresh token and other important fields
                        tokens["refresh_token"] = stored_tokens.get(
                            "refresh_token", refresh_token
                        )
                        tokens["scope"] = stored_tokens.get(
                            "scope", " ".join(self.config.SCOPES)
                        )

                        # Preserve any other custom fields
                        for key, value in stored_tokens.items():
                            if key not in tokens and key not in [
                                "access_token",
                                "expires_in",
                            ]:
                                tokens[key] = value

                    # Store the refreshed tokens
                    await self.store_tokens(tokens)
                    return tokens

                elif response.status_code == 400:
                    # Handle specific error cases
                    error_data = response.json()
                    error_type = error_data.get("error", "unknown")
                    error_description = error_data.get(
                        "error_description", "No description"
                    )

                    if error_type == "invalid_grant":
                        logger.error(
                            f"Gmail refresh token is invalid for {self.entity_id}:{self.user_id}: {error_description}"
                        )
                        raise Exception(f"Invalid refresh token: {error_description}")
                    elif error_type == "invalid_client":
                        logger.error(
                            f"Gmail OAuth client credentials are invalid for {self.entity_id}:{self.user_id}: {error_description}"
                        )
                        raise Exception(f"Invalid OAuth client: {error_description}")
                    else:
                        logger.error(
                            f"Gmail token refresh failed with 400 for {self.entity_id}:{self.user_id}: {error_type} - {error_description}"
                        )
                        raise Exception(
                            f"Token refresh failed: {error_type} - {error_description}"
                        )

                else:
                    logger.error(
                        f"Gmail token refresh failed with status {response.status_code} for {self.entity_id}:{self.user_id}: {response.text}"
                    )
                    raise Exception(
                        f"Token refresh failed with status {response.status_code}: {response.text}"
                    )

        except httpx.TimeoutException:
            logger.error(
                f"Gmail token refresh timeout for {self.entity_id}:{self.user_id}"
            )
            raise Exception("Token refresh request timed out")
        except httpx.RequestError as e:
            logger.error(
                f"Gmail token refresh network error for {self.entity_id}:{self.user_id}: {e}"
            )
            raise Exception(f"Network error during token refresh: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error during Gmail token refresh for {self.entity_id}:{self.user_id}: {e}"
            )
            raise Exception(f"Unexpected error during token refresh: {e}")

    async def get_valid_credentials(self) -> Optional[Credentials]:
        """Get valid Google credentials for API calls with robust token refresh."""
        stored_tokens = await self.get_stored_tokens()
        if not stored_tokens:
            raise PlexusExternalAuthRequiredError("No stored Gmail tokens found")

        # Check if we have required tokens
        access_token = stored_tokens.get("access_token")
        refresh_token = stored_tokens.get("refresh_token")

        if not access_token:
            raise PlexusExternalAuthRequiredError(
                "No access token found in stored Gmail tokens"
            )

        if not refresh_token:
            raise PlexusExternalAuthRequiredError(
                "No refresh token found in stored Gmail tokens - cannot refresh"
            )

        # Create credentials object
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.config.CLIENT_ID,
            client_secret=self.config.CLIENT_SECRET,
            scopes=self.config.SCOPES,
        )

        # Check if token is expired and refresh if needed
        if credentials.expired and credentials.refresh_token:
            logger.info(
                f"Gmail token expired for {self.entity_id}:{self.user_id}, attempting refresh..."
            )

            try:
                # Attempt to refresh using Google's built-in refresh mechanism
                credentials.refresh(Request())

                # Store updated tokens
                updated_tokens = {
                    "access_token": credentials.token,
                    "refresh_token": credentials.refresh_token,
                    "token_type": "Bearer",
                    "expires_at": credentials.expiry.isoformat()
                    if credentials.expiry
                    else None,
                    "scope": " ".join(self.config.SCOPES),
                }

                # Preserve any other fields from original tokens
                for key, value in stored_tokens.items():
                    if key not in updated_tokens:
                        updated_tokens[key] = value

                await self.store_tokens(updated_tokens)
                logger.info(
                    f"Successfully refreshed Gmail tokens for {self.entity_id}:{self.user_id}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to refresh Gmail credentials for {self.entity_id}:{self.user_id}: {e}"
                )

                # Try manual refresh as fallback
                try:
                    logger.info(
                        f"Attempting manual token refresh for {self.entity_id}:{self.user_id}"
                    )
                    refreshed_tokens = await self.refresh_access_token(refresh_token)

                    if refreshed_tokens and refreshed_tokens.get("access_token"):
                        # Update credentials with new token
                        credentials.token = refreshed_tokens["access_token"]
                        logger.info(
                            f"Manual token refresh successful for {self.entity_id}:{self.user_id}"
                        )
                    else:
                        raise Exception("Manual refresh returned no valid tokens")

                except Exception as manual_refresh_error:
                    logger.error(
                        f"Manual token refresh also failed for {self.entity_id}:{self.user_id}: {manual_refresh_error}"
                    )

                    # Check if this is a permanent failure (invalid refresh token)
                    if "invalid_grant" in str(manual_refresh_error).lower():
                        logger.error(
                            f"Refresh token is invalid for {self.entity_id}:{self.user_id} - user must re-authenticate"
                        )
                        raise PlexusExternalAuthRequiredError(
                            "Gmail refresh token is invalid - please re-authenticate your Gmail integration"
                        )
                    else:
                        raise PlexusExternalAuthRequiredError(
                            f"Failed to refresh Gmail credentials: {manual_refresh_error}"
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
                logger.error(f"Error revoking Gmail tokens: {e}")

        # Remove from storage
        service = await self.get_unified_service()
        await service.delete_oauth_tokens(
            self.entity_id,
            self.user_id,
            "gmail",
        )

    async def migrate_to_tenant_storage(self) -> bool:
        """
        Migration is no longer needed - all tokens are now stored at tenant level.

        Returns:
            True (always successful since no migration is needed)
        """
        logger.info("Migration not needed - Gmail tokens are already at tenant level")
        return True


# Factory functions for easy instantiation


async def create_gmail_auth_tenant_level(
    entity_id: str, user_id: str
) -> UnifiedGmailAuth:
    """
    Create Gmail auth instance using new tenant-level tokens.
    For new code using the updated architecture.
    """
    return UnifiedGmailAuth(
        entity_id=entity_id,
        user_id=user_id,
        use_tenant_storage=True,
    )


async def create_gmail_auth_unified(entity_id: str, user_id: str) -> UnifiedGmailAuth:
    """
    Create Gmail auth instance with unified access (recommended).
    Reads from both storages (prefers tenant-level) and saves to tenant-level.
    """
    return UnifiedGmailAuth(
        entity_id=entity_id,
        user_id=user_id,
        use_tenant_storage=True,
    )
