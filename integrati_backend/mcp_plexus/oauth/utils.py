"""
OAuth utility functions for token management and validation.
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


def is_token_expired(token_data: Dict[str, Any]) -> bool:
    """
    Check if an OAuth token is expired.

    Args:
        token_data: Token data dictionary containing expiry information

    Returns:
        True if token is expired, False otherwise
    """
    if not token_data:
        return True

    # Check expires_at field (ISO format)
    expires_at = token_data.get("expires_at")
    if expires_at:
        try:
            if isinstance(expires_at, str):
                expiry_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            else:
                expiry_dt = expires_at

            # Add 5 minute buffer to prevent edge cases
            buffer_time = datetime.now(timezone.utc) + timedelta(minutes=5)
            return expiry_dt <= buffer_time
        except Exception as e:
            logger.warning(f"Error parsing token expiry: {e}")
            return True

    # Check expires_in field (seconds from now)
    expires_in = token_data.get("expires_in")
    if expires_in:
        try:
            # If expires_in is a timestamp, convert to datetime
            if (
                isinstance(expires_in, (int, float)) and expires_in > 1000000000
            ):  # Likely a timestamp
                expiry_dt = datetime.fromtimestamp(expires_in, tz=timezone.utc)
                buffer_time = datetime.now(timezone.utc) + timedelta(minutes=5)
                return expiry_dt <= buffer_time
        except Exception as e:
            logger.warning(f"Error parsing expires_in: {e}")
            return True

    # If we can't determine expiry, assume it's expired
    return True


def validate_token_data(token_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean up token data.

    Args:
        token_data: Raw token data from OAuth provider

    Returns:
        Cleaned and validated token data
    """
    if not token_data:
        return {}

    # Ensure required fields exist
    required_fields = ["access_token"]
    for field in required_fields:
        if not token_data.get(field):
            logger.warning(f"Missing required token field: {field}")
            return {}

    # Clean up the token data
    cleaned_data = {}

    # Copy essential fields
    for key in ["access_token", "refresh_token", "token_type", "scope"]:
        if key in token_data:
            cleaned_data[key] = token_data[key]

    # Handle expiry information
    if "expires_in" in token_data:
        try:
            expires_in = int(token_data["expires_in"])
            # Calculate expiry time from now
            expiry_dt = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            cleaned_data["expires_at"] = expiry_dt.isoformat()
        except (ValueError, TypeError):
            logger.warning(f"Invalid expires_in value: {token_data['expires_in']}")

    elif "expires_at" in token_data:
        # Keep expires_at if it's already in ISO format
        cleaned_data["expires_at"] = token_data["expires_at"]

    # Add metadata
    cleaned_data["obtained_at"] = datetime.now(timezone.utc).isoformat()

    return cleaned_data


def should_refresh_token(token_data: Dict[str, Any]) -> bool:
    """
    Determine if a token should be refreshed.

    Args:
        token_data: Token data dictionary

    Returns:
        True if token should be refreshed, False otherwise
    """
    if not token_data:
        return True

    # Check if token is expired
    if is_token_expired(token_data):
        return True

    # Check if we have a refresh token
    if not token_data.get("refresh_token"):
        return False

    # Check if token expires soon (within 1 hour)
    expires_at = token_data.get("expires_at")
    if expires_at:
        try:
            if isinstance(expires_at, str):
                expiry_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            else:
                expiry_dt = expires_at

            # Refresh if token expires within 1 hour
            refresh_threshold = datetime.now(timezone.utc) + timedelta(hours=1)
            return expiry_dt <= refresh_threshold
        except Exception as e:
            logger.warning(f"Error checking refresh threshold: {e}")
            return False

    return False


def log_token_status(
    entity_id: str, user_id: str, provider: str, token_data: Dict[str, Any]
) -> None:
    """
    Log token status for debugging purposes.

    Args:
        entity_id: The tenant entity ID
        user_id: The user/config ID
        provider: OAuth provider name
        token_data: Token data to analyze
    """
    if not token_data:
        logger.info(f"OAuth {provider}: No tokens for E:{entity_id} U:{user_id}")
        return

    has_access = bool(token_data.get("access_token"))
    has_refresh = bool(token_data.get("refresh_token"))
    is_expired = is_token_expired(token_data)
    should_refresh = should_refresh_token(token_data)

    status = "VALID"
    if is_expired:
        status = "EXPIRED"
    elif should_refresh:
        status = "NEEDS_REFRESH"

    logger.info(
        f"OAuth {provider} status for E:{entity_id} U:{user_id}: {status} "
        f"(access: {has_access}, refresh: {has_refresh}, expired: {is_expired}, should_refresh: {should_refresh})"
    )
