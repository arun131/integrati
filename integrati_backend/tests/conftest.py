"""Common test fixtures and configuration."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path
import sys
import os

# Add the integrati_backend directory to the Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_settings():
    """Mock settings fixture for testing."""
    with pytest.MonkeyPatch().context() as m:
        # Mock environment variables
        m.setenv("DEBUG_MODE", "false")
        m.setenv("STORAGE_BACKEND", "sqlite")
        m.setenv("REDIS_HOST", "localhost")
        m.setenv("REDIS_PORT", "6379")
        yield m


@pytest.fixture
def mock_logger():
    """Mock logger fixture for testing."""
    with pytest.MonkeyPatch().context() as m:
        mock_logger = MagicMock()
        m.setattr("mcp_plexus.tool_loader.logger", mock_logger)
        m.setattr("mcp_plexus.settings.logger", mock_logger)
        m.setattr("mcp_plexus.main.logger", mock_logger)
        yield mock_logger


@pytest.fixture
def mock_path():
    """Mock pathlib.Path fixture for testing."""
    with pytest.MonkeyPatch().context() as m:
        mock_path = MagicMock()
        m.setattr("pathlib.Path", mock_path)
        yield mock_path


@pytest.fixture
def mock_async_context():
    """Async context manager fixture for testing."""

    async def async_context():
        return AsyncMock()

    return async_context


@pytest.fixture
def sample_integration_data():
    """Sample integration data for testing."""
    return {
        "gmail": {
            "name": "gmail",
            "tools_file": "tools.py",
            "has_register_function": True,
        },
        "slack": {
            "name": "slack",
            "tools_file": "tools.py",
            "has_register_function": False,
        },
    }


@pytest.fixture
def mock_fastapi_app():
    """Mock FastAPI app fixture for testing."""
    mock_app = MagicMock()
    mock_app.routes = []
    mock_app.user_middleware = []
    mock_app.title = "MCP Plexus"
    mock_app.version = "1.0.0"
    mock_app.description = "Test description"
    return mock_app


@pytest.fixture
def mock_test_client():
    """Mock FastAPI test client fixture."""
    from fastapi.testclient import TestClient
    from mcp_plexus.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    # Ensure we're in the right directory
    os.chdir(str(project_root))

    # Set test environment variables
    os.environ.setdefault("TESTING", "true")
    os.environ.setdefault("DEBUG_MODE", "false")

    yield

    # Cleanup after test
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
