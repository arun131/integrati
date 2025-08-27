"""Calendar integration constants and configuration."""

import logging

logger = logging.getLogger(__name__)

# Tool names for smart categorization
CALENDAR_TOOL_NAMES = [
    "get_calendar_events",
    "create_calendar_event",
    "update_calendar_event",
    "delete_calendar_event",
    "get_calendar_event",
    "search_calendar_events",
    "get_upcoming_events",
]

# Default permission levels for background agent config
# 1 = NO_ACCESS, 2 = RESTRICTED_ACCESS, 3 = FULL_ACCESS
CALENDAR_DEFAULT_BACKGROUND_PERMISSIONS = {
    "get_calendar_events": 3,  # Full access - safe for background reading
    "create_calendar_event": 2,  # Restricted - needs approval for creating
    "update_calendar_event": 2,  # Restricted - needs approval for updating
    "delete_calendar_event": 2,  # Restricted - needs approval for deleting
    "get_calendar_event": 3,  # Full access - safe for background reading
    "search_calendar_events": 3,  # Restricted - needs approval for searching
    "get_upcoming_events": 3,  # Full access - safe for background reading
}
