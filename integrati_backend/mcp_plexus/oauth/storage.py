# mcp_plexus/oauth/storage.py
import logging
from typing import Optional

import redis.asyncio as aioredis

from ..settings import settings as plexus_global_settings
from .storage_interfaces import (
    AbstractAuthCodeStore,
    AbstractOAuthTokenStore,
    AbstractExternalOAuthProviderConfigStore,
    AbstractOAuthClientStore,
)
from .models import (
    AuthCodeData,
    AccessTokenData,
    RefreshTokenData,
    OAuthProviderSettings,
)

# SQLite implementations and their factory functions
from .sqlite_oauth_internal_token_store import get_sqlite_oauth_internal_token_store
from .sqlite_auth_code_store import get_sqlite_auth_code_store
from .sqlite_external_oauth_provider_config_store import (
    get_sqlite_external_oauth_provider_config_store,
)
from .sqlite_oauth_internal_client_store import get_sqlite_internal_oauth_client_store
from .sqlite_tenant_external_token_store import get_sqlite_tenant_external_token_store

logger = logging.getLogger(__name__)


class RedisAuthCodeStore(AbstractAuthCodeStore):
    """
    Redis-based storage for OAuth authorization codes with automatic expiration.

    Auth codes are temporary tokens with a short TTL for security purposes.
    """

    _redis_client: Optional[aioredis.Redis] = None
    AUTH_CODE_TTL_SECONDS: int = 600  # 10 minutes default TTL

    def __init__(self, auth_code_ttl_seconds: Optional[int] = None):
        if auth_code_ttl_seconds is not None:
            self.AUTH_CODE_TTL_SECONDS = auth_code_ttl_seconds
        logger.info(
            f"RedisAuthCodeStore initialized. TTL: {self.AUTH_CODE_TTL_SECONDS}s."
        )

    async def initialize(self) -> None:
        """Establish Redis connection with configured parameters."""
        if self._redis_client:
            return

        connection_params = {
            "host": plexus_global_settings.redis_host,
            "port": plexus_global_settings.redis_port,
            "db": plexus_global_settings.redis_db,
            "decode_responses": False,
        }

        if plexus_global_settings.redis_password:
            connection_params["password"] = plexus_global_settings.redis_password

        try:
            self._redis_client = aioredis.Redis(**connection_params)
            await self._redis_client.ping()
            logger.info("RedisAuthCodeStore: Successfully connected to Redis.")
        except Exception as e:
            logger.error(f"RedisAuthCodeStore: Failed to connect: {e}", exc_info=True)
            self._redis_client = None
            raise

    async def teardown(self) -> None:
        """Clean up Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            logger.info("RedisAuthCodeStore: Connection closed.")

    async def _get_client(self) -> aioredis.Redis:
        """Get initialized Redis client or raise error if not ready."""
        if not self._redis_client:
            raise RuntimeError("RedisAuthCodeStore not initialized.")
        return self._redis_client

    def _get_key(self, code: str) -> str:
        """Generate Redis key for auth code storage."""
        return f"plexus:oauth:auth_code:{code}"

    async def save_auth_code(self, auth_code_data: AuthCodeData) -> None:
        """Save auth code with automatic expiration."""
        client = await self._get_client()
        await client.set(
            self._get_key(auth_code_data.code),
            auth_code_data.model_dump_json().encode("utf-8"),
            ex=self.AUTH_CODE_TTL_SECONDS,
        )
        logger.info(
            f"Saved Redis auth code '{auth_code_data.code}' with TTL {self.AUTH_CODE_TTL_SECONDS}s."
        )

    async def load_auth_code(self, code: str) -> Optional[AuthCodeData]:
        """Load auth code data, returning None if not found or corrupted."""
        client = await self._get_client()
        data_bytes = await client.get(self._get_key(code))
        if data_bytes:
            try:
                return AuthCodeData.model_validate_json(data_bytes.decode("utf-8"))
            except Exception as e:
                logger.error(
                    f"Error deserializing Redis auth code '{code}': {e}", exc_info=True
                )
                return None
        return None

    async def delete_auth_code(self, code: str) -> None:
        """Remove auth code from Redis storage."""
        client = await self._get_client()
        await client.delete(self._get_key(code))
        logger.info(f"Deleted Redis auth code '{code}'.")


class RedisOAuthTokenStore(AbstractOAuthTokenStore):
    """
    Redis-based storage for internal OAuth server tokens (access and refresh).

    Tokens are stored with appropriate TTLs for security and cleanup.
    """

    _redis_client: Optional[aioredis.Redis] = None
    ACCESS_TOKEN_TTL_SECONDS: int = 3600  # 1 hour default TTL
    REFRESH_TOKEN_TTL_SECONDS: int = 2592000  # 30 days default TTL

    def __init__(
        self,
        access_token_ttl_seconds: Optional[int] = None,
        refresh_token_ttl_seconds: Optional[int] = None,
    ):
        if access_token_ttl_seconds is not None:
            self.ACCESS_TOKEN_TTL_SECONDS = access_token_ttl_seconds
        if refresh_token_ttl_seconds is not None:
            self.REFRESH_TOKEN_TTL_SECONDS = refresh_token_ttl_seconds
        logger.info(
            f"RedisOAuthTokenStore initialized. Access TTL: {self.ACCESS_TOKEN_TTL_SECONDS}s, "
            f"Refresh TTL: {self.REFRESH_TOKEN_TTL_SECONDS}s."
        )

    async def initialize(self) -> None:
        """Establish Redis connection with configured parameters."""
        if self._redis_client:
            return

        connection_params = {
            "host": plexus_global_settings.redis_host,
            "port": plexus_global_settings.redis_port,
            "db": plexus_global_settings.redis_db,
            "decode_responses": False,
        }

        if plexus_global_settings.redis_password:
            connection_params["password"] = plexus_global_settings.redis_password

        try:
            self._redis_client = aioredis.Redis(**connection_params)
            await self._redis_client.ping()
            logger.info("RedisOAuthTokenStore: Successfully connected to Redis.")
        except Exception as e:
            logger.error(f"RedisOAuthTokenStore: Failed to connect: {e}", exc_info=True)
            self._redis_client = None
            raise

    async def teardown(self) -> None:
        """Clean up Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            logger.info("RedisOAuthTokenStore: Connection closed.")

    async def _get_client(self) -> aioredis.Redis:
        """Get initialized Redis client or raise error if not ready."""
        if not self._redis_client:
            raise RuntimeError("RedisOAuthTokenStore not initialized.")
        return self._redis_client

    def _get_access_token_key(self, token: str) -> str:
        """Generate Redis key for access token storage."""
        return f"plexus:oauth:access_token:{token}"

    def _get_refresh_token_key(self, token: str) -> str:
        """Generate Redis key for refresh token storage."""
        return f"plexus:oauth:refresh_token:{token}"

    async def save_access_token(self, access_token_data: AccessTokenData) -> None:
        """Save access token with automatic expiration."""
        client = await self._get_client()
        await client.set(
            self._get_access_token_key(access_token_data.access_token),
            access_token_data.model_dump_json().encode("utf-8"),
            ex=self.ACCESS_TOKEN_TTL_SECONDS,
        )
        logger.info(
            f"Saved Redis access token '{access_token_data.access_token}' with TTL {self.ACCESS_TOKEN_TTL_SECONDS}s."
        )

    async def load_access_token(self, access_token: str) -> Optional[AccessTokenData]:
        """Load access token data, returning None if not found or corrupted."""
        client = await self._get_client()
        data_bytes = await client.get(self._get_access_token_key(access_token))
        if data_bytes:
            try:
                return AccessTokenData.model_validate_json(data_bytes.decode("utf-8"))
            except Exception as e:
                logger.error(
                    f"Error deserializing Redis access token '{access_token}': {e}",
                    exc_info=True,
                )
                return None
        return None

    async def delete_access_token(self, access_token: str) -> None:
        """Remove access token from Redis storage."""
        client = await self._get_client()
        await client.delete(self._get_access_token_key(access_token))
        logger.info(f"Deleted Redis access token '{access_token}'.")

    async def save_refresh_token(self, refresh_token_data: RefreshTokenData) -> None:
        """Save refresh token with automatic expiration."""
        client = await self._get_client()
        await client.set(
            self._get_refresh_token_key(refresh_token_data.refresh_token),
            refresh_token_data.model_dump_json().encode("utf-8"),
            ex=self.REFRESH_TOKEN_TTL_SECONDS,
        )
        logger.info(
            f"Saved Redis refresh token '{refresh_token_data.refresh_token}' with TTL {self.REFRESH_TOKEN_TTL_SECONDS}s."
        )

    async def load_refresh_token(
        self, refresh_token: str
    ) -> Optional[RefreshTokenData]:
        """Load refresh token data, returning None if not found or corrupted."""
        client = await self._redis_client
        data_bytes = await client.get(self._get_refresh_token_key(refresh_token))
        if data_bytes:
            try:
                return RefreshTokenData.model_validate_json(data_bytes.decode("utf-8"))
            except Exception as e:
                logger.error(
                    f"Error deserializing Redis refresh token '{refresh_token}': {e}",
                    exc_info=True,
                )
                return None
        return None

    async def delete_refresh_token(self, refresh_token: str) -> None:
        """Remove refresh token from Redis storage."""
        client = await self._get_client()
        await client.delete(self._get_refresh_token_key(refresh_token))
        logger.info(f"Deleted Redis refresh token '{refresh_token}'.")


