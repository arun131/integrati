from sqlalchemy.orm import Session
from app.models.tool import UserTool

def create_user_tool(db: Session, user_id: int, integration_name: str, tool_name: str, state: str = 'enabled'):
    tool = UserTool(user_id=user_id, integration_name=integration_name, tool_name=tool_name, state=state)
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool

def get_user_tools(db: Session, user_id: int, integration_name: str = None):
    query = db.query(UserTool).filter(UserTool.user_id == user_id)
    if integration_name:
        query = query.filter(UserTool.integration_name == integration_name)
    return query.all()

def get_user_tool(db: Session, user_id: int, integration_name: str, tool_name: str):
    return db.query(UserTool).filter_by(user_id=user_id, integration_name=integration_name, tool_name=tool_name).first()

def update_user_tool_state(db: Session, user_id: int, integration_name: str, tool_name: str, state: str):
    tool = get_user_tool(db, user_id, integration_name, tool_name)
    if tool:
        tool.state = state
        db.commit()
        db.refresh(tool)
    return tool 