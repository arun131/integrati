from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Ensure the database directory exists
db_dir = "app/database"
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Only define create_db_tables, do not import models or call it here
def create_db_tables():
    from app.models.user import User
    from app.models.integration import UserIntegration
    from app.models.tool import UserTool
    from app.models.pending_action import PendingAction
    Base.metadata.create_all(bind=engine) 