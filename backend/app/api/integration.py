from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.crud.integration import create_user_integration, get_user_integrations, update_user_integration_status
from app.crud.tool import create_user_tool, get_user_tools, update_user_tool_state, get_user_tool
from app.crud.pending_action import get_pending_actions, update_pending_action_status
from app.models.integration import UserIntegration, UserIntegrationResponse
from app.models.tool import UserTool, UserToolResponse
from app.models.pending_action import PendingAction, PendingActionResponse
from typing import List

router = APIRouter()

from app.core.dependencies import get_current_user
from app.models.user import UserInDB

def get_user_id(request: Request):
    raise NotImplementedError('Use Depends(get_current_user) instead')

@router.get('/integrations', response_model=List[UserIntegrationResponse])
def list_integrations(current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_user_integrations(db, current_user.id)

@router.post('/integrations/{integration_name}', response_model=UserIntegrationResponse)
def connect_integration(integration_name: str, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):
    integration = create_user_integration(db, current_user.id, integration_name)
    # TODO: Create default tools for this integration for the user
    return integration

@router.delete('/integrations/{integration_name}', response_model=UserIntegrationResponse)
def disconnect_integration(integration_name: str, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):
    integration = update_user_integration_status(db, current_user.id, integration_name, 'disconnected')
    return integration

@router.get('/integrations/{integration_name}/tools', response_model=List[UserToolResponse])
def list_tools(integration_name: str, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_user_tools(db, current_user.id, integration_name)

@router.get('/integrations/{integration_name}/tools/{tool_name}', response_model=UserToolResponse)
def get_tool_state(integration_name: str, tool_name: str, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):
    tool = get_user_tool(db, current_user.id, integration_name, tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail='Tool not found')
    return tool

@router.put('/integrations/{integration_name}/tools/{tool_name}', response_model=UserToolResponse)
def set_tool_state(integration_name: str, tool_name: str, state: str, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):
    tool = update_user_tool_state(db, current_user.id, integration_name, tool_name, state)
    if not tool:
        raise HTTPException(status_code=404, detail='Tool not found')
    return tool

@router.get('/pending-actions', response_model=List[PendingActionResponse])
def list_pending_actions(current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_pending_actions(db, current_user.id)

from app.mcp.instance import mcp

@router.post('/pending-actions/{action_id}/approve', response_model=PendingActionResponse)
def approve_pending_action(action_id: int, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):
    action = update_pending_action_status(db, action_id, 'approved')
    # Execute the tool if action is present and approved
    if action and action.status == 'approved':
        # Dynamically call the tool using MCP registry
        integration = action.integration_name
        tool = action.tool_name
        params = action.parameters or {}
        # Insert user_id if not present
        if 'user_id' not in params:
            params['user_id'] = action.user_id
        # Find the tool function
        mcp_tool = getattr(mcp.tools.get(integration, {}), tool, None)
        if mcp_tool is None:
            # fallback: try mcp.tools[tool]
            mcp_tool = mcp.tools.get(tool)
        if mcp_tool:
            try:
                result = mcp_tool(**params)
                action.result = result if isinstance(result, dict) else {'result': result}
            except Exception as e:
                action.result = {'error': str(e)}
        db.commit()
        db.refresh(action)
    return action

@router.post('/pending-actions/{action_id}/reject', response_model=PendingActionResponse)
def reject_pending_action(action_id: int, request: Request, db: Session = Depends(get_db)):
    action = update_pending_action_status(db, action_id, 'rejected')
    return action 