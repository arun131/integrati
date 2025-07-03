import os
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import Optional
import base64
from email.mime.text import MIMEText

from backend.app.core.config import settings
from backend.app.crud.user import update_user_tokens

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
]

CLIENT_SECRETS_FILE = "./app/credentials.json"

def get_google_auth_flow():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )
    return flow

def get_google_credentials(token_data: dict, db_user_id: int, db):
    creds = None
    if token_data:
        creds = Credentials(
            token=token_data.get('access_token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=SCOPES
        )
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                from backend.app.crud.user import get_user_by_google_id
                db_user = get_user_by_google_id(db, token_data['google_id'])
                if db_user:
                    update_user_tokens(db, db_user, creds.token, creds.refresh_token, creds.expiry, " ".join(creds.scopes))
            except Exception as e:
                print(f"Error refreshing token: {e}")
                return None
        else:
            print("No valid credentials or refresh token available.")
            return None
    return creds

def get_gmail_service(creds: Credentials):
    return build('gmail', 'v1', credentials=creds)

def search_gmail_messages(service, query: str):
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
    except Exception as e:
        print(f"Error searching Gmail messages: {e}")
        return []

def get_last_received_email(service):
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
    except Exception as e:
        print(f"Error getting last email: {e}")
        return None

def send_gmail_message(service, sender_email: str, to_email: str, subject: str, message_text: str, thread_id: Optional[str] = None):
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
    except Exception as e:
        print(f"Error sending Gmail message: {e}")
        return None 