class RedisExternalOAuthProviderConfigStore(AbstractExternalOAuthProviderConfigStore):
    """
    Redis-based storage for external OAuth provider configurations.

    Provider configs are stored per entity with no expiration.
    """

    _redis_client: Optional[aioredis.Redis] = None

    def __init__(self):
        logger.info("RedisExternalOAuthProviderConfigStore initialized.")

    async def initialize(self) -> None:
        """Establish Redis connection with configured parameters."""
        if self._redis_client:
            return

        connection_params = {
            "host": plexus_global_settings.redis_host,
            "port": plexus_global_settings.redis_port,
            "db": plexus_global_settings.redis_db,
            "decode_responses": False,
        }

        if plexus_global_settings.redis_password:
            connection_params["password"] = plexus_global_settings.redis_password

        try:
            self._redis_client = aioredis.Redis(**connection_params)
            await self._redis_client.ping()
            logger.info(
                "RedisExternalOAuthProviderConfigStore: Successfully connected to Redis."
            )
        except Exception as e:
            logger.error(
                f"RedisExternalOAuthProviderConfigStore: Failed to connect: {e}",
                exc_info=True,
            )
            self._redis_client = None
            raise

    async def teardown(self) -> None:
        """Clean up Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            logger.info("RedisExternalOAuthProviderConfigStore: Connection closed.")

    async def _get_client(self) -> aioredis.Redis:
        """Get initialized Redis client or raise error if not ready."""
        if not self._redis_client:
            raise RuntimeError("RedisExternalOAuthProviderConfigStore not initialized.")
        return self._redis_client

    def _get_key(self, entity_id: str, provider_name: str) -> str:
        """Generate Redis key for provider config storage."""
        return f"plexus:ext_oauth_provider_config:{entity_id}:{provider_name}"

    async def save_provider_config(
        self, entity_id: str, provider_config: OAuthProviderSettings
    ) -> None:
        """Save provider configuration to Redis storage."""
        client = await self._get_client()
        key = self._get_key(entity_id, provider_config.provider_name)
        await client.set(
            key,
            provider_config.model_dump_json().encode("utf-8"),
        )
        logger.info(
            f"Saved Redis provider config for E:{entity_id}, P:{provider_config.provider_name}."
        )

    async def load_provider_config(
        self, entity_id: str, provider_name: str
    ) -> Optional[OAuthProviderSettings]:
        """Load provider configuration from Redis storage."""
        client = await self._get_client()
        key = self._get_key(entity_id, provider_name)
        data_bytes = await client.get(key)
        if data_bytes:
            try:
                return OAuthProviderSettings.model_validate_json(
                    data_bytes.decode("utf-8")
                )
            except Exception as e:
                logger.error(
                    f"Error deserializing Redis provider config for "
                    f"E:{entity_id}, P:{provider_name}: {e}",
                    exc_info=True,
                )
                return None
        return None

    async def delete_provider_config(self, entity_id: str, provider_name: str) -> None:
        """Remove provider configuration from Redis storage."""
        client = await self._get_client()
        key = self._get_key(entity_id, provider_name)
        await client.delete(key)
        logger.info(
            f"Deleted Redis provider config for E:{entity_id}, P:{provider_name}."
        )

    async def load_all_provider_configs_for_entity(
        self, entity_id: str
    ) -> list[OAuthProviderSettings]:
        """Load all provider configurations for an entity from Redis storage."""
        client = await self._get_client()
        pattern = f"plexus:ext_oauth_provider_config:{entity_id}:*"
        keys = await client.keys(pattern)
        configs = []
        for key in keys:
            data_bytes = await client.get(key)
            if data_bytes:
                try:
                    config = OAuthProviderSettings.model_validate_json(
                        data_bytes.decode("utf-8")
                    )
                    configs.append(config)
                except Exception as e:
                    logger.error(
                        f"Error deserializing Redis provider config from key '{key}': {e}",
                        exc_info=True,
                    )
        return configs


# Global singleton instances for each store type
_internal_oauth_token_store_instance: Optional[AbstractOAuthTokenStore] = None
_internal_auth_code_store_instance: Optional[AbstractAuthCodeStore] = None
_external_oauth_provider_config_store_instance: Optional[
    AbstractExternalOAuthProviderConfigStore
] = None
_internal_oauth_client_store_instance: Optional[AbstractOAuthClientStore] = None


async def get_internal_oauth_token_store() -> AbstractOAuthTokenStore:
    """
    Factory function to get the configured internal OAuth token store instance.

    Returns a singleton instance based on the storage_backend setting.
    """
    global _internal_oauth_token_store_instance

    if _internal_oauth_token_store_instance is None:
        if plexus_global_settings.storage_backend == "sqlite":
            logger.info(
                "Using SQLiteOAuthInternalTokenStore for internal OAuth tokens."
            )
            _internal_oauth_token_store_instance = (
                await get_sqlite_oauth_internal_token_store()
            )
        elif plexus_global_settings.storage_backend == "redis":
            logger.info("Using RedisOAuthTokenStore for internal OAuth tokens.")
            _internal_oauth_token_store_instance = RedisOAuthTokenStore()
            await _internal_oauth_token_store_instance.initialize()
        else:
            raise ValueError(
                f"Unsupported storage_backend for internal OAuth tokens: {plexus_global_settings.storage_backend}"
            )

    return _internal_oauth_token_store_instance


async def get_internal_auth_code_store() -> AbstractAuthCodeStore:
    """
    Factory function to get the configured internal OAuth auth code store instance.

    Returns a singleton instance based on the storage_backend setting.
    """
    global _internal_auth_code_store_instance

    if _internal_auth_code_store_instance is None:
        if plexus_global_settings.storage_backend == "sqlite":
            logger.info("Using SQLiteAuthCodeStore for internal OAuth auth codes.")
            _internal_auth_code_store_instance = await get_sqlite_auth_code_store()
        elif plexus_global_settings.storage_backend == "redis":
            logger.info("Using RedisAuthCodeStore for internal OAuth auth codes.")
            _internal_auth_code_store_instance = RedisAuthCodeStore()
            await _internal_auth_code_store_instance.initialize()
        else:
            raise ValueError(
                f"Unsupported storage_backend for internal OAuth auth codes: {plexus_global_settings.storage_backend}"
            )

    return _internal_auth_code_store_instance


async def get_external_oauth_provider_config_store() -> (
    AbstractExternalOAuthProviderConfigStore
):
    """
    Factory function to get the configured external OAuth provider config store instance.

    Returns a singleton instance based on the storage_backend setting.
    """
    global _external_oauth_provider_config_store_instance

    if _external_oauth_provider_config_store_instance is None:
        if plexus_global_settings.storage_backend == "sqlite":
            logger.info(
                "Using SQLiteExternalOAuthProviderConfigStore for external provider configs."
            )
            _external_oauth_provider_config_store_instance = (
                await get_sqlite_external_oauth_provider_config_store()
            )
        elif plexus_global_settings.storage_backend == "redis":
            logger.info(
                "Using RedisExternalOAuthProviderConfigStore for external provider configs."
            )
            _external_oauth_provider_config_store_instance = (
                RedisExternalOAuthProviderConfigStore()
            )
            await _external_oauth_provider_config_store_instance.initialize()
        else:
            raise ValueError(
                f"Unsupported storage_backend for external provider configs: {plexus_global_settings.storage_backend}"
            )

    return _external_oauth_provider_config_store_instance


async def get_internal_oauth_client_store() -> AbstractOAuthClientStore:
    """
    Factory function to get the configured internal OAuth client store instance.

    Returns a singleton instance based on the storage_backend setting.
    Note: Redis implementation is not yet available, falls back to SQLite.
    """
    global _internal_oauth_client_store_instance

    if _internal_oauth_client_store_instance is None:
        if plexus_global_settings.storage_backend == "sqlite":
            logger.info("Using SQLiteOAuthClientStore for internal OAuth clients.")
            _internal_oauth_client_store_instance = (
                await get_sqlite_internal_oauth_client_store()
            )
        elif plexus_global_settings.storage_backend == "redis":
            # Redis implementation not yet available, fallback to SQLite
            logger.error(
                "RedisOAuthClientStore is not yet implemented. Falling back to SQLite for internal clients."
            )
            _internal_oauth_client_store_instance = (
                await get_sqlite_internal_oauth_client_store()
            )
        else:
            raise ValueError(
                f"Unsupported storage_backend for internal OAuth clients: {plexus_global_settings.storage_backend}"
            )

    return _internal_oauth_client_store_instance


async def get_tenant_external_token_store():
    """
    Get the tenant external token store implementation.
    Currently returns SQLite implementation.
    """
    return await get_sqlite_tenant_external_token_store()
