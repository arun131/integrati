# test_gmail_api.py
import asyncio
import sys
import os
import sqlite3
import random
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add your project path to Python path
sys.path.append("/home/arunraj/development/integrati/integrati")

from integrati_backend.integrations.gmail.api import GmailAPI

# ============================================================================
# NEW GMAIL WRAPPER FUNCTIONS
# ============================================================================


def _normalize_keywords(keywords: Optional[List[str]]) -> List[str]:
    """Normalize keywords list by trimming whitespace and dropping empties."""
    if not keywords:
        return []
    normalized = []
    for term in keywords:
        if not term:
            continue
        t = str(term).strip()
        if t:
            normalized.append(t)
    return normalized


def _quote_if_needed(term: str) -> str:
    """Quote the term if it contains whitespace."""
    return f'"{term}"' if any(c.isspace() for c in term) else term


def _build_gmail_query_from_keywords(
    keywords: Optional[List[str]],
    email_addresses: Optional[List[str]] = None,
    timerange_days: Optional[int] = None,
) -> str:
    """Build a Gmail query that searches subject, body, from, to, cc for any keywords.

    - Tokens that look like operators (contain ':') are passed through as-is.
    - Plain tokens are expanded across subject/body/from/to/cc using OR groups.
    - Email addresses are added as from:address filters.
    - Date filter uses newer_than:Nd when provided.
    """
    parts: List[str] = []

    # Keyword expansion
    for raw in _normalize_keywords(keywords):
        # Treat operator-like tokens as-is (e.g., has:attachment, from:google)
        if ":" in raw and not any(ch.isspace() for ch in raw):
            parts.append(raw)
            continue

        term = _quote_if_needed(raw)
        group = [
            f"subject:{term}",
            term,  # bare term -> subject/body
            f"from:{term}",
            f"to:{term}",
            f"cc:{term}",
        ]
        parts.append("(" + " OR ".join(group) + ")")

    # Email address filters
    if email_addresses:
        for addr in email_addresses:
            a = str(addr).strip()
            if a:
                parts.append(f"from:{a}")

    # Date range
    if timerange_days and timerange_days > 0:
        parts.append(f"newer_than:{timerange_days}d")

    return " ".join(parts).strip()


def _extract_relevant_section(
    subject: str, body: str, keywords: List[str], context_chars: int = 200
) -> str:
    """Extract a relevant section around the first occurrence of any keyword.

    Searches body first, then subject if body doesn't contain any keyword.
    Returns up to context_chars before and after the match. If no keywords are
    found, returns the first 2*context_chars of body (or subject fallback).
    """
    haystack_primary = body or ""
    haystack_secondary = subject or ""

    # Helper to find first match index and length
    def find_first(hay: str) -> Optional[tuple]:
        if not hay:
            return None
        low = hay.lower()
        best_idx = None
        best_len = 0
        for kw in _normalize_keywords(keywords):
            k = kw.lower().strip()
            if not k:
                continue
            idx = low.find(k)
            if idx != -1 and (best_idx is None or idx < best_idx):
                best_idx = idx
                best_len = len(k)
        return (best_idx, best_len) if best_idx is not None else None

    target_text = haystack_primary
    match = find_first(haystack_primary)
    if match is None:
        match = find_first(haystack_secondary)
        target_text = haystack_secondary

    if match is None:
        # Fallback
        text = haystack_primary or haystack_secondary
        text = text.strip()
        if not text:
            return ""
        max_len = context_chars * 2
        return text[:max_len] + ("..." if len(text) > max_len else "")

    idx, match_len = match
    start = max(0, idx - context_chars)
    end = min(len(target_text), idx + match_len + context_chars)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(target_text) else ""
    return prefix + target_text[start:end] + suffix


