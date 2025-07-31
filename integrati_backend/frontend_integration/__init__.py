"""Frontend integration module."""

from .auth import router as auth_router
from .integrations import router as integrations_router
from .analytics import router as analytics_router
from .gmail_oauth import router as gmail_oauth_router
from .calendar_oauth import router as calendar_oauth_router

__all__ = [
    "auth_router",
    "integrations_router",
    "analytics_router",
    "gmail_oauth_router",
    "calendar_oauth_router",
]
