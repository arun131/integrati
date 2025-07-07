from sqlalchemy.orm import Session
from app.models.pending_action import PendingAction

def create_pending_action(db: Session, user_id: int, integration_name: str, tool_name: str, parameters: dict):
    action = PendingAction(user_id=user_id, integration_name=integration_name, tool_name=tool_name, parameters=parameters)
    db.add(action)
    db.commit()
    db.refresh(action)
    return action

def get_pending_actions(db: Session, user_id: int, status: str = 'pending'):
    return db.query(PendingAction).filter_by(user_id=user_id, status=status).all()

def update_pending_action_status(db: Session, action_id: int, status: str):
    action = db.query(PendingAction).filter_by(id=action_id).first()
    if action:
        action.status = status
        db.commit()
        db.refresh(action)
    return action 