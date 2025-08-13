# mcp_plexus/tenants/endpoints.py
import logging
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from typing import List, Annotated

from .models import Tenant, TenantCreate, TenantUpdate
from .service import TenantService
from .sqlite_tenant_store import get_sqlite_tenant_store
from .storage_interfaces import AbstractTenantStore
from ..dependencies import (
    get_admin_api_key,
    get_tenant_config_store_dependency,
    get_tenant_store_dependency,
)
from .models import TenantConfigCreate, TenantConfigUpdate, TenantConfigResponse
from .storage_interfaces import AbstractTenantConfigStore

logger = logging.getLogger(__name__)

# Admin router for tenant management - requires admin API key authentication
tenants_admin_router = APIRouter(
    prefix="/admin/tenants",
    tags=["Admin - Tenants"],
    dependencies=[Depends(get_admin_api_key)],
)


async def get_tenant_service(
    tenant_store: Annotated[AbstractTenantStore, Depends(get_sqlite_tenant_store)],
) -> TenantService:
    """Factory function to create TenantService with injected store dependency."""
    return TenantService(tenant_store)


@tenants_admin_router.post(
    "/", response_model=Tenant, status_code=status.HTTP_201_CREATED
)
async def create_tenant_endpoint(
    tenant_create: TenantCreate,
    service: Annotated[TenantService, Depends(get_tenant_service)],
):
    """Create a new tenant. Returns 409 if tenant with entity_id already exists."""
    logger.info(f"API: Received request to create tenant: {tenant_create.model_dump()}")
    try:
        # Service returns TenantInDB model, convert to API response model
        created_tenant_in_db = await service.create_tenant(tenant_create)
        return Tenant.model_validate(created_tenant_in_db)
    except ValueError as e:
        logger.warning(
            f"API: Tenant creation failed for entity_id '{tenant_create.entity_id}': {e}"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(
            f"API: Unexpected error creating tenant '{tenant_create.entity_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create tenant.",
        )


@tenants_admin_router.get("/{entity_id}", response_model=Tenant)
async def get_tenant_endpoint(
    entity_id: Annotated[str, Path(description="The ID of the tenant to retrieve")],
    service: Annotated[TenantService, Depends(get_tenant_service)],
):
    """Retrieve a specific tenant by entity_id."""
    tenant_in_db = await service.get_tenant(entity_id)
    if not tenant_in_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    return Tenant.model_validate(tenant_in_db)


@tenants_admin_router.get("/", response_model=List[Tenant])
@tenants_admin_router.get("", response_model=List[Tenant], include_in_schema=False)
async def list_tenants_endpoint(
    service: Annotated[TenantService, Depends(get_tenant_service)],
    skip: Annotated[int, Query(ge=0, description="Number of tenants to skip.")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Maximum number of tenants to return.")
    ] = 100,
):
    """List all tenants with pagination support. Handles both trailing slash variants."""
    tenants_in_db = await service.list_tenants(skip=skip, limit=limit)
    return [Tenant.model_validate(t) for t in tenants_in_db]


@tenants_admin_router.put("/{entity_id}", response_model=Tenant)
async def update_tenant_endpoint(
    entity_id: Annotated[str, Path(description="The ID of the tenant to update")],
    tenant_update: TenantUpdate,
    service: Annotated[TenantService, Depends(get_tenant_service)],
):
    """Update an existing tenant. Returns 404 if tenant does not exist."""
    updated_tenant_in_db = await service.update_tenant(entity_id, tenant_update)
    if not updated_tenant_in_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    return Tenant.model_validate(updated_tenant_in_db)


@tenants_admin_router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant_endpoint(
    entity_id: Annotated[str, Path(description="The ID of the tenant to delete")],
    service: Annotated[TenantService, Depends(get_tenant_service)],
):
    """Delete a tenant by entity_id. Returns 404 if tenant does not exist."""
    deleted = await service.delete_tenant(entity_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found or could not be deleted.",
        )
    return None


@tenants_admin_router.post("/{entity_id}/configs/", response_model=TenantConfigResponse)
async def create_tenant_config(
    entity_id: str,
    config_create: TenantConfigCreate,
    tenant_config_store: Annotated[
        AbstractTenantConfigStore, Depends(get_tenant_config_store_dependency)
    ],
    tenant_store: Annotated[AbstractTenantStore, Depends(get_tenant_store_dependency)],
    admin_api_key: Annotated[str, Depends(get_admin_api_key)],
):
    """
    Create a new configuration/profile for a tenant.

    This endpoint creates configs which replace the concept of users within tenants.
    Each config represents a different personality/setting profile for the same human user.
    """
    try:
        # Ensure the entity_id in path matches the one in body
        if config_create.entity_id != entity_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Entity ID in path must match entity ID in request body",
            )

        # Check if tenant exists
        tenant = await tenant_store.get_tenant_by_entity_id(entity_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with entity_id '{entity_id}' not found",
            )

        config_in_db = await tenant_config_store.create_config(config_create)

        return TenantConfigResponse(
            entity_id=config_in_db.entity_id,
            config_id=config_in_db.config_id,
            config_name=config_in_db.config_name,
            config_type=config_in_db.config_type,
            is_default=config_in_db.is_default,
            settings_json=config_in_db.settings_json,
            created_at=config_in_db.created_at.isoformat(),
            updated_at=config_in_db.updated_at.isoformat(),
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating tenant config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during config creation",
        )