async def search_emails_snapshot(
    gmail_api: GmailAPI,
    keywords: List[str] = None,
    email_addresses: List[str] = None,
    timerange_days: int = None,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """Search emails and return a lightweight snapshot for each match.

    Usage:
    - Provide simple keywords like ["gemini", "google"]; the wrapper will search subject, body, from, to, and cc.
    - You can also pass Gmail operators directly (e.g., ["has:attachment", "from:gmail.com"]).
    - Optionally filter by specific sender addresses via email_addresses, and/or by a relative date range.

    Args:
    - gmail_api: An initialized GmailAPI instance.
    - keywords: List of terms and/or Gmail operators. Plain terms are expanded across fields.
    - email_addresses: Optional list of sender email addresses to include (added as from:address filters).
    - timerange_days: Optional integer for Gmail newer_than:Nd filter (e.g., 7 for last 7 days).
    - max_results: Max number of results to return.

    Returns: List of dict with keys:
    - id, subject, datetime, from, relevant_section (up to 200 chars on either side of the first match; sensible fallback if no match).
    """
    # Build search query
    query = _build_gmail_query_from_keywords(keywords, email_addresses, timerange_days)

    # Debug: Print the actual search query being sent
    print(f"      DEBUG: Search query: '{query}'")

    # If no query specified, get recent emails without search
    if not query.strip():
        result = await gmail_api.get_inbox_emails(max_results=max_results)
    else:
        # Search emails
        result = await gmail_api.search_emails(query, max_results)

    messages = result.get("messages", [])

    # Ensure newest-first ordering (also enforced in API layer)
    messages = sorted(
        messages, key=lambda m: int(m.get("internal_date") or 0), reverse=True
    )

    # Create lightweight snapshot using the parsed message data
    snapshot = []
    for msg in messages:
        # The Gmail API already parses the message, so we can access the fields directly
        subject = msg.get("subject", "").strip() or "No Subject"
        body = msg.get("body", "").strip()
        relevant = _extract_relevant_section(
            subject, body, _normalize_keywords(keywords), context_chars=200
        )

        snapshot.append(
            {
                "id": msg.get("id"),
                "subject": subject,
                "datetime": msg.get("date", "Unknown"),
                "from": msg.get("from", "Unknown"),
                "relevant_section": relevant,
            }
        )

    return snapshot


async def search_emails_by_keywords_detailed(
    gmail_api: GmailAPI,
    keywords: List[str] = None,
    timerange_days: int = None,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """Search emails and return full message content with metadata.

    Usage:
    - Pass keyword list like ["gemini", "google"] or operator terms like ["has:attachment"].

    Args:
    - gmail_api: GmailAPI instance.
    - keywords: List of terms/operators. Plain terms are expanded across subject/body/from/to/cc.
    - timerange_days: Optional newer_than:Nd filter.
    - max_results: Max results to fetch.

    Returns: List[dict] with id, subject, from, to, date, body, attachments (count), labels.
    """
    # Build search query
    query = _build_gmail_query_from_keywords(keywords, None, timerange_days)

    # Debug: Print the actual search query being sent
    print(f"      DEBUG: Search query: '{query}'")

    # If no query specified, get recent emails without search
    if not query.strip():
        result = await gmail_api.get_inbox_emails(max_results=max_results)
    else:
        # Search emails
        result = await gmail_api.search_emails(query, max_results)

    messages = result.get("messages", [])

    # Ensure newest-first ordering (also enforced in API layer)
    messages = sorted(
        messages, key=lambda m: int(m.get("internal_date") or 0), reverse=True
    )

    # Return full emails with metadata using parsed message data
    detailed_emails = []
    for msg in messages:
        subject = msg.get("subject", "").strip() or "No Subject"

        detailed_emails.append(
            {
                "id": msg.get("id"),
                "subject": subject,
                "from": msg.get("from", "Unknown"),
                "to": msg.get("to", "Unknown"),
                "date": msg.get("date", "Unknown"),
                "body": msg.get("body", ""),
                "attachments": len(msg.get("attachments", [])),
                "labels": msg.get("label_ids", []),
            }
        )

    return detailed_emails


async def send_new_email(
    gmail_api: GmailAPI,
    message: str,
    attachments_url: List[str] = None,
    attachments: List[str] = None,
) -> str:
    """Send a new email with optional attachments."""
    try:
        # Get user's email for self-sending
        profile = await gmail_api.get_profile()
        user_email = profile.get("email_address", "")

        # Create subject and body
        subject = "Test Email - Gmail API Wrapper Functions"
        body = """Hello!

{message}

This is a test email sent using the new Gmail wrapper functions.

Best regards,
Gmail API Test Script
"""

        # Send email
        result = await gmail_api.send_email(
            to=user_email, subject=subject, body=body, attachments=attachments
        )

        return result.get("id", "")
    except Exception as e:
        print(f"Error in send_new_email: {e}")
        return ""


async def retrieve_specific_email_thread(
    gmail_api: GmailAPI, message_id: str
) -> Dict[str, Any]:
    """Retrieve an email or thread with detailed information including attachments."""
    try:
        # Get the message
        message = await gmail_api.get_email(message_id)

        # Get thread if available
        thread_id = message.get("thread_id")
        thread_messages = []
        if thread_id:
            thread_result = await gmail_api.get_email_threads(thread_id)
            thread_messages = thread_result.get("messages", [])

        return {
            "message": message,
            "thread_messages": thread_messages,
            "thread_id": thread_id,
            "has_attachments": len(message.get("attachments", [])) > 0,
        }
    except Exception as e:
        print(f"Error in retrieve_specific_email_thread: {e}")
        return {}


async def retrieve_emails_by_label_snapshot(
    gmail_api: GmailAPI,
    label_name: str,
    daterange: str = "1d",
    keywords: List[str] = None,
    email_address_filter: List[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve emails by label with optional keyword, sender, and date filters.

    Usage:
    - Example: retrieve_emails_by_label_snapshot(api, "AI_relabeled", "1w", ["gemini"]).

    Args:
    - label_name: Gmail label name (e.g., "INBOX", custom label).
    - daterange: One of {"1d", "1w", "1m"}; converted to newer_than.
    - keywords: List of terms/operators. Plain terms are expanded across subject/body/from/to/cc.
    - email_address_filter: Optional list of sender addresses.

    Returns: List of snapshot dicts with id, subject, datetime, from, relevant_section.
    """
    try:
        # Base label and date filters
        parts = [f"label:{label_name}"]
        if daterange:
            if daterange in {"1d", "1w", "1m"}:
                parts.append(f"newer_than:{daterange}")
        # Keywords and address filters
        query_expanded = _build_gmail_query_from_keywords(
            keywords, email_address_filter, None
        )
        if query_expanded:
            parts.append(query_expanded)
        query = " ".join(parts)

        # Search emails
        result = await gmail_api.search_emails(query, max_results=20)
        messages = result.get("messages", [])

        # Create snapshot aligned to new shape
        snapshot = []
        for msg in messages:
            subject = msg.get("subject", "No Subject")
            body = msg.get("body", "")
            relevant = _extract_relevant_section(
                subject, body, _normalize_keywords(keywords or []), context_chars=200
            )
            snapshot.append(
                {
                    "id": msg.get("id"),
                    "subject": subject,
                    "datetime": msg.get("date", "Unknown"),
                    "from": msg.get("from", "Unknown"),
                    "relevant_section": relevant,
                }
            )

        return snapshot
    except Exception as e:
        print(f"Error in retrieve_emails_by_label_snapshot: {e}")
        return []


async def label_emails(
    gmail_api: GmailAPI, label_name: str, message_ids: List[str]
) -> Dict[str, Any]:
    """Create (if needed) or find a label, and apply it to given message IDs.

    Args:
    - label_name: Label to apply (created if missing).
    - message_ids: List of Gmail message IDs.

    Returns: Dict with label_name, label_id, and per-message results.
    """
    try:
        # Find or create label
        label_result = await gmail_api.find_or_create_label(label_name)
        label_id = label_result.get("id")

        if not label_id:
            return {"error": "Could not create/find label"}

        # Apply label to all messages
        results = []
        for msg_id in message_ids:
            try:
                await gmail_api.add_label_to_email(msg_id, [label_id])
                results.append({"message_id": msg_id, "status": "success"})
            except Exception as e:
                results.append(
                    {"message_id": msg_id, "status": "error", "error": str(e)}
                )

        return {"label_name": label_name, "label_id": label_id, "results": results}
    except Exception as e:
        print(f"Error in label_emails: {e}")
        return {"error": str(e)}


async def get_last_received_email_with_attachments(
    gmail_api: GmailAPI, label: str = "INBOX"
) -> Dict[str, Any]:
    """Get the most recent email (by label) including attachments list.

    Args:
    - label: One of "INBOX", "SENT", or any custom label.

    Returns: Dict with id, subject, from, date, body, attachments (list), labels.
    """
    try:
        if label == "INBOX":
            result = await gmail_api.get_inbox_emails(max_results=1)
        elif label == "SENT":
            result = await gmail_api.get_sent_emails(max_results=1)
        else:
            result = await gmail_api.search_emails(f"label:{label}", max_results=1)

        messages = result.get("messages", [])
        if not messages:
            return {}

        message = messages[0]
        return {
            "id": message.get("id"),
            "subject": message.get("subject", "No Subject"),
            "from": message.get("from", "Unknown"),
            "date": message.get("date", "Unknown"),
            "body": message.get("body", ""),
            "attachments": message.get("attachments", []),
            "labels": message.get("label_ids", []),
        }
    except Exception as e:
        print(f"Error in get_last_received_email_with_attachments: {e}")
        return {}


async def star_email(
    gmail_api: GmailAPI, message_ids: List[str], star: bool = True
) -> Dict[str, Any]:
    """Star or unstar the given messages.

    Args:
    - message_ids: List of Gmail message IDs.
    - star: True to star, False to unstar.

    Returns: Dict with action, message_ids, result (API response).
    """
    try:
        if star:
            result = await gmail_api.star_email(message_ids)
        else:
            result = await gmail_api.unstar_email(message_ids)

        return {
            "action": "star" if star else "unstar",
            "message_ids": message_ids,
            "result": result,
        }
    except Exception as e:
        print(f"Error in star_email: {e}")
        return {"error": str(e)}


async def mark_emails_as_read(
    gmail_api: GmailAPI, message_ids: List[str]
) -> Dict[str, Any]:
    """Mark the given messages as read.

    Args:
    - message_ids: List of Gmail message IDs.

    Returns: Dict with action, message_ids, result.
    """
    try:
        result = await gmail_api.mark_as_read(message_ids)
        return {"action": "mark_as_read", "message_ids": message_ids, "result": result}
    except Exception as e:
        print(f"Error in mark_emails_as_read: {e}")
        return {"error": str(e)}


async def get_unread_emails_snapshot(gmail_api: GmailAPI) -> List[Dict[str, Any]]:
    """Get snapshot of unread emails using the standardized snapshot shape.

    Returns: List of dicts: id, subject, datetime, from, relevant_section.
    """
    try:
        result = await gmail_api.search_emails("is:unread", max_results=20)
        messages = result.get("messages", [])

        snapshot = []
        for msg in messages:
            subject = msg.get("subject", "No Subject")
            body = msg.get("body", "")
            relevant = _extract_relevant_section(subject, body, [], context_chars=200)
            snapshot.append(
                {
                    "id": msg.get("id"),
                    "subject": subject,
                    "datetime": msg.get("date", "Unknown"),
                    "from": msg.get("from", "Unknown"),
                    "relevant_section": relevant,
                }
            )

        return snapshot
    except Exception as e:
        print(f"Error in get_unread_emails_snapshot: {e}")
        return []


async def reply_to_email(
    gmail_api: GmailAPI,
    message_id: str,
    text: str,
    attachments: List[str] = None,
    to: List[str] = None,
    cc: List[str] = None,
) -> str:
    """Reply to a message, optionally adding attachments and overriding recipients.

    Args:
    - message_id: The Gmail message ID to reply to.
    - text: Plaintext body to include in reply.
    - attachments: Optional list of file paths.
    - to: Optional list of recipient addresses (override default reply-to).
    - cc: Optional list of CC addresses.

    Returns: New reply message ID (str) on success, empty string otherwise.
    """
    try:
        result = await gmail_api.reply_to_email(
            message_id=message_id,
            body=text,
            body_type="text",
            to=to,
            cc=cc,
            attachments=attachments,
        )
        return result.get("id", "")
    except Exception as e:
        print(f"Error in reply_to_email: {e}")
        return ""


async def forward_email_and_reply(
    gmail_api: GmailAPI,
    message_id: str,
    text: str,
    attachments: List[str] = None,
    to: List[str] = None,
    cc: List[str] = None,
) -> str:
    """Forward an email to the authenticated user, with additional text and optional recipients.

    Args:
    - message_id: Gmail message ID to forward.
    - text: Plaintext body to include in forward.
    - attachments: Optional list of file paths to attach.
    - to: Optional list of additional To recipients.
    - cc: Optional list of CC recipients.

    Returns: New forwarded message ID (str) on success, empty string otherwise.
    """
    try:
        # Get user's email for self-forwarding
        profile = await gmail_api.get_profile()
        user_email = profile.get("email_address", "")

        result = await gmail_api.forward_email(
            message_id=message_id,
            to=user_email if not to else to,
            body=text,
            body_type="text",
            cc=cc,
            attachments=attachments,
        )
        return result.get("id", "")
    except Exception as e:
        print(f"Error in forward_email_and_reply: {e}")
        return ""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_random_gmail_user():
    """Get a random user with Gmail integration from the database."""
    known_test_user = ("agm.redpenguin", "base")
    print("🔍 Looking for Gmail users in database...")
    print(
        f"📝 Known test user: entity_id={known_test_user[0]}, user_id={known_test_user[1]}"
    )

    try:
        db_path = "/home/arunraj/development/integrati/integrati/integrati_backend/data/mcp_plexus_data.sqlite3"

        if not os.path.exists(db_path):
            print(f"❌ Database not found at: {db_path}")
            print("Using known test user as fallback")
            return known_test_user

        print(f"✅ Found database at: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query for Gmail users
        try:
            query = """
            SELECT DISTINCT entity_id, provider_name
            FROM tenant_external_oauth_tokens
            WHERE provider_name = 'gmail'
            AND token_data IS NOT NULL
            AND token_data != ''
            LIMIT 10
            """
            cursor.execute(query)
            gmail_providers = cursor.fetchall()
            print(f"🔍 Found {len(gmail_providers)} Gmail providers")

            if gmail_providers:
                selected_user = random.choice(gmail_providers)
                entity_id, provider_name = selected_user
                print(f"✅ Found Gmail user: entity_id={entity_id}, user_id=base")
                return entity_id, "base"

        except Exception as e:
            print(f"❌ Query failed: {e}")

        conn.close()
        print("Using known test user as fallback")
        return known_test_user

    except Exception as e:
        print(f"❌ Database error: {e}")
        print("Using known test user as fallback")
        return known_test_user


def create_test_attachment(content: str = None) -> str:
    """Create a test attachment file for testing purposes."""
    if content is None:
        content = """This is a test attachment file for Gmail API testing.
Created at: Test run
It contains some sample text to verify that attachments are working correctly.

Test content includes:
- Multiple lines of text
- Special characters: !@#$%^&*()
- Numbers: 1234567890
- Unicode: 🚀 📧 ✨

This file is used to test the Gmail API attachment functionality.
"""

    filename = f"/tmp/test_attachment_{int(datetime.now().timestamp())}.txt"

    try:
        with open(filename, "w") as f:
            f.write(content)
        return filename
    except Exception as e:
        print(f"Warning: Could not create test attachment {filename}: {e}")
        return None


# ============================================================================
# MAIN TEST FUNCTION
# ============================================================================


async def test_gmail_wrapper_functions():
    """Test all the new Gmail wrapper functions."""

    # Get Gmail user
    entity_id, user_id = get_random_gmail_user()

    if not entity_id or not user_id:
        print("❌ No valid credentials provided. Exiting.")
        return

    print(
        f"\n🧪 Testing Gmail Wrapper Functions for entity: {entity_id}, user: {user_id}"
    )
    print("=" * 80)

    gmail_api = GmailAPI(entity_id, user_id)

    profile = await gmail_api.get_profile()
    user_email = profile.get("email_address", "")
    print(f"📧 User email: {user_email}")

    print("\n" + "=" * 80)
    print("🔍 TESTING SEARCH AND RETRIEVAL FUNCTIONS")
    print("=" * 80)

    # Test 1: Search emails snapshot
    print("\n1. Testing search_emails_snapshot")
    print(
        "   Input: keywords=['gemini'], email_addresses=[], timerange_days=7, max_results=5"
    )
    result1 = await search_emails_snapshot(gmail_api, ["gemini"], [], 7, 5)
    print(f"   Output: Found {len(result1)} emails and showing first 2")
    if result1:
        for i, email in enumerate(result1[:2]):  # Show first 2
            print(f"      {i+1}. Subject: {email.get('subject', 'N/A')}")
            print(f"         From: {email.get('from', 'N/A')}")
            print(f"         Relevant: {email.get('relevant_section', 'N/A')[:100]}...")
    else:
        print("      No emails found with 'gemini' keyword in last week")

    # Test 2: Search emails by keywords detailed
    print("\n2. Testing search_emails_by_keywords_detailed")
    print("   Input: keywords=['google'], timerange_days=7, max_results=3")
    result2 = await search_emails_by_keywords_detailed(gmail_api, ["google"], 7, 3)
    print(f"   Output: Found {len(result2)} emails and showing first 2")
    if result2:
        for i, email in enumerate(result2[:2]):  # Show first 2
            print(f"      {i+1}. Subject: {email.get('subject', 'N/A')}")
            print(f"         From: {email.get('from', 'N/A')}")
            print(f"         Attachments: {email.get('attachments', 0)}")
    else:
        print("      No emails found with 'gemini' keyword in last week")

    # Test 3: Search emails from Google Gemini specifically
    print("\n3. Testing search_emails_snapshot from Google Gemini")
    print(
        "   Input: keywords=[], email_addresses=['noreply@google.com'], timerange_days=7, max_results=3"
    )
    result3 = await search_emails_snapshot(gmail_api, [], ["noreply@google.com"], 7, 3)
    print(f"   Output: Found {len(result3)} emails and showing first 2")
    if result3:
        for i, email in enumerate(result3[:2]):  # Show first 2
            print(f"      {i+1}. Subject: {email.get('subject', 'N/A')}")
            print(f"         From: {email.get('from', 'N/A')}")
            print(f"         Datetime: {email.get('datetime', 'N/A')}")
    else:
        print("      No emails found from noreply@google.com in last week")

    # Test 4: Search emails without any restrictions
    print("\n4. Testing search_emails_snapshot without restrictions")
    print(
        "   Input: keywords=[], email_addresses=[], timerange_days=None, max_results=3"
    )
    result4 = await search_emails_snapshot(gmail_api, [], [], None, 3)
    print(f"   Output: Found {len(result4)} emails and showing first 2")
    if result4:
        for i, email in enumerate(result4[:2]):  # Show first 2
            print(f"      {i+1}. Subject: {email.get('subject', 'N/A')}")
            print(f"         From: {email.get('from', 'N/A')}")
            print(f"         Datetime: {email.get('datetime', 'N/A')}")
            # Show snippet/body preview to verify we're getting content
            relevant = email.get("relevant_section", "").strip()
            if relevant:
                print(f"         Relevant: {relevant[:100]}...")
    else:
        print("      No emails found without any restrictions")

    # Test 5: Let's also test getting recent emails with a broader search
    print("\n5. Testing search for recent emails from any Gmail address")
    print("   Input: keywords=['from:gmail.com'], timerange_days=30, max_results=5")
    result5 = await search_emails_snapshot(gmail_api, ["from:gmail.com"], [], 30, 5)
    print(
        f"   Output: Found {len(result5)} emails from Gmail addresses in last 30 days"
    )
    if result5:
        for i, email in enumerate(result5[:3]):  # Show first 3
            print(f"      {i+1}. Subject: {email.get('subject', 'N/A')}")
            print(f"         From: {email.get('from', 'N/A')}")
            relevant = email.get("relevant_section", "").strip()
            if relevant:
                print(f"         Relevant: {relevant[:80]}...")

    # Test 6: Test searching for emails with attachments
    print("\n6. Testing search for emails with attachments")
    print("   Input: keywords=['has:attachment'], timerange_days=30, max_results=3")
    result6 = await search_emails_snapshot(gmail_api, ["has:attachment"], [], 30, 3)
    print(f"   Output: Found {len(result6)} emails with attachments in last 30 days")
    if result6:
        for i, email in enumerate(result6[:2]):  # Show first 2
            print(f"      {i+1}. Subject: {email.get('subject', 'N/A')}")
            print(f"         From: {email.get('from', 'N/A')}")
    else:
        print("      No emails with attachments found in last month")

    # Test 7: Get unread emails snapshot
    print("\n7. Testing get_unread_emails_snapshot")
    print("   Input: None")
    unread_list = await get_unread_emails_snapshot(gmail_api)
    print(f"   Output: Found {len(unread_list)} unread emails and showing first 2")
    for i, email in enumerate(unread_list[:2]):  # Show first 2
        print(f"      {i+1}. Subject: {email.get('subject', 'N/A')}")
        print(f"         From: {email.get('from', 'N/A')}")
        print(f"         Datetime: {email.get('datetime', 'N/A')}")
        rel = email.get("relevant_section", "") or ""
        if rel:
            print(f"         Relevant: {rel[:100]}...")

    # Test 8: Get last received email with attachments
    print("\n8. Testing get_last_received_email_with_attachments")
    print("   Input: label='INBOX'")
    last_with_attachments = await get_last_received_email_with_attachments(
        gmail_api, "INBOX"
    )
    if last_with_attachments:
        print(
            f"   Output: Last email subject: {last_with_attachments.get('subject', 'N/A')}"
        )
        print(f"           From: {last_with_attachments.get('from', 'N/A')}")
        print(
            f"           Attachments: {len(last_with_attachments.get('attachments', []))}"
        )
    else:
        print("   Output: No emails found")

    print("\n" + "=" * 80)
    print("📧 TESTING EMAIL SENDING FUNCTIONS")
    print("=" * 80)

    # Test 9: Send email without attachments
    print("\n9. Testing send_new_email (no attachments)")
    print("   Input: message='Testing email without attachments'")
    email_id_no_attachments = await send_new_email(
        gmail_api, "Testing email without attachments"
    )
    if email_id_no_attachments:
        print(
            f"   Output: Email sent successfully! Message ID: {email_id_no_attachments}"
        )
    else:
        print("   Output: Failed to send email")

    # Test 10: Send email with attachments
    print("\n10. Testing send_new_email (with attachments)")
    print("   Input: message='Testing email with attachments', attachments=[test_file]")
    test_file = create_test_attachment()
    email_id_with_attachments = await send_new_email(
        gmail_api, "Testing email with attachments", attachments=[test_file]
    )
    if email_id_with_attachments:
        print(
            f"   Output: Email sent successfully! Message ID: {email_id_with_attachments}"
        )
    else:
        print("   Output: Failed to send email")

    # Wait for emails to be processed
    if email_id_no_attachments or email_id_with_attachments:
        print("\n⏳ Waiting 5 seconds for emails to be processed...")
        await asyncio.sleep(5)

    print("\n" + "=" * 80)
    print("🏷️  TESTING LABELING FUNCTIONS")
    print("=" * 80)

    # Test 11: Label emails to "AI"
    if email_id_no_attachments and email_id_with_attachments:
        print("\n11. Testing label_emails")
        print(
            f"   Input: label_name='AI', message_ids=[{email_id_no_attachments}, {email_id_with_attachments}]"
        )
        result7 = await label_emails(
            gmail_api, "AI", [email_id_no_attachments, email_id_with_attachments]
        )
        if result7.get("error"):
            print(f"   Output: Error - {result7.get('error')}")
        else:
            print(
                f"   Output: Successfully labeled {len(result7.get('results', []))} emails"
            )
            print(f"           Label ID: {result7.get('label_id')}")

    print("\n" + "=" * 80)
    print("📎 TESTING RETRIEVAL FUNCTIONS")
    print("=" * 80)

    # Test 12: Retrieve specific email thread (no attachments)
    if email_id_no_attachments:
        print("\n12. Testing retrieve_specific_email_thread (no attachments)")
        print(f"   Input: message_id='{email_id_no_attachments}'")
        result8 = await retrieve_specific_email_thread(
            gmail_api, email_id_no_attachments
        )
        if result8 and result8.get("message"):
            print("   Output: Retrieved message successfully")
            message = result8.get("message", {})
            subject = message.get("subject", "No Subject")
            print(f"           Subject: {subject}")
            print(
                f"           Has attachments: {result8.get('has_attachments', False)}"
            )
        else:
            print("   Output: Failed to retrieve message or message is empty")

    # Test 13: Retrieve specific email thread (with attachments)
    if email_id_with_attachments:
        print("\n13. Testing retrieve_specific_email_thread (with attachments)")
        print(f"   Input: message_id='{email_id_with_attachments}'")
        result9 = await retrieve_specific_email_thread(
            gmail_api, email_id_with_attachments
        )
        if result9 and result9.get("message"):
            print("   Output: Retrieved message successfully")
            message = result9.get("message", {})
            subject = message.get("subject", "No Subject")
            print(f"           Subject: {subject}")
            print(
                f"           Has attachments: {result9.get('has_attachments', False)}"
            )
            if result9.get("has_attachments"):
                attachments = result9.get("message", {}).get("attachments", [])
                print(f"           Attachment count: {len(attachments)}")
        else:
            print("   Output: Failed to retrieve message or message is empty")

    print("\n" + "=" * 80)
    print("🔄 TESTING REPLY AND FORWARD FUNCTIONS")
    print("=" * 80)

    # Test 14: Reply to email (no attachments)
    if email_id_no_attachments:
        print("\n14. Testing reply_to_email")
        print(
            f"    Input: message_id='{email_id_no_attachments}', text='This is a test reply', to=['arun7569raj@gmail.com'], cc=['agm.redpenguin@gmail.com']"
        )
        result10 = await reply_to_email(
            gmail_api,
            email_id_no_attachments,
            "This is a test reply",
            to=["arun7569raj@gmail.com"],
            cc=["agm.redpenguin@gmail.com"],
        )
        if result10:
            print(f"    Output: Reply sent successfully! Message ID: {result10}")
        else:
            print("    Output: Failed to send reply")

    # Test 15: Reply to email with custom to/cc
    if email_id_no_attachments:
        print("\n15. Testing reply_to_email with custom to/cc")
        print(
            f"    Input: message_id='{email_id_no_attachments}', text='This is a test reply with custom recipients', to=['arun7569raj@gmail.com'], cc=['agm.redpenguin@gmail.com']"
        )
        result10b = await reply_to_email(
            gmail_api,
            email_id_no_attachments,
            "This is a test reply with custom recipients",
            to=["arun7569raj@gmail.com"],
            cc=["agm.redpenguin@gmail.com"],
        )
        if result10b:
            print(
                f"    Output: Reply with custom recipients sent successfully! Message ID: {result10b}"
            )
        else:
            print("    Output: Failed to send reply with custom recipients")

    print("\n" + "=" * 80)
    print("⭐ TESTING STAR AND READ FUNCTIONS")
    print("=" * 80)

    # Test 16: Star emails
    if email_id_no_attachments:
        print("\n16. Testing star_email")
        print(f"    Input: message_ids=[{email_id_no_attachments}], star=True")
        result12 = await star_email(gmail_api, [email_id_no_attachments], True)
        if result12.get("error"):
            print(f"    Output: Error - {result12.get('error')}")
        else:
            print(
                f"    Output: Successfully starred {len(result12.get('message_ids', []))} emails"
            )

    # Test 17: Mark emails as read
    if email_id_with_attachments:
        print("\n17. Testing mark_emails_as_read")
        print(f"    Input: message_ids=[{email_id_with_attachments}]")
        result13 = await mark_emails_as_read(gmail_api, [email_id_with_attachments])
        if result13.get("error"):
            print(f"    Output: Error - {result13.get('error')}")
        else:
            print(
                f"    Output: Successfully marked {len(result13.get('message_ids', []))} emails as read"
            )

    print("\n" + "=" * 80)
    print("🏷️  TESTING LABEL RETRIEVAL")
    print("=" * 80)

    # Test 18: Retrieve emails by label snapshot
    print("\n18. Testing retrieve_emails_by_label_snapshot")
    print("    Input: label_name='AI_relabeled', daterange='1d', keywords=['gemini']")
    result14 = await retrieve_emails_by_label_snapshot(
        gmail_api, "AI_relabeled", "1d", ["gemini"]
    )
    print(
        f"    Output: Found {len(result14)} emails with AI_relabeled label and showing first 2"
    )
    if result14:
        for i, email in enumerate(result14[:2]):  # Show first 2
            print(f"       {i+1}. Subject: {email.get('subject', 'N/A')}")
            print(f"          From: {email.get('from', 'N/A')}")
            print(f"          Datetime: {email.get('datetime', 'N/A')}")
            rel = email.get("relevant_section", "") or ""
            if rel:
                print(f"          Relevant: {rel[:100]}...")
    else:
        print("       No emails found with AI_relabeled label")

    print("\n" + "=" * 80)
    print("✅ TESTING COMPLETE!")
    print("=" * 80)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("🚀 Gmail API Wrapper Functions Test Script")
    print("=" * 50)

    # Test the new wrapper functions
    asyncio.run(test_gmail_wrapper_functions())

    print("\n✨ Testing complete!")
