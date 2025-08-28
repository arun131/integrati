# mcp_plexus/oauth/__init__.py
# OAuth 2.1 Provider Package for MCP Plexus

# Import storage interfaces and implementations
from .storage_interfaces import (
    AbstractAuthCodeStore,
    AbstractOAuthTokenStore,
    AbstractExternalOAuthProviderConfigStore,
    AbstractOAuthClientStore,
)

# Import storage implementations
from .storage import (
    get_internal_oauth_token_store,
    get_internal_auth_code_store,
    get_external_oauth_provider_config_store,
    get_internal_oauth_client_store,
)

# Import OAuth models
from .models import (
    AuthCodeData,
    AccessTokenData,
    RefreshTokenData,
    OAuthProviderSettings,
    OAuthClient,
)

# Import OAuth errors
from .errors import (
    OAuthError,
    InvalidRequestError,
    InvalidClientError,
    InvalidGrantError,
    UnauthorizedClientError,
    UnsupportedGrantTypeError,
    InvalidScopeError,
    InvalidTokenError,
    InsufficientScopeError,
    ServerError,
    TemporarilyUnavailableError,
    PlexusExternalAuthRequiredError,
    PlexusApiKeyRequiredError,
)

# Import OAuth provider
from .provider import OAuthProvider

__all__ = [
    # Storage interfaces
    "AbstractAuthCodeStore",
    "AbstractOAuthTokenStore",
    "AbstractExternalOAuthProviderConfigStore",
    "AbstractOAuthClientStore",
    # Storage functions
    "get_internal_oauth_token_store",
    "get_internal_auth_code_store",
    "get_external_oauth_provider_config_store",
    "get_internal_oauth_client_store",
    # Models
    "AuthCodeData",
    "AccessTokenData",
    "RefreshTokenData",
    "OAuthProviderSettings",
    "OAuthClient",
    # Errors
    "OAuthError",
    "InvalidRequestError",
    "InvalidClientError",
    "InvalidGrantError",
    "UnauthorizedClientError",
    "UnsupportedGrantTypeError",
    "InvalidScopeError",
    "InvalidTokenError",
    "InsufficientScopeError",
    "ServerError",
    "TemporarilyUnavailableError",
    "PlexusExternalAuthRequiredError",
    "PlexusApiKeyRequiredError",
    # Provider
    "OAuthProvider",
]
