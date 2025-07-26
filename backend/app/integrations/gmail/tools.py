"""
This module contains the core functions for the Gmail integration.
"""
import base64
from email.mime.text import MIMEText
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core.config import settings
from app.crud.user import update_user_tokens

def get_google_credentials(user, db_user_id: int, db) -> Optional[Credentials]:
    """Gets Google credentials from a user object."""
    # Get the actual SQLAlchemy user from database
    from app.crud.user import get_user_by_id
    db_user = get_user_by_id(db, db_user_id)
    if not db_user:
        print(f"User not found in database for ID: {db_user_id}")
        return None
    
    creds = None
    if db_user and db_user.access_token:
        print(f"Creating credentials for user: {db_user.email}")
        print(f"User scopes: {db_user.scope}")
        
        # Use the scopes that were granted during OAuth
        scopes = db_user.scope.split(' ') if db_user.scope else []
        print(f"Parsed scopes: {scopes}")
        
        user_info = {
            "token": db_user.access_token,
            "refresh_token": db_user.refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "scopes": scopes,
        }
        creds = Credentials.from_authorized_user_info(info=user_info)
        print(f"Credentials created: {creds is not None}")
        print(f"Credentials valid: {creds.valid if creds else False}")
        print(f"Credentials expired: {creds.expired if creds else False}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Attempting to refresh credentials...")
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                print("Credentials refreshed successfully")
                if db_user:
                    update_user_tokens(db, db_user, creds.token, creds.refresh_token, creds.expiry, " ".join(creds.scopes))
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                return None
        else:
            print("No valid credentials or refresh token available")
            return None
    return creds

def get_gmail_service(creds: Credentials):
    """Builds the Gmail service from credentials."""
    return build('gmail', 'v1', credentials=creds)

def search_gmail_messages(service, query: str) -> list:
    """Searches for emails in the user's Gmail account.

    Args:
        service: The Gmail service object.
        query: The search query.

    Returns:
        A list of matching emails.
    """
    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=10).execute()
        messages = results.get('messages', [])
        parsed_messages = []
        for msg in messages:
            msg_details = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            headers = msg_details['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No Date')
            snippet = msg_details.get('snippet', '')
            body = ""
            if 'parts' in msg_details['payload']:
                for part in msg_details['payload']['parts']:
                    if part['mimeType'] == 'text/plain' and 'body' in part and 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
            elif 'body' in msg_details['payload'] and 'data' in msg_details['payload']['body']:
                body = base64.urlsafe_b64decode(msg_details['payload']['body']['data']).decode('utf-8')
            parsed_messages.append({
                'id': msg['id'],
                'threadId': msg['threadId'],
                'subject': subject,
                'sender': sender,
                'date': date,
                'snippet': snippet,
                'body': body
            })
        return parsed_messages
    except Exception:
        return []

def get_last_received_email(service) -> Optional[dict]:
    """Gets the last received email from the user's Gmail account.

    Args:
        service: The Gmail service object.

    Returns:
        The last received email, or None if not found.
    """
    try:
        results = service.users().messages().list(userId='me', maxResults=1).execute()
        messages = results.get('messages', [])
        if messages:
            msg_id = messages[0]['id']
            msg_details = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            headers = msg_details['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No Date')
            body = ""
            if 'parts' in msg_details['payload']:
                for part in msg_details['payload']['parts']:
                    if part['mimeType'] == 'text/plain' and 'body' in part and 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
            elif 'body' in msg_details['payload'] and 'data' in msg_details['payload']['body']:
                body = base64.urlsafe_b64decode(msg_details['payload']['body']['data']).decode('utf-8')
            return {
                'id': msg_id,
                'threadId': msg_details['threadId'],
                'subject': subject,
                'sender': sender,
                'date': date,
                'snippet': msg_details.get('snippet', ''),
                'body': body
            }
        return None
    except Exception:
        return None

def send_gmail_message(service, sender_email: str, to_email: str, subject: str, message_text: str, thread_id: Optional[str] = None) -> Optional[dict]:
    """Sends an email using the user's Gmail account.

    Args:
        service: The Gmail service object.
        sender_email: The sender's email address.
        to_email: The recipient's email address.
        subject: The email subject.
        message_text: The email body.
        thread_id: The ID of the thread to reply to, if any.

    Returns:
        The sent message, or None on failure.
    """
    try:
        message = MIMEText(message_text)
        message['to'] = to_email
        message['from'] = sender_email
        message['subject'] = subject
        if thread_id:
            message['In-Reply-To'] = f"<{thread_id}@mail.gmail.com>"
            message['References'] = f"<{thread_id}@mail.gmail.com>"
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw_message}
        if thread_id:
            body['threadId'] = thread_id
        send_message = service.users().messages().send(userId='me', body=body).execute()
        return send_message
    except Exception:
        return None
