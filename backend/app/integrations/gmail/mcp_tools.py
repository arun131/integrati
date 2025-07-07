from app.mcp.instance import mcp
from app.mcp.access_control import user_has_permission
from app.mcp.utils import create_pending_action_for_tool
from fastapi import Depends
from app.database.connection import get_db
from app.crud.user import get_user_by_id
from .google_auth import get_google_credentials, get_gmail_service, search_gmail_messages, send_gmail_message

def get_db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

from app.core.dependencies import get_current_user
from app.models.user import UserInDB

@mcp.tool()
def search_gmail(query: str, current_user: UserInDB = Depends(get_current_user), db=Depends(get_db_session)):
    user_id = current_user.id
    allowed, state = user_has_permission(db, user_id, 'gmail', 'search_gmail')
    if not allowed and state != 'verify':
        raise Exception('Not authorized')
    if state == 'verify':
        create_pending_action_for_tool(db, user_id, 'gmail', 'search_gmail', {"query": query})
        return {"status": "pending_user_approval"}
    user = get_user_by_id(db, user_id)
    if not user:
        raise Exception('User not found')
    creds = get_google_credentials(user.__dict__, user_id, db)
    if not creds:
        raise Exception('Could not refresh Google credentials.')
    service = get_gmail_service(creds)
    messages = search_gmail_messages(service, query)
    return {"results": messages}

@mcp.tool()
def send_gmail(user_id: int, to: str, subject: str, body: str, db=Depends(get_db_session)):
    allowed, state = user_has_permission(db, user_id, 'gmail', 'send_gmail')
    if not allowed and state != 'verify':
        raise Exception('Not authorized')
    if state == 'verify':
        create_pending_action_for_tool(db, user_id, 'gmail', 'send_gmail', {"to": to, "subject": subject, "body": body})
        return {"status": "pending_user_approval"}
    user = get_user_by_id(db, user_id)
    if not user:
        raise Exception('User not found')
    creds = get_google_credentials(user.__dict__, user_id, db)
    if not creds:
        raise Exception('Could not refresh Google credentials.')
    service = get_gmail_service(creds)
    send_result = send_gmail_message(service, user.email, to, subject, body)
    if send_result:
        return {"status": "sent", "id": send_result['id']}
    else:
        raise Exception('Failed to send email.') 