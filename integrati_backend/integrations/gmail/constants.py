"""Gmail integration constants and configuration."""

import logging

logger = logging.getLogger(__name__)

# Tool names for smart categorization
GMAIL_TOOL_NAMES = [
    "search_gmail_messages",
    "get_last_received_email",
    "send_gmail_message",
    "get_gmail_message",
    "get_unread_email_count",
    "search_gmail_by_sender",
    "search_gmail_by_subject",
]

# Default permission levels for background agent config
# 1 = NO_ACCESS, 2 = RESTRICTED_ACCESS, 3 = FULL_ACCESS
GMAIL_DEFAULT_BACKGROUND_PERMISSIONS = {
    "search_gmail_messages": 3,  # Full access - safe for background reading
    "get_last_received_email": 3,  # Full access - safe for background reading
    "send_gmail_message": 2,  # Restricted - needs approval for sending
    "get_gmail_message": 3,  # Full access - safe for background reading
    "get_unread_email_count": 3,  # Full access - safe for background reading
    "search_gmail_by_sender": 3,  # Full access - safe for background reading
    "search_gmail_by_subject": 3,  # Full access - safe for background reading
}
