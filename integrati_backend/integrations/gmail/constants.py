"""Gmail integration constants and configuration."""

import logging

logger = logging.getLogger(__name__)

# Tool names for smart categorization
GMAIL_TOOL_NAMES = [
    "search_emails",  # Merged search_emails_snapshot and search_emails_by_keywords_detailed
    "get_last_received_email_with_attachments",
    "send_gmail_message",
    "get_gmail_message",
    "reply_to_email",
    "forward_email_and_reply",
    "retrieve_specific_email_thread",
    "get_unread_email_count",
    "retrieve_emails_by_label_snapshot",
    "search_emails_by_field",
    "label_emails",
    "star_email",
    "mark_emails_as_read",
]

# Default permission levels for background agent config
# 1 = NO_ACCESS, 2 = RESTRICTED_ACCESS, 3 = FULL_ACCESS
GMAIL_DEFAULT_BACKGROUND_PERMISSIONS = {
    # READ operations - Full access (safe for background use)
    "search_emails": 3,  # Full access - safe for background agent (merged snapshot and detailed search)
    "get_last_received_email_with_attachments": 3,  # Full access - safe for background agent
    "get_gmail_message": 3,  # Full access - safe for background agent
    "retrieve_specific_email_thread": 3,  # Full access - safe for background agent
    "get_unread_email_count": 3,  # Full access - safe for background agent
    "retrieve_emails_by_label_snapshot": 3,  # Full access - safe for background agent
    "search_emails_by_field": 3,  # Full access - safe for background agent (merged sender and subject search)
    "label_emails": 3,  # Full access - safe for background agent
    "star_email": 3,  # Full access - safe for background agent
    "mark_emails_as_read": 3,  # Full access - safe for background agent
    # WRITE/MODIFY operations - Restricted access (requires approval)
    "send_gmail_message": 2,  # Restricted - needs approval for sending
    "reply_to_email": 2,  # Restricted - needs approval for replying to emails
    "forward_email_and_reply": 2,  # Restricted - needs approval for forwarding emails
}
