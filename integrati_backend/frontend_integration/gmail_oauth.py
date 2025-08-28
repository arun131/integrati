"""Gmail OAuth authentication for frontend integration."""

import logging
import os
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
import httpx

from mcp_plexus.plexus_auth.dependencies import get_current_plexus_user_from_token
from mcp_plexus.oauth.storage import get_tenant_external_token_store
from analytics.logger import log_integration_event
from integrations.common.watchers import WatcherKey
from integrations.gmail.watcher import GmailWatcher

logger = logging.getLogger(__name__)

router = APIRouter()

# Gmail OAuth scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def get_google_auth_flow(redirect_uri: str, scopes: list) -> Flow:
    """Create Google OAuth flow."""
    logger.info(
        f"GMAIL DEBUG: Creating OAuth flow with redirect_uri={redirect_uri}, scopes={scopes}"
    )

    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    logger.info(f"GMAIL DEBUG: Using client_id={client_id}")
    logger.info(
        f"GMAIL DEBUG: Using client_secret={'*' * len(client_secret) if client_secret else 'None'}"
    )

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }

    logger.info(f"GMAIL DEBUG: Client config created: {client_config}")

    flow = Flow.from_client_config(
        client_config, scopes=scopes, redirect_uri=redirect_uri
    )
    logger.info("GMAIL DEBUG: OAuth flow created successfully")
    return flow


@router.get("/gmail/login")
async def gmail_login(
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
):
    """
    Start the Gmail OAuth flow by redirecting to Google's authorization URL.
    """
    try:
        logger.info("=== GMAIL OAUTH DEBUG START ===")
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        logger.info(f"GMAIL DEBUG: entity_id={entity_id}, user_id={user_id}")

        # Create state parameter for security
        state = f"{entity_id}:{user_id}:gmail"
        logger.info(f"GMAIL DEBUG: state={state}")

        # Get redirect URI from environment
        redirect_uri = os.getenv(
            "GMAIL_REDIRECT_URI",
            "http://localhost:8000/api/integrations/gmail/callback",
        )
        logger.info(f"GMAIL DEBUG: redirect_uri={redirect_uri}")

        # Get client credentials
        client_id = os.getenv("GMAIL_CLIENT_ID")
        client_secret = os.getenv("GMAIL_CLIENT_SECRET")
        logger.info(f"GMAIL DEBUG: client_id={client_id}")
        logger.info(
            f"GMAIL DEBUG: client_secret={'*' * len(client_secret) if client_secret else 'None'}"
        )

        # Create OAuth flow
        logger.info("GMAIL DEBUG: Creating OAuth flow...")
        flow = get_google_auth_flow(redirect_uri, SCOPES)
        logger.info("GMAIL DEBUG: OAuth flow created successfully")

        # Generate authorization URL
        logger.info("GMAIL DEBUG: Generating authorization URL...")
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )

        logger.info(f"GMAIL DEBUG: authorization_url={authorization_url}")

        # Log the OAuth start event
        logger.info("GMAIL DEBUG: Logging OAuth start event...")
        await log_integration_event(
            entity_id=entity_id,
            user_id=user_id,
            integration_name="gmail",
            event_type="oauth_start",
            metadata={"redirect_uri": redirect_uri},
            success=True,
        )

        logger.info("GMAIL DEBUG: Returning RedirectResponse")
        logger.info("=== GMAIL OAUTH DEBUG END ===")
        return RedirectResponse(authorization_url)

    except Exception as e:
        logger.error(f"GMAIL DEBUG ERROR: {e}")
        logger.error(f"Error starting Gmail OAuth flow: {e}")
        raise HTTPException(status_code=500, detail="Failed to start Gmail OAuth flow")


async def get_user_from_state(state: str) -> Dict[str, Any]:
    """
    Extract user information from the state parameter.
    State format: {entity_id}:{user_id}:gmail
    """
    try:
        if not state:
            raise HTTPException(status_code=400, detail="State parameter not found")

        parts = state.split(":")
        if len(parts) != 3:
            raise HTTPException(
                status_code=400, detail="Invalid state parameter format"
            )

        entity_id, user_id, integration_name = parts

        if integration_name != "gmail":
            raise HTTPException(
                status_code=400, detail="Invalid integration in state parameter"
            )

        return {"entity_id": entity_id, "persistent_user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing state parameter: {e}")
        raise HTTPException(status_code=400, detail="Invalid state parameter")


@router.get("/gmail/callback")
async def gmail_callback(request: Request):
    """
    Handle the OAuth callback from Google for Gmail integration.
    """
    try:
        # Get parameters from callback
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")

        if error:
            logger.error(f"Google OAuth error: {error}")
            raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")

        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not found")

        # Extract user information from state parameter
        current_user = await get_user_from_state(state)
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        logger.info(
            f"Received Gmail OAuth callback for entity: {entity_id}, user: {user_id}"
        )

        # Exchange authorization code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        redirect_uri = os.getenv(
            "GMAIL_REDIRECT_URI",
            "http://localhost:8000/api/integrations/gmail/callback",
        )

        token_data = {
            "client_id": os.getenv("GMAIL_CLIENT_ID"),
            "client_secret": os.getenv("GMAIL_CLIENT_SECRET"),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=token_data)

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to exchange authorization code: {response.text}",
            )

        token_info = response.json()
        logger.info("Gmail token exchange successful")

        # Store tokens at tenant level
        token_store = await get_tenant_external_token_store()
        await token_store.save_tenant_external_token(entity_id, "gmail", token_info)

        # Log successful OAuth completion
        await log_integration_event(
            entity_id=entity_id,
            user_id=user_id,
            integration_name="gmail",
            event_type="oauth_complete",
            metadata={"tokens_received": bool(token_info)},
            success=True,
        )

        # Redirect back to frontend
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        redirect_url = f"{frontend_url}/dashboard?gmail_connected=true"

        logger.info(
            f"Gmail OAuth completed successfully, redirecting to: {redirect_url}"
        )

        # Ensure watcher registration (push-only) using a tenant-level identity key
        try:
            key = WatcherKey(
                provider_name="gmail", entity_id=entity_id, identity_key="tenant_base"
            )
            await GmailWatcher().ensure_registered(key)
        except Exception as e:
            logger.error(f"Failed to ensure Gmail watcher for {entity_id}: {e}")

        return RedirectResponse(redirect_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Gmail OAuth callback: {e}")

        # Log failed OAuth completion
        await log_integration_event(
            entity_id=current_user["entity_id"],
            user_id=current_user["persistent_user_id"],
            integration_name="gmail",
            event_type="oauth_complete",
            metadata={"error": str(e)},
            success=False,
            error_message=str(e),
        )

        raise HTTPException(status_code=500, detail="Internal server error")
