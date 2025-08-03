import logging
from fastapi import APIRouter, Depends, HTTPException, Path, Header, status
from typing import Annotated, Optional
from datetime import datetime, timezone

from .models import (
    UserRegistrationRequest,
    PlexusUserAuthTokenResponse,
    PlexusUserAuthTokenData,
)
from .errors import PlexusUserAuthTokenGenerationError
from .token_manager import DefaultPlexusUserTokenManager, PlexusUserTokenManagerProtocol
from .storage_interfaces import AbstractPlexusUserAuthTokenStore
from .dependencies import verify_host_app_secret
from .sqlite_user_auth_token_store import get_sqlite_plexus_user_auth_token_store
from ..settings import settings
from ..dependencies import get_tenant_config_store_dependency
from ..tenants.storage_interfaces import AbstractTenantConfigStore
from ..tenants.models import TenantConfigCreate
from ..tenants.storage_interfaces import AbstractTenantStore
from ..tenants.sqlite_tenant_store import get_sqlite_tenant_store

logger = logging.getLogger(__name__)
plexus_auth_router = APIRouter()


async def get_plexus_user_auth_token_store_dependency() -> (
    AbstractPlexusUserAuthTokenStore
):
    """
    Returns the configured token store implementation.
    Currently uses SQLite but can be extended to support multiple backends.
    """
    return await get_sqlite_plexus_user_auth_token_store()


def get_plexus_user_token_manager_dependency() -> PlexusUserTokenManagerProtocol:
    """Returns the default token manager for generating and hashing tokens."""
    return DefaultPlexusUserTokenManager()


@plexus_auth_router.post(
    "/register-user",
    response_model=PlexusUserAuthTokenResponse,
    summary="Register a host application user and get a Plexus User Auth Token",
    tags=["Plexus User Authentication"],
)
async def register_user_and_get_token(
    request_data: UserRegistrationRequest,
    entity_id: Annotated[
        str, Path(description="The tenant identifier for this registration.")
    ],
    token_store: Annotated[
        AbstractPlexusUserAuthTokenStore,
        Depends(get_plexus_user_auth_token_store_dependency),
    ],
    token_manager: Annotated[
        PlexusUserTokenManagerProtocol,
        Depends(get_plexus_user_token_manager_dependency),
    ],
    _: Annotated[str, Depends(verify_host_app_secret)],
):
    """
    Registers a user from a host application and generates a Plexus authentication token.

    If the user already exists, generates a new token and updates the existing record.
    The host application secret is verified via dependency injection before this handler executes.
    """
    logger.info(
        f"Attempting user registration for entity '{entity_id}', "
        f"host_app_user_id: '{request_data.user_id_from_host_app}'."
    )

    # Additional safety check for registration secret configuration
    if not settings.host_app_registration_secret:
        logger.warning(
            "HOST_APP_REGISTRATION_SECRET is not set, yet request proceeded. "
            "This indicates a potential logic flaw if header was checked."
        )

    persistent_user_id = request_data.user_id_from_host_app

    # Check if user already exists in the system
    existing_token_data = await token_store.get_token_data_by_user_id(
        entity_id, persistent_user_id
    )

    if existing_token_data:
        logger.info(
            f"User '{persistent_user_id}' in entity '{entity_id}' already exists. "
            f"Generating a new token and updating record."
        )

    try:
        # Generate new token and its hash for secure storage
        plexus_user_auth_token, token_hash = token_manager.generate_token_and_hash()

        # Create token data record with current timestamp
        new_token_data = PlexusUserAuthTokenData(
            entity_id=entity_id,
            persistent_user_id=persistent_user_id,
            token_hash=token_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
            last_used_at=datetime.now(timezone.utc).isoformat(),
        )

        # Save or update the token data in storage
        await token_store.save_token_data(new_token_data)

        logger.info(
            f"Successfully processed Plexus User Auth Token for user '{persistent_user_id}' "
            f"in entity '{entity_id}'."
        )

        return PlexusUserAuthTokenResponse(
            plexus_user_auth_token=plexus_user_auth_token,
            persistent_user_id=persistent_user_id,
        )

    except Exception as e:
        logger.error(
            f"Error during token generation/storage for user '{persistent_user_id}': {e}",
            exc_info=True,
        )
        raise PlexusUserAuthTokenGenerationError(
            detail=f"Could not process user token: {str(e)}"
        )


@plexus_auth_router.post("/register-base-config")
async def register_base_config(
    entity_id: Annotated[
        str, Path(description="The tenant identifier for this registration.")
    ],
    user_registration: UserRegistrationRequest,
    tenant_config_store: Annotated[
        AbstractTenantConfigStore, Depends(get_tenant_config_store_dependency)
    ],
    tenant_store: Annotated[AbstractTenantStore, Depends(get_sqlite_tenant_store)],
    token_manager: Annotated[
        PlexusUserTokenManagerProtocol,
        Depends(get_plexus_user_token_manager_dependency),
    ],
    token_store: Annotated[
        AbstractPlexusUserAuthTokenStore,
        Depends(get_plexus_user_auth_token_store_dependency),
    ],
    host_app_secret: Annotated[Optional[str], Header(alias="X-Host-App-Secret")] = None,
) -> PlexusUserAuthTokenResponse:
    """
    Register a base configuration for a tenant and create a user auth token.

    This endpoint implements the new architecture workflow where:
    1. Admin creates tenant → Gets entity_id
    2. System creates base config for that tenant → Default profile
    3. User can later create additional configs → Same OAuth, different preferences

    This replaces the old concept of user registration within a tenant.
    """
    if not host_app_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required X-Host-App-Secret header",
        )

    if host_app_secret != settings.host_app_registration_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Host App Secret"
        )

    try:
        # Verify tenant exists
        tenant = await tenant_store.get_tenant_by_entity_id(entity_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with entity_id '{entity_id}' not found",
            )

        # Create base config for the tenant
        base_config_id = "base"  # Standard ID for the base config
        base_config = TenantConfigCreate(
            entity_id=entity_id,
            config_id=base_config_id,
            config_name="Default Profile",
            config_type="profile",
            is_default=True,
            settings_json={},
        )

        # Check if base config already exists
        existing_config = await tenant_config_store.get_config_by_id(
            entity_id, base_config_id
        )
        if existing_config:
            logger.info(
                f"Base config already exists for tenant {entity_id}, skipping creation"
            )
        else:
            await tenant_config_store.create_config(base_config)
            logger.info(f"Created base config for tenant {entity_id}")

        # Create user auth token using the config_id as the persistent_user_id
        # This maintains compatibility with existing auth system while using new concept
        persistent_user_id = base_config_id

        # Generate token
        token = token_manager.generate_token()
        token_hash = token_manager.hash_token(token)

        # Store token data
        token_data = PlexusUserAuthTokenData(
            entity_id=entity_id,
            persistent_user_id=persistent_user_id,
            token_hash=token_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        await token_store.save_token_data(token_data)

        logger.info(
            f"Base config and auth token created for tenant {entity_id}, config {persistent_user_id}"
        )

        return PlexusUserAuthTokenResponse(
            plexus_user_auth_token=token,
            persistent_user_id=persistent_user_id,
            message="Base config registered and user token created successfully.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during base config registration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during base config registration",
        )
