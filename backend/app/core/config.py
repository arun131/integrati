from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Google OAuth credentials
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str # This will be your backend's /callback URL

    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database settings
    DATABASE_URL: str = "sqlite:///./app/database/app.db" # Relative path within container

    # CORS settings (add your Vercel frontend URL here in production)
    FRONTEND_URL: str = "http://localhost:3000" # For local development

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings() 