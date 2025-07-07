from fastapi import Request, Depends
from app.crud.tool import get_user_tool

from app.core.dependencies import get_current_user
from app.models.user import UserInDB

def get_user_id_from_request(request: Request, current_user: UserInDB = Depends(get_current_user)):
    return current_user.id

def user_has_permission(db, user_id: int, integration: str, tool_name: str):
    tool = get_user_tool(db, user_id, integration, tool_name)
    if not tool:
        return False, None
    return tool.state == 'enabled', tool.state 