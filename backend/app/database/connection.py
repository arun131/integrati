from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Ensure the database directory exists
db_dir = "app/database"
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

SQLALCHEMY_DATABASE_URL = "sqlite:///./app/database/app.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_db_tables():
    Base.metadata.create_all(bind=engine) 