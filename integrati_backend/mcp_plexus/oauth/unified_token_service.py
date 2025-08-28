# mcp_plexus/oauth/unified_token_service.py
"""
Tenant-Level OAuth Token Service

This service provides a unified interface for accessing OAuth tokens at the tenant level.
All OAuth tokens are now stored and managed at the tenant level for better scalability
and simplified architecture.
"""

import logging
from typing import Optional, Dict, Any, List

from .storage_interfaces import AbstractTenantExternalTokenStore
from .storage import get_tenant_external_token_store

logger = logging.getLogger(__name__)


class TenantOAuthTokenService:
    """
    Service for accessing OAuth tokens from tenant-level storage.

    This service implements the new architecture where OAuth tokens
    are stored at the tenant level rather than per user/config.
    """

    def __init__(self):
        self._tenant_token_store: Optional[AbstractTenantExternalTokenStore] = None

    async def _get_tenant_token_store(self) -> AbstractTenantExternalTokenStore:
        """Lazy load tenant token store."""
        if self._tenant_token_store is None:
            self._tenant_token_store = await get_tenant_external_token_store()
        return self._tenant_token_store

    async def get_oauth_tokens(
        self,
        entity_id: str,
        user_id: str,  # Kept for API compatibility but not used
        provider_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get OAuth tokens for a tenant and provider.

        Args:
            entity_id: The tenant's entity ID
            user_id: The user/config ID within the tenant (kept for compatibility)
            provider_name: OAuth provider name (e.g., 'gmail', 'calendar')

        Returns:
            Token data dictionary if found, None otherwise
        """
        try:
            tenant_store = await self._get_tenant_token_store()
            tenant_tokens = await tenant_store.load_tenant_external_token(
                entity_id, provider_name
            )
            if tenant_tokens:
                logger.debug(
                    f"Found tenant-level tokens for {entity_id}:{provider_name}"
                )
                return tenant_tokens

            logger.debug(f"No tokens found for {entity_id}:{provider_name}")
            return None

        except Exception as e:
            logger.error(
                f"Error getting OAuth tokens for {entity_id}:{provider_name}: {e}"
            )
            return None

    async def save_oauth_tokens(
        self,
        entity_id: str,
        user_id: str,  # Kept for API compatibility but not used
        provider_name: str,
        token_data: Dict[str, Any],
    ) -> bool:
        """
        Save OAuth tokens to tenant-level storage.

        Args:
            entity_id: The tenant's entity ID
            user_id: The user/config ID within the tenant (kept for compatibility)
            provider_name: OAuth provider name
            token_data: Token data to save

        Returns:
            True if successful, False otherwise
        """
        try:
            tenant_store = await self._get_tenant_token_store()
            await tenant_store.save_tenant_external_token(
                entity_id, provider_name, token_data
            )
            logger.info(f"Saved tenant-level tokens for {entity_id}:{provider_name}")
            return True

        except Exception as e:
            logger.error(
                f"Error saving OAuth tokens for {entity_id}:{provider_name}: {e}"
            )
            return False

    async def delete_oauth_tokens(
        self,
        entity_id: str,
        user_id: str,  # Kept for API compatibility but not used
        provider_name: str,
    ) -> bool:
        """
        Delete OAuth tokens from tenant-level storage.

        Args:
            entity_id: The tenant's entity ID
            user_id: The user/config ID within the tenant (kept for compatibility)
            provider_name: OAuth provider name

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            tenant_store = await self._get_tenant_token_store()
            await tenant_store.delete_tenant_external_token(entity_id, provider_name)
            logger.info(f"Deleted tenant-level tokens for {entity_id}:{provider_name}")
            return True

        except Exception as e:
            logger.error(
                f"Error deleting OAuth tokens for {entity_id}:{provider_name}: {e}"
            )
            return False

    async def list_tenant_providers(self, entity_id: str) -> List[str]:
        """
        List all OAuth providers configured for a tenant.

        Args:
            entity_id: The tenant's entity ID

        Returns:
            List of provider names
        """
        try:
            tenant_store = await self._get_tenant_token_store()
            return await tenant_store.list_tenant_providers(entity_id)
        except Exception as e:
            logger.error(f"Error listing providers for tenant {entity_id}: {e}")
            return []


# Global singleton instance
_tenant_oauth_token_service_instance: Optional[TenantOAuthTokenService] = None


async def get_tenant_oauth_token_service() -> TenantOAuthTokenService:
    """
    Get or create the singleton TenantOAuthTokenService instance.
    """
    global _tenant_oauth_token_service_instance
    if _tenant_oauth_token_service_instance is None:
        _tenant_oauth_token_service_instance = TenantOAuthTokenService()
    return _tenant_oauth_token_service_instance


# Backward compatibility alias
get_unified_oauth_token_service = get_tenant_oauth_token_service
