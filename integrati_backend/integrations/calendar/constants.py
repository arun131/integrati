"""Calendar integration constants and configuration."""

import logging

logger = logging.getLogger(__name__)

# Tool names for smart categorization
CALENDAR_TOOL_NAMES = [
    # Unified event management tools
    "get_events",  # Merged get_calendar_events, search_calendar_events, get_upcoming_events, get_calendar_event
    "create_event",  # Renamed from create_calendar_event
    "update_event",  # Merged update_calendar_event and add_attendees_to_event
    "delete_event",  # Renamed from delete_calendar_event
    # Calendar management tools
    "list_calendars",
    "create_calendar",
    # Advanced features
    "quick_add_event_from_text",
    "check_attendee_status",
    "query_free_busy",
    "schedule_mutual",
    "analyze_busyness",
]

# Default permission levels for background agent config
# 1 = NO_ACCESS, 2 = RESTRICTED_ACCESS, 3 = FULL_ACCESS
CALENDAR_DEFAULT_BACKGROUND_PERMISSIONS = {
    # READ operations - Full access (safe for background use)
    "get_events": 3,  # Full access - safe for background reading (merged multiple functions)
    "list_calendars": 3,  # Full access - safe for background reading
    "check_attendee_status": 3,  # Full access - safe for background reading
    "query_free_busy": 3,  # Full access - safe for background reading
    "analyze_busyness": 3,  # Full access - safe for background reading
    "create_calendar": 3,  # Full access - safe for background reading
    # WRITE/CREATE/MODIFY operations - Restricted access (requires approval)
    "create_event": 2,  # Restricted - needs approval for creating events
    "update_event": 2,  # Restricted - needs approval for updating events
    "delete_event": 2,  # Restricted - needs approval for deleting events
    "quick_add_event_from_text": 2,  # Restricted - needs approval for creating events
    "schedule_mutual": 2,  # Restricted - needs approval for creating meetings
}
