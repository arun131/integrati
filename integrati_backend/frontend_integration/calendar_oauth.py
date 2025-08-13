"""Calendar OAuth authentication for frontend integration."""

import logging
import os
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
import requests

from mcp_plexus.plexus_auth.dependencies import get_current_plexus_user_from_token
from mcp_plexus.oauth.storage import get_tenant_external_token_store
from analytics.logger import log_integration_event

logger = logging.getLogger(__name__)

router = APIRouter()

# Calendar OAuth scopes
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def get_google_auth_flow(redirect_uri: str, scopes: list) -> Flow:
    """Create Google OAuth flow."""
    logger.info(
        f"CALENDAR DEBUG: Creating OAuth flow with redirect_uri={redirect_uri}, scopes={scopes}"
    )

    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    logger.info(f"CALENDAR DEBUG: Using client_id={client_id}")
    logger.info(
        f"CALENDAR DEBUG: Using client_secret={'*' * len(client_secret) if client_secret else 'None'}"
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

    logger.info(f"CALENDAR DEBUG: Client config created: {client_config}")

    flow = Flow.from_client_config(
        client_config, scopes=scopes, redirect_uri=redirect_uri
    )
    logger.info("CALENDAR DEBUG: OAuth flow created successfully")
    return flow


@router.get("/calendar/login")
async def calendar_login(
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
):
    """
    Start the Calendar OAuth flow by redirecting to Google's authorization URL.
    """
    try:
        logger.info("=== CALENDAR OAUTH DEBUG START ===")
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        logger.info(f"CALENDAR DEBUG: entity_id={entity_id}, user_id={user_id}")

        # Create state parameter for security
        state = f"{entity_id}:{user_id}:calendar"
        logger.info(f"CALENDAR DEBUG: state={state}")

        # Get redirect URI from environment
        redirect_uri = os.getenv(
            "CALENDAR_REDIRECT_URI",
            "http://localhost:8000/api/integrations/calendar/callback",
        )
        logger.info(f"CALENDAR DEBUG: redirect_uri={redirect_uri}")

        # Get client credentials
        client_id = os.getenv("GMAIL_CLIENT_ID")
        client_secret = os.getenv("GMAIL_CLIENT_SECRET")
        logger.info(f"CALENDAR DEBUG: client_id={client_id}")
        logger.info(
            f"CALENDAR DEBUG: client_secret={'*' * len(client_secret) if client_secret else 'None'}"
        )

        # Create OAuth flow
        logger.info("CALENDAR DEBUG: Creating OAuth flow...")
        flow = get_google_auth_flow(redirect_uri, SCOPES)
        logger.info("CALENDAR DEBUG: OAuth flow created successfully")

        # Generate authorization URL
        logger.info("CALENDAR DEBUG: Generating authorization URL...")
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )

        logger.info(f"CALENDAR DEBUG: authorization_url={authorization_url}")

        # Log the OAuth start event
        logger.info("CALENDAR DEBUG: Logging OAuth start event...")
        await log_integration_event(
            entity_id=entity_id,
            user_id=user_id,
            integration_name="calendar",
            event_type="oauth_start",
            metadata={"redirect_uri": redirect_uri},
            success=True,
        )

        logger.info("CALENDAR DEBUG: Returning RedirectResponse")
        logger.info("=== CALENDAR OAUTH DEBUG END ===")
        return RedirectResponse(authorization_url)

    except Exception as e:
        logger.error(f"CALENDAR DEBUG ERROR: {e}")
        logger.error(f"Error starting Calendar OAuth flow: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to start Calendar OAuth flow"
        )


async def get_user_from_state(state: str) -> Dict[str, Any]:
    """
    Extract user information from the state parameter.
    State format: {entity_id}:{user_id}:calendar
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

        if integration_name != "calendar":
            raise HTTPException(
                status_code=400, detail="Invalid integration in state parameter"
            )

        return {"entity_id": entity_id, "persistent_user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing state parameter: {e}")
        raise HTTPException(status_code=400, detail="Invalid state parameter")


@router.get("/calendar/callback")
async def calendar_callback(request: Request):
    """
    Handle the OAuth callback from Google for Calendar integration.
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
            f"Received Calendar OAuth callback for entity: {entity_id}, user: {user_id}"
        )

        # Exchange authorization code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        redirect_uri = os.getenv(
            "CALENDAR_REDIRECT_URI",
            "http://localhost:8000/api/integrations/calendar/callback",
        )

        token_data = {
            "client_id": os.getenv("GMAIL_CLIENT_ID"),
            "client_secret": os.getenv("GMAIL_CLIENT_SECRET"),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        response = requests.post(token_url, data=token_data)

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to exchange authorization code: {response.text}",
            )

        token_info = response.json()
        logger.info("Calendar token exchange successful")

        # Store tokens at tenant level
        token_store = await get_tenant_external_token_store()
        await token_store.save_tenant_external_token(entity_id, "calendar", token_info)

        logger.info(f"Calendar tokens stored for tenant: {entity_id}")

        # Log the successful OAuth completion
        await log_integration_event(
            entity_id=entity_id,
            user_id=user_id,
            integration_name="calendar",
            event_type="oauth_complete",
            metadata={"tokens_received": bool(token_info)},
            success=True,
        )

        # Redirect back to frontend
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        redirect_url = f"{frontend_url}/dashboard?calendar_connected=true"

        logger.info(
            f"Calendar OAuth completed successfully, redirecting to: {redirect_url}"
        )

        return RedirectResponse(redirect_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Calendar OAuth callback: {e}")

        # Log the failed OAuth completion
        try:
            current_user = await get_user_from_state(state)
            await log_integration_event(
                entity_id=current_user["entity_id"],
                user_id=current_user["persistent_user_id"],
                integration_name="calendar",
                event_type="oauth_complete",
                metadata={"error": str(e)},
                success=False,
                error_message=str(e),
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=500, detail="Failed to complete Calendar OAuth flow"
        )
