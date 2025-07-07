from sqlalchemy.orm import Session
from app.models.integration import UserIntegration

def create_user_integration(db: Session, user_id: int, integration_name: str, status: str = 'connected'):
    integration = UserIntegration(user_id=user_id, integration_name=integration_name, status=status)
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration

def get_user_integrations(db: Session, user_id: int):
    return db.query(UserIntegration).filter(UserIntegration.user_id == user_id).all()

def get_user_integration(db: Session, user_id: int, integration_name: str):
    return db.query(UserIntegration).filter_by(user_id=user_id, integration_name=integration_name).first()

def update_user_integration_status(db: Session, user_id: int, integration_name: str, status: str):
    integration = get_user_integration(db, user_id, integration_name)
    if integration:
        integration.status = status
        db.commit()
        db.refresh(integration)
    return integration 