# mcp_plexus/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional
import logging
from pathlib import Path
import os

# Configure logging for settings module
logger = logging.getLogger(__name__)
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s SETTINGS.PY - [%(levelname)s] - %(message)s'
    )

# Determine the project root dynamically from this file's location
# This settings.py file is at MCP_Plexus/mcp_plexus/settings.py
# Two .parent calls will get to MCP_Plexus/ directory
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DOTENV_PATH = PROJECT_ROOT / ".env"

logger.info(f"SETTINGS.PY: Determined PROJECT_ROOT as: {PROJECT_ROOT}")
logger.info(f"SETTINGS.PY: Explicit .env path for pydantic-settings: {DOTENV_PATH}")

if DOTENV_PATH.exists():
    logger.info(f"SETTINGS.PY: .env file FOUND at explicit path: {DOTENV_PATH}")
else:
    logger.warning(
        f"SETTINGS.PY: .env file NOT FOUND at explicit path: {DOTENV_PATH}. "
        "Will rely on OS env vars or defaults."
    )


def get_data_directory() -> Path:
    """Determine the appropriate data directory based on environment."""
    # Check if we're running in Docker (common Docker environment variables)
    is_docker = any([
        os.path.exists('/.dockerenv'),  # Docker creates this file
        os.environ.get('DOCKER_CONTAINER') == 'true',
        os.environ.get('KUBERNETES_SERVICE_HOST'),  # Kubernetes
    ])
    
    if is_docker:
        # In Docker, use /app/data (mounted volume)
        data_dir = Path("/app/data")
        logger.info(f"SETTINGS.PY: Running in Docker environment, using data directory: {data_dir}")
    else:
        # Local development, use project-relative path
        data_dir = PROJECT_ROOT / "data"
        logger.info(f"SETTINGS.PY: Running in local environment, using data directory: {data_dir}")
    
    # Ensure the data directory exists with proper permissions
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # In local development, ensure the directory is writable
    if not is_docker:
        try:
            # Set directory permissions to 755 (rwxr-xr-x)
            data_dir.chmod(0o755)
            
            # Check if there are existing database files and make them writable
            for db_file in data_dir.glob("*.db"):
                db_file.chmod(0o666)  # Make database files writable
            for db_file in data_dir.glob("*.sqlite3"):
                db_file.chmod(0o666)  # Make database files writable
                
        except Exception as e:
            logger.warning(f"SETTINGS.PY: Could not set permissions on data directory: {e}")
    
    return data_dir


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    app_name: str = "MCP Plexus"
    debug_mode: bool = False
    storage_backend: str = "sqlite"
    
    # Redis configuration
    # Note: MCP Session Management currently defaults to and requires Redis
    # This will be made more configurable in the future
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_ssl: bool = False
    
    # SQLite configuration - Dynamic path based on environment
    sqlite_db_path: str = Field(
        default_factory=lambda: str(get_data_directory() / "mcp_plexus_data.sqlite3"),
        description="Path to the main SQLite database file"
    )
    
    # Logging and authentication settings
    plexus_fastmcp_log_level: str = "INFO"
    plexus_user_auth_token_bytes_length: int = 32
    plexus_user_auth_token_lifetime_days: Optional[int] = 90
    
    # Security settings
    host_app_registration_secret: Optional[str] = "default_secret_if_env_missing"
    admin_api_key: Optional[str] = Field(
        default=None, 
        description="API Key for accessing admin routes."
    )
    plexus_encryption_key: Optional[str] = Field(
        default=None, 
        description="Key for encrypting sensitive data like external API keys. MUST be set for production."
    )
    
    # Google OAuth settings for Gmail integration
    google_client_id: Optional[str] = Field(
        default=None,
        description="Google OAuth client ID for Gmail integration."
    )
    google_client_secret: Optional[str] = Field(
        default=None,
        description="Google OAuth client secret for Gmail integration."
    )

    model_config = SettingsConfigDict(
        env_file=DOTENV_PATH if DOTENV_PATH.exists() else None,
        extra="ignore",
        env_file_encoding='utf-8'
    )


# Initialize settings instance
settings = Settings()

# Log configuration values for debugging (sensitive values are masked)
logger.info(
    f"SETTINGS.PY: Post-Settings() settings.host_app_registration_secret: "
    f"{'********' if settings.host_app_registration_secret else 'None'} (Type: {type(settings.host_app_registration_secret)})"
)
logger.info(
    f"SETTINGS.PY: Post-Settings() settings.debug_mode: "
    f"{settings.debug_mode} (Type: {type(settings.debug_mode)})"
)
logger.info(
    f"SETTINGS.PY: Post-Settings() settings.storage_backend: "
    f"'{settings.storage_backend}' (Type: {type(settings.storage_backend)})"
)
logger.info(
    f"SETTINGS.PY: Post-Settings() settings.redis_host: "
    f"'{settings.redis_host}' (Type: {type(settings.redis_host)})"
)
logger.info(
    f"SETTINGS.PY: Post-Settings() settings.plexus_fastmcp_log_level: "
    f"'{settings.plexus_fastmcp_log_level}' (Type: {type(settings.plexus_fastmcp_log_level)})"
)
logger.info(
    f"SETTINGS.PY: Post-Settings() settings.admin_api_key: "
    f"{'********' if settings.admin_api_key else 'None'} (Type: {type(settings.admin_api_key)})"
)
logger.info(
    f"SETTINGS.PY: Post-Settings() settings.google_client_id: "
    f"{'********' if settings.google_client_id else 'None'} (Type: {type(settings.google_client_id)})"
)
logger.info(
    f"SETTINGS.PY: Post-Settings() settings.sqlite_db_path: "
    f"'{settings.sqlite_db_path}' (Type: {type(settings.sqlite_db_path)})"
)