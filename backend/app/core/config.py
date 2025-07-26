import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Google OAuth credentials
    GOOGLE_CLIENT_ID: str = "test-client-id"
    GOOGLE_CLIENT_SECRET: str = "test-client-secret"
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/callback"

    # Integration-specific redirect URIs
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/integrations/gmail/auth/callback"
    CALENDAR_REDIRECT_URI: str = (
        "http://localhost:8000/integrations/calendar/auth/callback"
    )

    # JWT settings
    SECRET_KEY: str = "test-secret-key-for-development-only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database settings
    DATABASE_URL: str = "sqlite:///./app.db"  # Relative path within container

    # CORS settings (add your Vercel frontend URL here in production)
    FRONTEND_URL: str = "http://localhost:3000"  # For local development

    # Firebase settings (optional for testing)
    FIREBASE_PROJECT_ID: str = "test-project-id"
    FIREBASE_PRIVATE_KEY_ID: str = "test-private-key-id"
    FIREBASE_PRIVATE_KEY: str = "test-private-key"
    FIREBASE_CLIENT_EMAIL: str = "test@example.com"
    FIREBASE_CLIENT_ID: str = "test-client-id"
    FIREBASE_AUTH_URI: str = "https://accounts.google.com/o/oauth2/auth"
    FIREBASE_TOKEN_URI: str = "https://oauth2.googleapis.com/token"
    FIREBASE_AUTH_PROVIDER_X509_CERT_URL: str = (
        "https://www.googleapis.com/oauth2/v1/certs"
    )
    FIREBASE_CLIENT_X509_CERT_URL: str = (
        "https://www.googleapis.com/robot/v1/metadata/x509/test"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def __init__(self, **kwargs):
        # Check if we're in a testing environment
        if os.getenv("TESTING") == "true" or os.getenv("CI") == "true":
            # Use test defaults for CI/testing environment
            kwargs.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
            kwargs.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
            kwargs.setdefault(
                "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback"
            )
            kwargs.setdefault("SECRET_KEY", "test-secret-key-for-development-only")
            kwargs.setdefault("DATABASE_URL", "sqlite:///./test.db")

        super().__init__(**kwargs)


settings = Settings()
