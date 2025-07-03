from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database.connection import create_db_tables
from backend.app.api import auth, gmail
from backend.app.core.config import settings

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

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(gmail.router, prefix="/gmail", tags=["Gmail"])

@app.on_event("startup")
def on_startup():
    create_db_tables()

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Gmail & Calendar Manager Backend MVP!"} 