@tenants_admin_router.get(
    "/{entity_id}/configs/", response_model=List[TenantConfigResponse]
)
async def list_tenant_configs(
    entity_id: str,
    tenant_config_store: Annotated[
        AbstractTenantConfigStore, Depends(get_tenant_config_store_dependency)
    ],
    tenant_store: Annotated[AbstractTenantStore, Depends(get_tenant_store_dependency)],
    admin_api_key: Annotated[str, Depends(get_admin_api_key)],
    skip: int = 0,
    limit: int = 100,
):
    """
    List all configurations/profiles for a specific tenant.
    """
    try:
        # Check if tenant exists
        tenant = await tenant_store.get_tenant_by_entity_id(entity_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with entity_id '{entity_id}' not found",
            )

        configs = await tenant_config_store.list_configs_for_tenant(
            entity_id, skip, limit
        )

        return [
            TenantConfigResponse(
                entity_id=config.entity_id,
                config_id=config.config_id,
                config_name=config.config_name,
                config_type=config.config_type,
                is_default=config.is_default,
                settings_json=config.settings_json,
                created_at=config.created_at.isoformat(),
                updated_at=config.updated_at.isoformat(),
            )
            for config in configs
        ]

    except Exception as e:
        logger.error(f"Error listing tenant configs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during config listing",
        )


@tenants_admin_router.get(
    "/{entity_id}/configs/{config_id}", response_model=TenantConfigResponse
)
async def get_tenant_config(
    entity_id: str,
    config_id: str,
    tenant_config_store: Annotated[
        AbstractTenantConfigStore, Depends(get_tenant_config_store_dependency)
    ],
    admin_api_key: Annotated[str, Depends(get_admin_api_key)],
):
    """
    Get a specific configuration/profile for a tenant.
    """
    try:
        config = await tenant_config_store.get_config_by_id(entity_id, config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config '{config_id}' not found for tenant '{entity_id}'",
            )

        return TenantConfigResponse(
            entity_id=config.entity_id,
            config_id=config.config_id,
            config_name=config.config_name,
            config_type=config.config_type,
            is_default=config.is_default,
            settings_json=config.settings_json,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Error getting tenant config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during config retrieval",
        )


@tenants_admin_router.put(
    "/{entity_id}/configs/{config_id}", response_model=TenantConfigResponse
)
async def update_tenant_config(
    entity_id: str,
    config_id: str,
    config_update: TenantConfigUpdate,
    tenant_config_store: Annotated[
        AbstractTenantConfigStore, Depends(get_tenant_config_store_dependency)
    ],
    admin_api_key: Annotated[str, Depends(get_admin_api_key)],
):
    """
    Update a specific configuration/profile for a tenant.
    """
    try:
        updated_config = await tenant_config_store.update_config(
            entity_id, config_id, config_update
        )
        if not updated_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config '{config_id}' not found for tenant '{entity_id}'",
            )

        return TenantConfigResponse(
            entity_id=updated_config.entity_id,
            config_id=updated_config.config_id,
            config_name=updated_config.config_name,
            config_type=updated_config.config_type,
            is_default=updated_config.is_default,
            settings_json=updated_config.settings_json,
            created_at=updated_config.created_at.isoformat(),
            updated_at=updated_config.updated_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Error updating tenant config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during config update",
        )


@tenants_admin_router.delete("/{entity_id}/configs/{config_id}")
async def delete_tenant_config(
    entity_id: str,
    config_id: str,
    tenant_config_store: Annotated[
        AbstractTenantConfigStore, Depends(get_tenant_config_store_dependency)
    ],
    admin_api_key: Annotated[str, Depends(get_admin_api_key)],
):
    """
    Delete a specific configuration/profile for a tenant.
    """
    try:
        deleted = await tenant_config_store.delete_config(entity_id, config_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config '{config_id}' not found for tenant '{entity_id}'",
            )

        return {"message": f"Config '{config_id}' deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting tenant config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during config deletion",
        )


@tenants_admin_router.post(
    "/{entity_id}/configs/{config_id}/set-default", response_model=TenantConfigResponse
)
async def set_default_tenant_config(
    entity_id: str,
    config_id: str,
    tenant_config_store: Annotated[
        AbstractTenantConfigStore, Depends(get_tenant_config_store_dependency)
    ],
    admin_api_key: Annotated[str, Depends(get_admin_api_key)],
):
    """
    Set a specific configuration/profile as the default for a tenant.
    """
    try:
        updated_config = await tenant_config_store.set_default_config(
            entity_id, config_id
        )
        if not updated_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config '{config_id}' not found for tenant '{entity_id}'",
            )

        return TenantConfigResponse(
            entity_id=updated_config.entity_id,
            config_id=updated_config.config_id,
            config_name=updated_config.config_name,
            config_type=updated_config.config_type,
            is_default=updated_config.is_default,
            settings_json=updated_config.settings_json,
            created_at=updated_config.created_at.isoformat(),
            updated_at=updated_config.updated_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Error setting default tenant config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during default config setting",
        )
