"""Unit tests for mcp_plexus main application."""

import pytest
from unittest.mock import patch, AsyncMock

# Try to import the app, but handle import errors gracefully
try:
    from fastapi.testclient import TestClient
    from mcp_plexus.main import app

    APP_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import mcp_plexus.main: {e}")
    APP_AVAILABLE = False
    app = None


class TestMCPPlexusMain:
    """Test cases for the main MCP Plexus application."""

    def setup_method(self):
        """Set up test client for each test method."""
        if APP_AVAILABLE:
            self.client = TestClient(app)
        else:
            self.client = None

    def test_root_endpoint(self):
        """Test the root endpoint returns expected response."""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "MCP Plexus" in data["message"]

    def test_health_endpoint(self):
        """Test the health endpoint returns expected response."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    @patch("mcp_plexus.main.plexus_session_manager_instance")
    @patch("mcp_plexus.main.plexus_fastmcp_http_session_manager")
    @patch("mcp_plexus.main.plexus_user_auth_token_store_instance")
    @patch("mcp_plexus.main.plexus_user_token_manager_instance")
    @patch("mcp_plexus.main.internal_oauth_token_store_instance")
    @patch("mcp_plexus.main.internal_auth_code_store_instance")
    async def test_fastapi_startup_event(
        self,
        mock_auth_code_store,
        mock_oauth_store,
        mock_token_manager,
        mock_auth_store,
        mock_http_session,
        mock_session_manager,
    ):
        """Test the FastAPI startup event initializes components correctly."""
        # Mock the components
        mock_session_manager.return_value = AsyncMock()
        mock_http_session.return_value = AsyncMock()
        mock_auth_store.return_value = AsyncMock()
        mock_token_manager.return_value = AsyncMock()
        mock_oauth_store.return_value = AsyncMock()
        mock_auth_code_store.return_value = AsyncMock()

        # Import and call the startup function
        from mcp_plexus.main import fastapi_startup

        await fastapi_startup()

        # Verify that the startup function executed without errors
        # The actual verification would depend on the specific implementation
        assert True  # If we get here, startup didn't raise an exception

    @pytest.mark.asyncio
    @patch("mcp_plexus.main.plexus_session_manager_instance")
    @patch("mcp_plexus.main.plexus_fastmcp_http_session_manager")
    async def test_fastapi_shutdown_event(
        self, mock_http_session, mock_session_manager
    ):
        """Test the FastAPI shutdown event closes connections properly."""
        # Mock the components
        mock_session_manager.return_value = AsyncMock()
        mock_http_session.return_value = AsyncMock()

        # Import and call the shutdown function
        from mcp_plexus.main import fastapi_shutdown

        await fastapi_shutdown()

        # Verify that the shutdown function executed without errors
        assert True  # If we get here, shutdown didn't raise an exception

    def test_cors_middleware_configured(self):
        """Test that CORS middleware is properly configured."""
        # Check if CORS middleware is in the app's middleware stack
        middleware_found = False
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                middleware_found = True
                break

        assert middleware_found, "CORS middleware should be configured"

    def test_app_has_expected_routes(self):
        """Test that the app has the expected routes configured."""
        routes = [route.path for route in app.routes]

        # Check for essential routes
        assert "/" in routes, "Root route should be configured"
        assert "/health" in routes, "Health route should be configured"

        # Check for router routes (these might be prefixed)
        route_paths = [route.path for route in app.routes]
        has_oauth_routes = any("/oauth" in path for path in route_paths)
        has_auth_routes = any("/auth" in path for path in route_paths)

        # These routes should exist (they might be under different prefixes)
        assert (
            has_oauth_routes or has_auth_routes
        ), "OAuth or auth routes should be configured"

    @patch("mcp_plexus.main.settings")
    def test_app_configuration(self, mock_settings):
        """Test that the app is configured with correct settings."""
        # Mock settings
        mock_settings.app_name = "Test MCP Plexus"
        mock_settings.debug_mode = False

        # Verify app configuration
        assert app.title == "MCP Plexus"
        assert hasattr(app, "version")
        assert hasattr(app, "description")

    def test_response_handled_class(self):
        """Test the ResponseHandled class functionality."""
        from mcp_plexus.main import ResponseHandled

        # Create an instance
        response = ResponseHandled()
        assert response is not None
        assert hasattr(response, "__call__")

    def test_plexus_mcp_endpoint_class(self):
        """Test the PlexusMCPEndpoint class structure."""
        from mcp_plexus.main import PlexusMCPEndpoint

        # Verify the class has expected methods
        assert hasattr(PlexusMCPEndpoint, "get")
        assert hasattr(PlexusMCPEndpoint, "post")
        assert hasattr(PlexusMCPEndpoint, "delete")
        assert hasattr(PlexusMCPEndpoint, "_extract_and_validate_plexus_token")
        assert hasattr(PlexusMCPEndpoint, "_get_persistent_user_id_from_token")
        assert hasattr(PlexusMCPEndpoint, "_dispatch_mcp_request")
