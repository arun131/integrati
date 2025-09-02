"""Common tools integration constants and configuration."""

import logging

logger = logging.getLogger(__name__)

# Tool names for smart categorization
COMMON_TOOL_NAMES = [
    "web_search",
    "local_search",
]

# Default permission levels for background agent config
# 1 = NO_ACCESS, 2 = RESTRICTED_ACCESS, 3 = FULL_ACCESS
COMMON_DEFAULT_BACKGROUND_PERMISSIONS = {
    "web_search": 3,  # Full access - read-only search operations
    "local_search": 3,  # Full access - read-only search operations
}
