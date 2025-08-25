"""Firebase authentication integration for frontend."""

import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends
import firebase_admin
from firebase_admin import auth as firebase_auth

from mcp_plexus.plexus_auth.dependencies import get_current_plexus_user
from mcp_plexus.plexus_auth.token_manager import DefaultPlexusUserTokenManager
from mcp_plexus.plexus_auth.sqlite_user_auth_token_store import (
    get_sqlite_plexus_user_auth_token_store,
)
from mcp_plexus.tenants.service import TenantService
from mcp_plexus.tenants.models import TenantCreate
from analytics.logger import log_auth_event

logger = logging.getLogger(__name__)

# Ensure Firebase Admin SDK initialized once using service account JSON or environment variables
if not firebase_admin._apps:
    import os
    import json

    service_account_path = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-service-account.json"
    )
    if os.path.exists(service_account_path):
        cred = firebase_admin.credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        logger.info("Initialized Firebase Admin using service account file.")
    elif os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"):
        service_account_info = json.loads(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"))
        cred = firebase_admin.credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
        logger.info("Initialized Firebase Admin using JSON from env var.")
    else:
        # Fallback to default credentials (e.g. GOOGLE_APPLICATION_CREDENTIALS)
        firebase_admin.initialize_app()
        logger.warning("Initialized Firebase Admin with default credentials.")

router = APIRouter()


@router.post("/auth/firebase-token")
async def create_plexus_token_from_firebase(request: Request):
    """Exchange Firebase ID token for Plexus token."""
    try:
        body = await request.json()
        logger.info(f"Received Firebase token exchange request: {body}")
        id_token = body.get("id_token")

        if not id_token:
            logger.error(f"Missing id_token in request body: {body}")
            raise HTTPException(status_code=400, detail="id_token required")

        # Verify Firebase token
        decoded_token = firebase_auth.verify_id_token(id_token)
        firebase_uid = decoded_token["uid"]
        email = decoded_token.get("email")

        if not email:
            raise HTTPException(status_code=400, detail="No email in Firebase token")

        # Create or get tenant and user
        from mcp_plexus.tenants.sqlite_tenant_store import get_sqlite_tenant_store

        tenant_store = await get_sqlite_tenant_store()
        tenant_service = TenantService(tenant_store)

        # Try to get existing tenant by email
        tenant = await tenant_service.get_tenant_by_email(email)

        if not tenant:
            # Create new tenant with username derived from email
            username = email.split("@")[0]  # Use email prefix as username
            tenant_data = TenantCreate(
                entity_id=username, tenant_name=username, status="active"
            )
            tenant = await tenant_service.create_tenant(tenant_data)

        # Create robust token management with base and background configs
        token_manager = DefaultPlexusUserTokenManager()
        token_store = await get_sqlite_plexus_user_auth_token_store()

        from mcp_plexus.plexus_auth.models import PlexusUserAuthTokenData
        from datetime import datetime, timezone

        # Strategy: Always generate fresh tokens for security, but use proper config management
        # Check if base config token already exists
        existing_base_token = await token_store.get_token_data_by_user_id(
            tenant.entity_id, "base"
        )

        if existing_base_token:
            # Generate new token but keep the same config association
            base_token, base_token_hash = token_manager.generate_token_and_hash()
            existing_base_token.token_hash = base_token_hash
            existing_base_token.last_used_at = datetime.now(timezone.utc).isoformat()
            await token_store.save_token_data(existing_base_token)  # This will upsert
            logger.info(
                f"Refreshed base config token for returning user {tenant.entity_id}"
            )
        else:
            # Create new base config token for new user
            base_token, base_token_hash = token_manager.generate_token_and_hash()
            base_token_data = PlexusUserAuthTokenData(
                entity_id=tenant.entity_id,
                persistent_user_id="base",  # Config ID stored as persistent_user_id
                token_hash=base_token_hash,
                created_at=datetime.now(timezone.utc).isoformat(),
                last_used_at=datetime.now(timezone.utc).isoformat(),
            )
            await token_store.save_token_data(base_token_data)
            logger.info(f"Created new base config token for {tenant.entity_id}")

        # Check if background agent config token already exists
        existing_bg_token = await token_store.get_token_data_by_user_id(
            tenant.entity_id, "background_agent"
        )

        if not existing_bg_token:
            # Create background agent config token for new user
            bg_token, bg_token_hash = token_manager.generate_token_and_hash()
            bg_token_data = PlexusUserAuthTokenData(
                entity_id=tenant.entity_id,
                persistent_user_id="background_agent",  # Config ID stored as persistent_user_id
                token_hash=bg_token_hash,
                created_at=datetime.now(timezone.utc).isoformat(),
                last_used_at=datetime.now(timezone.utc).isoformat(),
            )
            await token_store.save_token_data(bg_token_data)
            logger.info(
                f"Created new background_agent config token for {tenant.entity_id}"
            )

        # Create tenant configs in database
        from mcp_plexus.tenants.sqlite_tenant_config_store import (
            get_sqlite_tenant_config_store,
        )
        from mcp_plexus.tenants.models import TenantConfigCreate

        config_store = await get_sqlite_tenant_config_store()

        # Create base config if doesn't exist
        base_config = await config_store.get_config_by_id(tenant.entity_id, "base")
        if not base_config:
            base_config_data = TenantConfigCreate(
                entity_id=tenant.entity_id,
                config_id="base",
                config_name="Base Config",
                config_type="profile",
                is_default=True,
                settings_json={
                    "tool_permissions": {}
                },  # Empty = full access to all tools
            )
            await config_store.create_config(base_config_data)
            logger.info(f"Created base config for {tenant.entity_id}")

        # Create background agent config if doesn't exist
        bg_config = await config_store.get_config_by_id(
            tenant.entity_id, "background_agent"
        )
        if not bg_config:
            # Import default permissions from integration tools
            default_permissions = {}
            try:
                from integrations.common.constants import (
                    COMMON_DEFAULT_BACKGROUND_PERMISSIONS,
                )
                from integrations.gmail.constants import (
                    GMAIL_DEFAULT_BACKGROUND_PERMISSIONS,
                )
                from integrations.calendar.constants import (
                    CALENDAR_DEFAULT_BACKGROUND_PERMISSIONS,
                )

                default_permissions.update(COMMON_DEFAULT_BACKGROUND_PERMISSIONS)
                default_permissions.update(GMAIL_DEFAULT_BACKGROUND_PERMISSIONS)
                default_permissions.update(CALENDAR_DEFAULT_BACKGROUND_PERMISSIONS)
            except ImportError:
                logger.warning("Could not import default background permissions")

            bg_config_data = TenantConfigCreate(
                entity_id=tenant.entity_id,
                config_id="background_agent",
                config_name="Background Agent Config",
                config_type="profile",
                is_default=False,
                settings_json={"tool_permissions": default_permissions},
            )
            await config_store.create_config(bg_config_data)
            logger.info(f"Created background_agent config for {tenant.entity_id}")

        # Log analytics (optional - don't fail the request if this fails)
        try:
            await log_auth_event(
                entity_id=tenant.entity_id,
                user_id="base",  # Use config_id as user_id for analytics
                event_type="firebase_login",
                metadata={"email": email, "firebase_uid": firebase_uid},
                success=True,
            )
        except Exception as analytics_error:
            logger.warning(f"Failed to log analytics event: {analytics_error}")
            # Don't let analytics failure break the auth flow

        response_data = {
            "plexus_token": base_token,  # Return the base config token
            "entity_id": tenant.entity_id,
            "user_id": "base",  # Return config_id as user_id
            "email": email,
            "tenant_name": tenant.tenant_name,
            "config_id": "base",  # Explicitly include config info
        }
        logger.info(f"Returning successful response: {response_data}")
        return response_data

    except firebase_auth.InvalidIdTokenError:
        try:
            await log_auth_event(
                entity_id="unknown",
                user_id="unknown",
                event_type="firebase_login",
                metadata={"error": "Invalid Firebase ID token"},
                success=False,
                error_message="Invalid Firebase ID token",
            )
        except Exception as analytics_error:
            logger.warning(f"Failed to log analytics event: {analytics_error}")
        raise HTTPException(status_code=401, detail="Invalid Firebase ID token")
    except Exception as e:
        logger.error(f"Error in Firebase token exchange: {e}", exc_info=True)
        try:
            await log_auth_event(
                entity_id="unknown",
                user_id="unknown",
                event_type="firebase_login",
                metadata={"error": str(e)},
                success=False,
                error_message=str(e),
            )
        except Exception as analytics_error:
            logger.warning(f"Failed to log analytics event: {analytics_error}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/auth/me")
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_plexus_user),
):
    """Get current user information."""
    try:
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        # Get unread notification count
        unread_notifications = 0
        try:
            from analytics.database import AnalyticsDatabase

            db = AnalyticsDatabase()
            unread_notifications = await db.get_unread_notification_count(
                entity_id, user_id
            )
        except Exception as notification_error:
            logger.warning(f"Failed to get notification count: {notification_error}")
            # Don't fail the request if notifications can't be retrieved

        return {
            "entity_id": entity_id,
            "user_id": user_id,
            "authenticated": True,
            "unread_notifications": unread_notifications,
        }
    except Exception as e:
        logger.error(f"Error getting current user info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/auth/logout")
async def logout_user(current_user: Dict[str, Any] = Depends(get_current_plexus_user)):
    """Logout user and invalidate token."""
    try:
        # Log the logout event
        await log_auth_event(
            entity_id=current_user["entity_id"],
            user_id=current_user["persistent_user_id"],
            event_type="logout",
            metadata={"logout_method": "api_call"},
            success=True,
        )

        return {
            "message": "Logout successful",
            "entity_id": current_user["entity_id"],
            "user_id": current_user["persistent_user_id"],
        }
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
