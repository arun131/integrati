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

        # Create Plexus user token
        token_manager = DefaultPlexusUserTokenManager()
        token_store = await get_sqlite_plexus_user_auth_token_store()

        # Generate token and hash
        token, token_hash = token_manager.generate_token_and_hash()

        # Save token data
        from mcp_plexus.plexus_auth.models import PlexusUserAuthTokenData
        from datetime import datetime, timezone

        token_data = PlexusUserAuthTokenData(
            entity_id=tenant.entity_id,
            persistent_user_id=firebase_uid,
            token_hash=token_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
            last_used_at=datetime.now(timezone.utc).isoformat(),
        )
        await token_store.save_token_data(token_data)

        # Log analytics (optional - don't fail the request if this fails)
        try:
            await log_auth_event(
                entity_id=tenant.entity_id,
                user_id=firebase_uid,
                event_type="firebase_login",
                metadata={"email": email, "firebase_uid": firebase_uid},
                success=True,
            )
        except Exception as analytics_error:
            logger.warning(f"Failed to log analytics event: {analytics_error}")
            # Don't let analytics failure break the auth flow

        response_data = {
            "plexus_token": token,
            "entity_id": tenant.entity_id,
            "user_id": firebase_uid,
            "email": email,
            "tenant_name": tenant.tenant_name,
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
        return {
            "entity_id": current_user["entity_id"],
            "user_id": current_user["persistent_user_id"],
            "authenticated": True,
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
