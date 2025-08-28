"""Integration management endpoints for frontend."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from mcp_plexus.plexus_auth.dependencies import (
    get_current_plexus_user,
    get_current_plexus_user_from_token,
)
from mcp_plexus.oauth.provider import OAuthProvider
from analytics.logger import log_integration_event
from mcp_plexus.oauth.unified_token_service import get_unified_oauth_token_service

logger = logging.getLogger(__name__)

router = APIRouter()


class IntegrationRequest(BaseModel):
    """Request model for integration operations."""

    integration_name: str


class IntegrationResponse(BaseModel):
    """Response model for integration operations."""

    integration_name: str
    status: str
    message: str


@router.get("/integrations")
async def list_user_integrations(
    current_user: Dict[str, Any] = Depends(get_current_plexus_user),
):
    """
    List all integrations for the current user.

    Updated to support both user-level and tenant-level tokens using unified service.
    """
    try:
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        # Get unified token service for checking both storage types
        unified_service = await get_unified_oauth_token_service()

        # Get all integrations for this user/tenant
        integrations = []
        for integration_name in ["gmail", "calendar"]:
            # Check for tokens using unified service (tries tenant-level first, then user-level)
            token_data = await unified_service.get_oauth_tokens(
                entity_id, user_id, integration_name
            )

            if token_data:
                # Determine storage type for informational purposes
                tenant_service = await unified_service._get_tenant_token_store()
                tenant_tokens = await tenant_service.load_tenant_external_token(
                    entity_id, integration_name
                )
                storage_type = "tenant-level" if tenant_tokens else "user-level"

                integrations.append(
                    {
                        "name": integration_name,
                        "status": "connected",
                        "storage_type": storage_type,
                        "connected_at": token_data.get("created_at", "unknown"),
                    }
                )
            else:
                integrations.append(
                    {
                        "name": integration_name,
                        "status": "disconnected",
                        "storage_type": None,
                    }
                )

        return {
            "integrations": integrations,
            "entity_id": entity_id,
            "user_id": user_id,
            "architecture": "unified",  # Indicates support for both architectures
        }
    except Exception as e:
        logger.error(f"Error listing integrations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/integrations/{integration_name}/auth")
async def start_oauth_flow(
    integration_name: str,
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
):
    """
    Start OAuth flow for an integration.

    Updated to use tenant-level OAuth flow (new architecture).
    """
    try:
        logger.info(
            f"Starting OAuth flow for {integration_name}, current_user: {current_user}"
        )
        entity_id = current_user["entity_id"]

        # Validate integration name
        if integration_name not in ["gmail", "calendar"]:
            raise HTTPException(status_code=400, detail="Invalid integration name")

        # NEW ARCHITECTURE: Redirect to tenant-level OAuth endpoints
        # OAuth tokens will be stored at tenant level and shared across all configs
        if integration_name == "gmail":
            # Return Gmail OAuth URL
            auth_url = "http://localhost:8000/api/integrations/gmail/login"
        elif integration_name == "calendar":
            # Return Calendar OAuth URL
            auth_url = "http://localhost:8000/api/integrations/calendar/login"

        return {
            "auth_url": auth_url,
            "message": f"Redirect to {auth_url} to authorize {integration_name}",
            "entity_id": entity_id,
            "integration": integration_name,
            "architecture": "tenant-level",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting OAuth flow for {integration_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/integrations/{integration_name}/callback")
async def oauth_callback(
    integration_name: str,
    code: str,
    state: str,
    current_user: Dict[str, Any] = Depends(get_current_plexus_user),
):
    """Handle OAuth callback."""
    try:
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        # Validate integration name
        if integration_name not in ["gmail", "calendar"]:
            raise HTTPException(status_code=400, detail="Invalid integration name")

        # Parse state to verify it matches
        expected_state = f"{entity_id}:{user_id}:{integration_name}"
        if state != expected_state:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        # Handle OAuth callback
        oauth_provider = OAuthProvider(integration_name)
        tokens = await oauth_provider.handle_callback(code, state, entity_id, user_id)

        # Log the successful OAuth completion
        await log_integration_event(
            entity_id=entity_id,
            user_id=user_id,
            integration_name=integration_name,
            event_type="oauth_complete",
            metadata={"tokens_received": bool(tokens)},
            success=True,
        )

        return {
            "status": "success",
            "integration": integration_name,
            "message": "Integration connected successfully",
        }
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        await log_integration_event(
            entity_id=current_user["entity_id"],
            user_id=current_user["persistent_user_id"],
            integration_name=integration_name,
            event_type="oauth_complete",
            metadata={"error": str(e)},
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/integrations/{integration_name}")
async def disconnect_integration(
    integration_name: str,
    current_user: Dict[str, Any] = Depends(get_current_plexus_user),
):
    """
    Disconnect an integration by removing stored tokens.

    Updated to handle both user-level and tenant-level token removal.
    """
    try:
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        if integration_name not in ["gmail", "calendar"]:
            raise HTTPException(status_code=400, detail="Invalid integration name")

        # Get unified token service
        unified_service = await get_unified_oauth_token_service()

        # Check what tokens exist
        token_data = await unified_service.get_oauth_tokens(
            entity_id, user_id, integration_name
        )

        if not token_data:
            return {
                "message": f"{integration_name} was not connected",
                "integration": integration_name,
                "entity_id": entity_id,
            }

        # Revoke tokens if possible
        if integration_name == "gmail" and token_data.get("access_token"):
            try:
                import httpx

                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://oauth2.googleapis.com/revoke",
                        data={"token": token_data["access_token"]},
                    )
                logger.info(f"Revoked {integration_name} tokens for {entity_id}")
            except Exception as e:
                logger.warning(f"Failed to revoke {integration_name} tokens: {e}")

        # Remove tokens from storage
        success = await unified_service.delete_oauth_tokens(
            entity_id,
            user_id,
            integration_name,
        )

        if success:
            return {
                "message": f"{integration_name} disconnected successfully",
                "integration": integration_name,
                "entity_id": entity_id,
                "removed_from": "both storage types",
            }
        else:
            raise HTTPException(
                status_code=500, detail="Failed to disconnect integration"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting {integration_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/integrations/{integration_name}/status")
async def get_integration_status(
    integration_name: str,
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
):
    """
    Get status of a specific integration.

    Updated to check both user-level and tenant-level tokens.
    """
    try:
        logger.info(
            f"get_integration_status called for {integration_name}, current_user: {current_user}"
        )
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        logger.info(
            f"Checking status for entity: {entity_id}, user: {user_id}, integration: {integration_name}"
        )

        if integration_name not in ["gmail", "calendar"]:
            raise HTTPException(status_code=400, detail="Invalid integration name")

        # Get unified token service
        logger.info("Getting unified token service...")
        unified_service = await get_unified_oauth_token_service()
        logger.info("Unified token service obtained successfully")

        # Check for tokens using unified service
        logger.info(
            f"Checking for tokens for entity: {entity_id}, user: {user_id}, integration: {integration_name}"
        )
        token_data = await unified_service.get_oauth_tokens(
            entity_id, user_id, integration_name
        )
        logger.info(f"Token data retrieved: {token_data is not None}")

        if token_data:
            # Determine storage type
            tenant_service = await unified_service._get_tenant_token_store()
            tenant_tokens = await tenant_service.load_tenant_external_token(
                entity_id, integration_name
            )
            storage_type = "tenant-level" if tenant_tokens else "user-level"

            # Check token validity
            has_access_token = bool(token_data.get("access_token"))
            has_refresh_token = bool(token_data.get("refresh_token"))

            # Check expiration if available
            is_expired = False
            token_expiry = token_data.get("expires_at") or token_data.get("expires_in")
            if token_expiry:
                try:
                    if isinstance(token_expiry, str):
                        from datetime import datetime

                        expiry_dt = datetime.fromisoformat(
                            token_expiry.replace("Z", "+00:00")
                        )
                        is_expired = expiry_dt <= datetime.utcnow()
                    elif isinstance(token_expiry, (int, float)):
                        from datetime import datetime

                        expiry_dt = datetime.fromtimestamp(token_expiry)
                        is_expired = expiry_dt <= datetime.utcnow()
                except (ValueError, TypeError):
                    logger.warning(f"Invalid token expiry format: {token_expiry}")

            return {
                "integration": integration_name,
                "status": "connected",
                "storage_type": storage_type,
                "has_access_token": has_access_token,
                "has_refresh_token": has_refresh_token,
                "is_expired": is_expired,
                "token_expiry": str(token_expiry) if token_expiry else None,
                "entity_id": entity_id,
                "user_id": user_id,
            }
        else:
            return {
                "integration": integration_name,
                "status": "disconnected",
                "storage_type": None,
                "entity_id": entity_id,
                "user_id": user_id,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting integration status for {integration_name}: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/integrations/{integration_name}/migrate")
async def migrate_integration_to_tenant_level(
    integration_name: str,
    current_user: Dict[str, Any] = Depends(get_current_plexus_user),
):
    """
    Migrate user-level tokens to tenant-level storage.

    This endpoint helps with the transition from old to new architecture.
    """
    try:
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        if integration_name not in ["gmail", "calendar"]:
            raise HTTPException(status_code=400, detail="Invalid integration name")

        # Migration is no longer needed - all tokens are now stored at tenant level
        return {
            "message": f"{integration_name} is already using tenant-level storage",
            "integration": integration_name,
            "entity_id": entity_id,
            "user_id": user_id,
            "migration": "not_needed",
        }

    except Exception as e:
        logger.error(f"Error migrating {integration_name} tokens: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
