from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import create_db_tables
from app.core.config import settings
from app.integrations.gmail.api import router as gmail_api_router
from app.integrations.gmail.auth import router as gmail_auth_router
from app.integrations.calendar.api import router as calendar_api_router
from app.integrations.calendar.auth import router as calendar_auth_router
from app.api.auth import router as auth_router

app = FastAPI(
    title="Gmail & Calendar Manager Backend MVP",
    description="FastAPI backend for managing Gmail and Calendar interactions.",
    version="0.1.0",
)

origins = [
    settings.FRONTEND_URL,
    "https://*.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(gmail_api_router, prefix="/integrations/gmail/api", tags=["Gmail API"])
app.include_router(gmail_auth_router, prefix="/integrations/gmail/auth", tags=["Gmail Auth"])
app.include_router(calendar_api_router, prefix="/integrations/calendar/api", tags=["Calendar API"])
app.include_router(calendar_auth_router, prefix="/integrations/calendar/auth", tags=["Calendar Auth"])

@app.on_event("startup")
def on_startup():
    create_db_tables()

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Gmail & Calendar Manager Backend MVP!"} 