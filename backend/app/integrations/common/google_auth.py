import os

from google_auth_oauthlib.flow import Flow

from app.core.config import settings


def get_google_auth_flow(redirect_uri=None, scopes=None):
    """
    Create a Google OAuth flow with the specified redirect URI and scopes.

    Args:
        redirect_uri: The redirect URI for the OAuth flow. If None, uses the default from settings.
        scopes: List of OAuth scopes to request. If None, uses empty list.

    Returns:
        Flow: A configured Google OAuth flow
    """
    if scopes is None:
        scopes = []

    # Use the provided redirect_uri or fall back to settings
    final_redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uris": [final_redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=scopes,
    )

    # Set the redirect URI explicitly on the flow
    flow.redirect_uri = final_redirect_uri

    return flow
