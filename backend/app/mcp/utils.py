from app.crud.pending_action import create_pending_action

def create_pending_action_for_tool(db, user_id: int, integration: str, tool_name: str, parameters: dict):
    return create_pending_action(db, user_id, integration, tool_name, parameters) 