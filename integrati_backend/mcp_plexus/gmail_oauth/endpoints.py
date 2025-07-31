# mcp_plexus/gmail_oauth/endpoints.py
import logging
import requests
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, status, Depends, Header
from fastapi.responses import RedirectResponse, HTMLResponse
from typing import Annotated, Optional, Dict, Any
from google.oauth2.credentials import Credentials

from ..plexus_auth.dependencies import get_plexus_user_auth_token_store_dependency, get_plexus_user_token_manager_dependency
from ..plexus_auth.storage_interfaces import AbstractPlexusUserAuthTokenStore
from ..plexus_auth.token_manager import PlexusUserTokenManagerProtocol
from ..oauth.storage import get_user_external_token_store, get_tenant_external_token_store
from ..oauth.storage_interfaces import AbstractUserExternalTokenStore, AbstractTenantExternalTokenStore
from ..dependencies import get_tenant_external_token_store_dependency
from ..settings import settings

logger = logging.getLogger(__name__)

gmail_oauth_router = APIRouter(prefix="/gmail", tags=["Gmail OAuth"])

# Gmail OAuth scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

def get_google_auth_url(redirect_uri: str, state: str = None) -> str:
    """Generate Google OAuth authorization URL."""
    base_url = "https://accounts.google.com/o/oauth2/auth"
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(GMAIL_SCOPES),
        "response_type": "code",
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent"
    }
    if state:
        params["state"] = state
    
    param_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{param_string}"


async def get_current_plexus_user_from_token(
    token_store: Annotated[AbstractPlexusUserAuthTokenStore, Depends(get_plexus_user_auth_token_store_dependency)],
    token_manager: Annotated[PlexusUserTokenManagerProtocol, Depends(get_plexus_user_token_manager_dependency)],
    authorization: Annotated[Optional[str], Header()] = None 
) -> Dict[str, Any]:
    """
    Authenticates and validates a Plexus user based on their Bearer token.
    This version doesn't require entity_id in the URL path.
    """
    token: Optional[str] = None
    auth_method_used: Optional[str] = None

    # Extract Bearer token from Authorization header
    if authorization:
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() == "bearer":
            token = credentials
            auth_method_used = "Header (Bearer)"
    
    if not token:
        logger.warning("Plexus User Auth: No token provided via Bearer header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated: Missing or invalid Plexus User Auth Token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Hash the token and verify it exists
    token_hash = token_manager.hash_token(token)
    token_data = await token_store.get_token_data_by_hash(token_hash)

    if not token_data:
        logger.warning("Plexus User Auth: Invalid or expired token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Plexus User Auth Token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update token last used timestamp for tracking purposes
    await token_store.update_token_last_used(token_hash)
    logger.info(f"Plexus User Auth: Successful for E:{token_data.entity_id}, User:{token_data.persistent_user_id} via {auth_method_used}.")
    
    return {"entity_id": token_data.entity_id, "persistent_user_id": token_data.persistent_user_id}


@gmail_oauth_router.get("/login")
async def gmail_login(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_plexus_user_from_token)]
):
    """
    Start the Gmail OAuth flow by redirecting to Google's authorization URL.
    Requires valid Plexus user authentication.
    
    NEW ARCHITECTURE: OAuth tokens are stored at tenant level, not user level.
    State parameter now only contains entity_id.
    """
    try:
        entity_id = current_user["entity_id"]
        
        # NEW: Create state parameter with only entity_id (not user_id)
        # OAuth tokens will be shared across all configs within the tenant
        state = entity_id
        
        # Use a single redirect URI for all tenants
        redirect_uri = f"{request.base_url}gmail/callback"
        
        # Generate Google OAuth URL
        auth_url = get_google_auth_url(redirect_uri, state)
        
        logger.info(f"Starting Gmail OAuth flow for tenant {entity_id} (tenant-level OAuth)")
        return RedirectResponse(auth_url)
        
    except Exception as e:
        logger.error(f"Error starting Gmail OAuth flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start Gmail OAuth flow"
        )


