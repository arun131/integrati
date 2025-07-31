# mcp_plexus/oauth/unified_token_service.py
"""
Unified OAuth Token Service

This service provides a unified interface for accessing OAuth tokens that works with both:
1. Legacy user-level tokens (for backward compatibility)  
2. New tenant-level tokens (for the new architecture)

It tries tenant-level tokens first, then falls back to user-level tokens if needed.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .storage_interfaces import AbstractUserExternalTokenStore, AbstractTenantExternalTokenStore
from .storage import get_user_external_token_store, get_tenant_external_token_store

logger = logging.getLogger(__name__)


class UnifiedOAuthTokenService:
    """
    Unified service for accessing OAuth tokens from both user-level and tenant-level storage.
    
    This service implements the migration strategy:
    1. First check tenant-level tokens (new architecture)
    2. If not found, check user-level tokens (legacy)
    3. Optionally migrate user-level tokens to tenant-level
    """
    
    def __init__(self):
        self._user_token_store: Optional[AbstractUserExternalTokenStore] = None
        self._tenant_token_store: Optional[AbstractTenantExternalTokenStore] = None
    
    async def _get_user_token_store(self) -> AbstractUserExternalTokenStore:
        """Lazy load user token store."""
        if self._user_token_store is None:
            self._user_token_store = await get_user_external_token_store()
        return self._user_token_store
    
    async def _get_tenant_token_store(self) -> AbstractTenantExternalTokenStore:
        """Lazy load tenant token store."""
        if self._tenant_token_store is None:
            self._tenant_token_store = await get_tenant_external_token_store()
        return self._tenant_token_store
    
    async def get_oauth_tokens(
        self, 
        entity_id: str, 
        user_id: str, 
        provider_name: str,
        prefer_tenant_level: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get OAuth tokens for a user/tenant and provider.
        
        Args:
            entity_id: The tenant's entity ID
            user_id: The user/config ID within the tenant  
            provider_name: OAuth provider name (e.g., 'gmail', 'calendar')
            prefer_tenant_level: If True, check tenant-level tokens first
            
        Returns:
            Token data dictionary if found, None otherwise
        """
        try:
            if prefer_tenant_level:
                # NEW ARCHITECTURE: Try tenant-level tokens first
                tenant_store = await self._get_tenant_token_store()
                tenant_tokens = await tenant_store.load_tenant_external_token(
                    entity_id, provider_name
                )
                if tenant_tokens:
                    logger.debug(f"Found tenant-level tokens for {entity_id}:{provider_name}")
                    return tenant_tokens
                
                # FALLBACK: Try user-level tokens
                user_store = await self._get_user_token_store()
                user_tokens = await user_store.load_user_external_token(
                    entity_id, user_id, provider_name
                )
                if user_tokens:
                    logger.debug(f"Found user-level tokens for {entity_id}:{user_id}:{provider_name}")
                    return user_tokens
            else:
                # LEGACY MODE: Try user-level tokens first
                user_store = await self._get_user_token_store()
                user_tokens = await user_store.load_user_external_token(
                    entity_id, user_id, provider_name
                )
                if user_tokens:
                    logger.debug(f"Found user-level tokens for {entity_id}:{user_id}:{provider_name}")
                    return user_tokens
                
                # FALLBACK: Try tenant-level tokens
                tenant_store = await self._get_tenant_token_store()
                tenant_tokens = await tenant_store.load_tenant_external_token(
                    entity_id, provider_name
                )
                if tenant_tokens:
                    logger.debug(f"Found tenant-level tokens for {entity_id}:{provider_name}")
                    return tenant_tokens
            
            logger.debug(f"No tokens found for {entity_id}:{user_id}:{provider_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting OAuth tokens for {entity_id}:{user_id}:{provider_name}: {e}")
            return None
    
    async def save_oauth_tokens(
        self,
        entity_id: str,
        user_id: str,
        provider_name: str,
        token_data: Dict[str, Any],
        use_tenant_level: bool = True
    ) -> bool:
        """
        Save OAuth tokens to either tenant-level or user-level storage.
        
        Args:
            entity_id: The tenant's entity ID
            user_id: The user/config ID within the tenant
            provider_name: OAuth provider name
            token_data: Token data to save
            use_tenant_level: If True, save to tenant-level storage
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if use_tenant_level:
                # NEW ARCHITECTURE: Save to tenant-level storage
                tenant_store = await self._get_tenant_token_store()
                await tenant_store.save_tenant_external_token(
                    entity_id, provider_name, token_data
                )
                logger.info(f"Saved tenant-level tokens for {entity_id}:{provider_name}")
            else:
                # LEGACY: Save to user-level storage
                user_store = await self._get_user_token_store()
                await user_store.save_user_external_token(
                    entity_id, user_id, provider_name, token_data
                )
                logger.info(f"Saved user-level tokens for {entity_id}:{user_id}:{provider_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving OAuth tokens for {entity_id}:{user_id}:{provider_name}: {e}")
            return False
    
    async def delete_oauth_tokens(
        self,
        entity_id: str,
        user_id: str,
        provider_name: str,
        delete_tenant_level: bool = True,
        delete_user_level: bool = False
    ) -> bool:
        """
        Delete OAuth tokens from storage.
        
        Args:
            entity_id: The tenant's entity ID
            user_id: The user/config ID within the tenant
            provider_name: OAuth provider name
            delete_tenant_level: If True, delete from tenant-level storage
            delete_user_level: If True, delete from user-level storage
            
        Returns:
            True if any deletion was successful, False otherwise
        """
        success = False
        
        try:
            if delete_tenant_level:
                tenant_store = await self._get_tenant_token_store()
                await tenant_store.delete_tenant_external_token(entity_id, provider_name)
                logger.info(f"Deleted tenant-level tokens for {entity_id}:{provider_name}")
                success = True
            
            if delete_user_level:
                user_store = await self._get_user_token_store()
                await user_store.delete_user_external_token(entity_id, user_id, provider_name)
                logger.info(f"Deleted user-level tokens for {entity_id}:{user_id}:{provider_name}")
                success = True
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting OAuth tokens for {entity_id}:{user_id}:{provider_name}: {e}")
            return False
    
    async def migrate_user_tokens_to_tenant(
        self,
        entity_id: str,
        user_id: str,
        provider_name: str
    ) -> bool:
        """
        Migrate user-level tokens to tenant-level storage.
        
        This is useful during the transition period to move existing
        user tokens to the new tenant-level architecture.
        
        Args:
            entity_id: The tenant's entity ID
            user_id: The user/config ID within the tenant
            provider_name: OAuth provider name
            
        Returns:
            True if migration was successful, False otherwise
        """
        try:
            # Get user-level tokens
            user_store = await self._get_user_token_store()
            user_tokens = await user_store.load_user_external_token(
                entity_id, user_id, provider_name
            )
            
            if not user_tokens:
                logger.debug(f"No user tokens to migrate for {entity_id}:{user_id}:{provider_name}")
                return False
            
            # Save to tenant-level storage
            tenant_store = await self._get_tenant_token_store()
            await tenant_store.save_tenant_external_token(
                entity_id, provider_name, user_tokens
            )
            
            logger.info(f"Migrated tokens from user-level to tenant-level for {entity_id}:{user_id}:{provider_name}")
            
            # Optionally delete user-level tokens after successful migration
            # await user_store.delete_user_external_token(entity_id, user_id, provider_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Error migrating tokens for {entity_id}:{user_id}:{provider_name}: {e}")
            return False
    
    async def list_tenant_providers(self, entity_id: str) -> List[str]:
        """
        List all OAuth providers configured for a tenant.
        
        This includes both tenant-level and user-level providers for compatibility.
        
        Args:
            entity_id: The tenant's entity ID
            
        Returns:
            List of provider names
        """
        providers = set()
        
        try:
            # Get tenant-level providers
            tenant_store = await self._get_tenant_token_store()
            tenant_providers = await tenant_store.list_tenant_providers(entity_id)
            providers.update(tenant_providers)
            
            # TODO: Could also check user-level providers for complete compatibility
            # but this might be expensive for tenants with many users
            
        except Exception as e:
            logger.error(f"Error listing providers for tenant {entity_id}: {e}")
        
        return list(providers)


# Global singleton instance
_unified_token_service_instance: Optional[UnifiedOAuthTokenService] = None


async def get_unified_oauth_token_service() -> UnifiedOAuthTokenService:
    """
    Get or create the singleton UnifiedOAuthTokenService instance.
    """
    global _unified_token_service_instance
    if _unified_token_service_instance is None:
        _unified_token_service_instance = UnifiedOAuthTokenService()
    return _unified_token_service_instance 