@gmail_oauth_router.get("/callback")
async def gmail_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    tenant_token_store: Annotated[AbstractTenantExternalTokenStore, Depends(get_tenant_external_token_store_dependency)] = None
):
    """
    Handle the OAuth callback from Google for Gmail integration.
    
    NEW ARCHITECTURE: Stores tokens at tenant level for use across all configs.
    State parameter now only contains entity_id.
    """
    if error:
        logger.error(f"Google OAuth error: {error}")
        return HTMLResponse(
            f"<h1>OAuth Error</h1><p>Error: {error}</p>",
            status_code=400
        )
    
    if not code:
        logger.error("No authorization code received")
        return HTMLResponse(
            "<h1>Error</h1><p>Authorization code not found</p>",
            status_code=400
        )
    
    if not state:
        logger.error("No state parameter received")
        return HTMLResponse(
            "<h1>Error</h1><p>State parameter missing</p>",
            status_code=400
        )
    
    try:
        # NEW: Parse state to get only entity_id (no user_id anymore)
        entity_id = state.strip()
        
        logger.info(f"Processing Gmail OAuth callback for tenant {entity_id} (tenant-level OAuth)")
        
        # Exchange authorization code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        redirect_uri = f"{request.base_url}gmail/callback"
        
        token_data = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        
        response = requests.post(token_url, data=token_data)
        
        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            return HTMLResponse(
                f"<h1>Error</h1><p>Failed to exchange authorization code: {response.text}</p>",
                status_code=400
            )
        
        token_info = response.json()
        logger.info("Token exchange successful")
        
        # Calculate token expiry
        token_expiry = None
        if token_info.get("expires_in"):
            token_expiry = datetime.utcnow() + timedelta(seconds=token_info.get("expires_in"))
        
        # NEW: Store tokens at tenant level using new tenant token store
        token_data_to_store = {
            "access_token": token_info.get("access_token"),
            "refresh_token": token_info.get("refresh_token"),
            "token_type": token_info.get("token_type", "Bearer"),
            "expires_at": token_expiry.isoformat() if token_expiry else None,
            "scope": token_info.get("scope"),
        }
        
        await tenant_token_store.save_tenant_external_token(
            entity_id=entity_id,
            provider_name="gmail",
            token_data=token_data_to_store
        )
        
        logger.info(f"Tenant Gmail OAuth tokens stored successfully for E:{entity_id}")
        
        # TODO: Register Gmail tools for the tenant (will be shared across all configs)
        
        return HTMLResponse("""
            <h1>Gmail Authorization Successful!</h1>
            <p>Gmail has been successfully connected to your tenant.</p>
            <p>All configs within your tenant can now use Gmail tools.</p>
            <script>
                setTimeout(() => window.close(), 3000);
            </script>
        """)
        
    except Exception as e:
        logger.error(f"Error processing Gmail OAuth callback: {e}", exc_info=True)
        return HTMLResponse(
            f"<h1>Error</h1><p>Failed to process authorization: {str(e)}</p>",
            status_code=500
        )


@gmail_oauth_router.get("/status")
async def gmail_status(
    current_user: Annotated[dict, Depends(get_current_plexus_user_from_token)],
    tenant_token_store: Annotated[AbstractTenantExternalTokenStore, Depends(get_tenant_external_token_store_dependency)]
):
    """
    Check Gmail OAuth status for the current tenant.
    
    NEW ARCHITECTURE: Checks tenant-level OAuth tokens.
    """
    try:
        entity_id = current_user["entity_id"]
        
        # NEW: Load tenant-level tokens instead of user-level tokens
        token_data = await tenant_token_store.load_tenant_external_token(
            entity_id=entity_id,
            provider_name="gmail"
        )
        
        if token_data:
            has_access_token = bool(token_data.get("access_token"))
            has_refresh_token = bool(token_data.get("refresh_token"))
            token_expiry = token_data.get("expires_at")
            
            # Check if token is expired
            is_expired = False
            if token_expiry:
                try:
                    expiry_dt = datetime.fromisoformat(token_expiry)
                    is_expired = expiry_dt <= datetime.utcnow()
                except ValueError:
                    logger.warning(f"Invalid token expiry format: {token_expiry}")
            
            return {
                "connected": True,
                "has_access_token": has_access_token,
                "has_refresh_token": has_refresh_token,
                "is_expired": is_expired,
                "token_expiry": token_expiry,
                "scope": token_data.get("scope"),
                "message": "Gmail is connected at tenant level - shared across all configs"
            }
        else:
            return {
                "connected": False,
                "message": "Gmail not connected for this tenant"
            }
            
    except Exception as e:
        logger.error(f"Error checking Gmail status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check Gmail status"
        ) 