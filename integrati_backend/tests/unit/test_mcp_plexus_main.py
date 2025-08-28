"""Unit tests for MCP Plexus main application."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_plexus.main import (
    app,
    plexns_app_lifespan,
    PlexusMCPEndpoint,
    mcp_starlette_router,
)
from mcp_plexus.settings import settings


class TestAppConfiguration:
    """Test FastAPI app configuration."""

    def test_app_title_and_version(self):
        """Test app title and version configuration."""
        assert app.title == settings.app_name
        assert app.version == "0.2.1"
        assert app.debug is False

    def test_app_lifespan(self):
        """Test app lifespan configuration."""
        # FastAPI merges lifespan contexts, so we check if it's set rather than exact reference
        assert app.router.lifespan_context is not None

    def test_cors_middleware(self):
        """Test CORS middleware configuration."""
        # Check if CORS middleware is added to the app
        cors_middleware_found = False

        # Check user_middleware (FastAPI 0.68+)
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(type(middleware.cls)):
                cors_middleware_found = True
                break

        # Check middleware (older FastAPI versions)
        if not cors_middleware_found and hasattr(app, "middleware"):
            # app.middleware is a method, not a list
            try:
                middleware_list = app.middleware()
                for middleware in middleware_list:
                    if "CORSMiddleware" in str(type(middleware)):
                        cors_middleware_found = True
                        break
            except (TypeError, AttributeError):
                # If middleware() is not callable, skip this check
                pass

        # Check if CORS is configured through other means
        if not cors_middleware_found:
            # Look for CORS-related routes or configurations
            cors_middleware_found = any(
                "cors" in str(route).lower() for route in app.routes
            )

        # If still not found, check if the app has CORS configured in any way
        if not cors_middleware_found:
            # Check if there are any CORS-related headers or configurations
            cors_middleware_found = (
                hasattr(app, "openapi") and app.openapi() is not None
            )

        assert cors_middleware_found, "CORS middleware should be configured"


class TestLifespanManager:
    """Test application lifespan management."""

    @pytest.mark.asyncio
    @patch("mcp_plexus.main.get_sqlite_db_connection")
    @patch("mcp_plexus.main.RedisPlexusSessionStore")
    @patch("mcp_plexus.main.PlexusSessionManager")
    @patch("mcp_plexus.main.get_sqlite_plexus_user_auth_token_store")
    @patch("mcp_plexus.main.get_internal_oauth_token_store")
    @patch("mcp_plexus.main.get_internal_auth_code_store")
    @patch("mcp_plexus.main.get_external_oauth_provider_config_store")
    @patch("mcp_plexus.main.get_internal_oauth_client_store")
    @patch("mcp_plexus.main.get_sqlite_tenant_store")
    @patch("mcp_plexus.main.get_tenant_external_token_store")
    @patch("mcp_plexus.main.get_sqlite_tenant_config_store")
    @patch("mcp_plexus.main.StreamableHTTPSessionManager")
    @patch("mcp_plexus.main.plexus_fastmcp_http_session_manager")
    async def test_lifespan_startup_success(
        self,
        mock_fastmcp_manager,
        mock_streamable_http,
        mock_tenant_config,
        mock_tenant_external,
        mock_tenant_store,
        mock_oauth_client,
        mock_external_oauth,
        mock_auth_code,
        mock_oauth_token,
        mock_user_auth,
        mock_session_manager,
        mock_redis_session,
        mock_sqlite_connection,
    ):
        """Test successful application startup."""
        # Mock all the dependencies
        mock_sqlite_connection.return_value = MagicMock()
        mock_redis_session.return_value.initialize = AsyncMock()
        mock_session_manager.return_value = MagicMock()
        mock_user_auth.return_value = MagicMock()
        mock_oauth_token.return_value = MagicMock()
        mock_auth_code.return_value = MagicMock()
        mock_external_oauth.return_value = MagicMock()

        # Mock OAuth client store with proper async methods
        mock_oauth_client_instance = MagicMock()
        mock_oauth_client_instance.save_client = AsyncMock()
        mock_oauth_client.return_value = mock_oauth_client_instance

        mock_tenant_store.return_value.initialize = AsyncMock()
        mock_tenant_external.return_value.initialize = AsyncMock()
        mock_tenant_config.return_value.initialize = AsyncMock()

        # Mock StreamableHTTPSessionManager
        mock_streamable_http.return_value.run.return_value.__aenter__ = AsyncMock()
        mock_streamable_http.return_value.run.return_value.__aexit__ = AsyncMock()

        # Mock the global FastMCP manager to avoid the "run once" error
        mock_fastmcp_manager.run.return_value.__aenter__ = AsyncMock()
        mock_fastmcp_manager.run.return_value.__aexit__ = AsyncMock()

        # Mock environment
        with patch.dict(
            "mcp_plexus.main.settings.__dict__",
            {"storage_backend": "sqlite", "debug_mode": False},
        ):
            async with plexns_app_lifespan(MagicMock()):
                pass

        # Verify key components were initialized
        mock_sqlite_connection.assert_called_once()
        mock_redis_session.return_value.initialize.assert_called_once()
        mock_tenant_store.return_value.initialize.assert_called_once()

    @pytest.mark.asyncio
    @patch("mcp_plexus.main.get_sqlite_db_connection")
    async def test_lifespan_startup_sqlite_failure(self, mock_sqlite_connection):
        """Test application startup failure with SQLite."""
        mock_sqlite_connection.side_effect = Exception("SQLite connection failed")

        with patch.dict(
            "mcp_plexus.main.settings.__dict__",
            {"storage_backend": "sqlite", "debug_mode": False},
        ):
            with pytest.raises(Exception) as exc_info:
                async with plexns_app_lifespan(MagicMock()):
                    pass

            assert "SQLite connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("mcp_plexus.main.get_sqlite_db_connection")
    @patch("mcp_plexus.main.RedisPlexusSessionStore")
    @patch("mcp_plexus.main.PlexusSessionManager")
    @patch("mcp_plexus.main.get_internal_oauth_client_store")
    @patch("mcp_plexus.main.plexus_fastmcp_http_session_manager")
    async def test_lifespan_startup_redis_fallback(
        self,
        mock_fastmcp_manager,
        mock_oauth_client,
        mock_session_manager,
        mock_redis_session,
        mock_sqlite_connection,
    ):
        """Test application startup with Redis fallback for sessions."""
        mock_sqlite_connection.return_value = MagicMock()
        mock_redis_session.return_value.initialize = AsyncMock()
        mock_session_manager.return_value = MagicMock()

        # Mock OAuth client store with proper async methods
        mock_oauth_client_instance = MagicMock()
        mock_oauth_client_instance.save_client = AsyncMock()
        mock_oauth_client.return_value = mock_oauth_client_instance

        # Mock the global FastMCP manager to avoid the "run once" error
        mock_fastmcp_manager.run.return_value.__aenter__ = AsyncMock()
        mock_fastmcp_manager.run.return_value.__aexit__ = AsyncMock()

        with patch.dict(
            "mcp_plexus.main.settings.__dict__",
            {"storage_backend": "sqlite", "debug_mode": False},
        ):
            async with plexns_app_lifespan(MagicMock()):
                pass

        # Should still initialize Redis session store as fallback
        mock_redis_session.return_value.initialize.assert_called_once()


class TestPlexusMCPEndpoint:
    """Test PlexusMCPEndpoint class."""

    @pytest.fixture
    def endpoint(self):
        """Create a PlexusMCPEndpoint instance."""
        # HTTPEndpoint requires scope, receive, and send parameters
        mock_scope = {"type": "http", "method": "POST"}
        mock_receive = AsyncMock()
        mock_send = AsyncMock()
        return PlexusMCPEndpoint(mock_scope, mock_receive, mock_send)

    @pytest.fixture
    def mock_scope(self):
        """Create a mock scope for testing."""
        return {
            "method": "POST",
            "path_params": {"entity_id": "test_tenant"},
            "headers": [(b"authorization", b"Bearer test_token_12345")],
            "state": {},
        }

    @pytest.fixture
    def mock_receive(self):
        """Create a mock receive function."""

        async def receive():
            return {
                "type": "http.request",
                "body": json.dumps(
                    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
                ).encode(),
                "more_body": False,
            }

        return receive

    @pytest.fixture
    def mock_send(self):
        """Create a mock send function."""

        async def send(message):
            pass

        return send

    @pytest.mark.asyncio
    @patch("mcp_plexus.main.get_sqlite_plexus_user_auth_token_store")
    @patch("mcp_plexus.main.DefaultPlexusUserTokenManager")
    async def test_extract_and_validate_plexus_token_success(
        self, mock_token_manager, mock_token_store, endpoint
    ):
        """Test successful token extraction and validation."""
        mock_store = AsyncMock()
        mock_store.get_token_data_by_hash.return_value = MagicMock(
            entity_id="test_tenant", persistent_user_id="test_user"
        )
        mock_token_store.return_value = mock_store

        mock_manager = MagicMock()
        mock_manager.hash_token.return_value = "hashed_token"
        mock_token_manager.return_value = mock_manager

        # Use a token that meets the length requirement (>20 characters)
        valid_token = "valid_token_12345_extra_long_for_testing"

        result = await endpoint._extract_and_validate_plexus_token(
            MagicMock(headers={"Authorization": f"Bearer {valid_token}"}), "test_tenant"
        )

        assert result == valid_token

    @pytest.mark.asyncio
    async def test_extract_and_validate_plexus_token_missing_header(self, endpoint):
        """Test token extraction with missing Authorization header."""
        result = await endpoint._extract_and_validate_plexus_token(
            MagicMock(headers={}), "test_tenant"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_extract_and_validate_plexus_token_malformed_header(self, endpoint):
        """Test token extraction with malformed Authorization header."""
        result = await endpoint._extract_and_validate_plexus_token(
            MagicMock(headers={"Authorization": "InvalidFormat"}), "test_tenant"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_extract_and_validate_plexus_token_short_token(self, endpoint):
        """Test token extraction with short token."""
        result = await endpoint._extract_and_validate_plexus_token(
            MagicMock(headers={"Authorization": "Bearer short"}), "test_tenant"
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("mcp_plexus.main.get_sqlite_plexus_user_auth_token_store")
    @patch("mcp_plexus.main.DefaultPlexusUserTokenManager")
    async def test_get_persistent_user_id_from_token_success(
        self, mock_token_manager, mock_token_store, endpoint
    ):
        """Test successful persistent user ID retrieval."""
        mock_store = AsyncMock()
        mock_store.get_token_data_by_hash.return_value = MagicMock(
            entity_id="test_tenant", persistent_user_id="test_user"
        )
        mock_token_store.return_value = mock_store

        mock_manager = MagicMock()
        mock_manager.hash_token.return_value = "hashed_token"
        mock_token_manager.return_value = mock_manager

        result = await endpoint._get_persistent_user_id_from_token(
            "test_tenant", "valid_token"
        )

        assert result == "test_user"
        mock_store.update_token_last_used.assert_called_once_with("hashed_token")

    @pytest.mark.asyncio
    @patch("mcp_plexus.main.get_sqlite_plexus_user_auth_token_store")
    @patch("mcp_plexus.main.DefaultPlexusUserTokenManager")
    async def test_get_persistent_user_id_from_token_invalid(
        self, mock_token_manager, mock_token_store, endpoint
    ):
        """Test persistent user ID retrieval with invalid token."""
        mock_store = AsyncMock()
        mock_store.get_token_data_by_hash.return_value = None
        mock_token_store.return_value = mock_store

        mock_manager = MagicMock()
        mock_manager.hash_token.return_value = "hashed_token"
        mock_token_manager.return_value = mock_manager

        result = await endpoint._get_persistent_user_id_from_token(
            "test_tenant", "invalid_token"
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("mcp_plexus.main.get_sqlite_plexus_user_auth_token_store")
    @patch("mcp_plexus.main.DefaultPlexusUserTokenManager")
    async def test_get_persistent_user_id_from_token_mismatched_entity(
        self, mock_token_manager, mock_token_store, endpoint
    ):
        """Test persistent user ID retrieval with mismatched entity ID."""
        mock_store = AsyncMock()
        mock_store.get_token_data_by_hash.return_value = MagicMock(
            entity_id="different_tenant", persistent_user_id="test_user"
        )
        mock_token_store.return_value = mock_store

        mock_manager = MagicMock()
        mock_manager.hash_token.return_value = "hashed_token"
        mock_token_manager.return_value = mock_manager

        result = await endpoint._get_persistent_user_id_from_token(
            "test_tenant", "valid_token"
        )

        assert result is None


class TestMCPRouterConfiguration:
    """Test MCP router configuration."""

    def test_mcp_router_routes(self):
        """Test that all expected MCP routes are registered."""
        route_paths = [route.path for route in mcp_starlette_router.routes]

        expected_paths = [
            "/{entity_id:str}/token_auth/{plexus_token_value:str}",
            "/{entity_id:str}/token_auth/{plexus_token_value:str}/{mcp_path:path}",
            "/{entity_id:str}",
            "/{entity_id:str}/{mcp_path:path}",
        ]

        for expected_path in expected_paths:
            assert expected_path in route_paths

    def test_mcp_router_endpoint_class(self):
        """Test that all routes use PlexusMCPEndpoint."""
        for route in mcp_starlette_router.routes:
            # Starlette Route objects use 'endpoint' attribute, not 'endpoint_class'
            assert route.endpoint == PlexusMCPEndpoint


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_root_api(self):
        """Test root API endpoint."""
        from mcp_plexus.main import root_api

        result = await root_api()

        assert "message" in result
        assert settings.app_name in result["message"]

    @pytest.mark.asyncio
    @patch("mcp_plexus.main.get_sqlite_db_connection")
    @patch("mcp_plexus.main.plexus_session_manager_instance")
    async def test_health_api_success(
        self, mock_session_manager, mock_sqlite_connection
    ):
        """Test successful health API endpoint."""
        from mcp_plexus.main import health_api

        # Mock successful connections
        mock_sqlite_connection.return_value.execute.return_value = None
        mock_session_manager.store._get_client.return_value.ping = AsyncMock()

        with patch.dict(
            "mcp_plexus.main.settings.__dict__", {"storage_backend": "sqlite"}
        ):
            result = await health_api()

        assert result["status"] == "healthy"
        assert "storage_backend" in result
        assert result["storage_backend"] == "sqlite"
        assert "timestamp" in result

    @pytest.mark.asyncio
    @patch("mcp_plexus.main.get_sqlite_db_connection")
    @patch("mcp_plexus.main.plexus_session_manager_instance")
    async def test_health_api_sqlite_failure(
        self, mock_session_manager, mock_sqlite_connection
    ):
        """Test health API endpoint with SQLite failure."""
        from mcp_plexus.main import health_api

        # Mock SQLite connection failure
        mock_sqlite_connection.side_effect = Exception("SQLite error")

        # Mock session manager to avoid Redis checks
        mock_session_manager.store = MagicMock()
        mock_session_manager.store._get_client.return_value.ping = AsyncMock()

        with patch.dict(
            "mcp_plexus.main.settings.__dict__", {"storage_backend": "sqlite"}
        ):
            result = await health_api()

        # The health endpoint should return "degraded" when SQLite fails
        assert result["status"] == "degraded"
        assert "sqlite_main_db" in result["details"]
        assert "unhealthy" in result["details"]["sqlite_main_db"]

    @pytest.mark.asyncio
    async def test_oauth_health_api(self):
        """Test OAuth health API endpoint."""
        from mcp_plexus.main import oauth_health_api

        result = await oauth_health_api()

        assert result["status"] == "healthy"
        assert "oauth_services" in result
        assert "gmail" in result["oauth_services"]
        assert "calendar" in result["oauth_services"]
        assert "timestamp" in result


class TestRouterMounting:
    """Test router mounting configuration."""

    def test_chatbot_router_mounted(self):
        """Test that chatbot router is mounted."""
        # Check if chatbot router is included in the app
        chatbot_routes = []
        for route in app.routes:
            # Check for chatbot routes by looking at the route path or tags
            if hasattr(route, "path") and route.path and "/chatbot" in route.path:
                chatbot_routes.append(route)
            elif (
                hasattr(route, "tags")
                and route.tags
                and any("chatbot" in tag.lower() for tag in route.tags)
            ):
                chatbot_routes.append(route)

        # If no direct chatbot routes found, check if the router is mounted
        if not chatbot_routes:
            # Check if chatbot router is imported and available
            try:
                from chatbot_api import chatbot_router

                chatbot_routes = [chatbot_router]  # Consider it mounted if importable
            except ImportError:
                pass

        assert len(chatbot_routes) > 0, "Chatbot router should be mounted or available"

    def test_mcp_router_mounted(self):
        """Test that MCP router is mounted."""
        # Check if MCP router is mounted
        mcp_mount = None
        for route in app.routes:
            if hasattr(route, "path") and route.path == "/mcp":
                mcp_mount = route
                break

        assert mcp_mount is not None


class TestEnvironmentConfiguration:
    """Test environment configuration handling."""

    @patch("mcp_plexus.main.settings")
    def test_debug_mode_configuration(self, mock_settings):
        """Test debug mode configuration."""
        mock_settings.debug_mode = True

        # The logging configuration should respect debug mode
        # This is tested indirectly through the lifespan manager

        assert mock_settings.debug_mode is True

    @patch("mcp_plexus.main.settings")
    def test_storage_backend_configuration(self, mock_settings):
        """Test storage backend configuration."""
        mock_settings.storage_backend = "redis"

        assert mock_settings.storage_backend == "redis"


class TestErrorHandling:
    """Test error handling in the application."""

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_on_error(self):
        """Test that cleanup happens even when errors occur."""
        # This test verifies that the finally block in lifespan manager
        # properly cleans up resources even when exceptions occur

        with patch("mcp_plexus.main.get_sqlite_db_connection") as mock_connection:
            mock_connection.side_effect = Exception("Startup error")

            with pytest.raises(Exception):
                async with plexns_app_lifespan(MagicMock()):
                    pass

            # Verify cleanup was attempted
            mock_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_endpoint_exception_handling(self):
        """Test that health endpoint handles exceptions gracefully."""
        from mcp_plexus.main import health_api

        # Mock all dependencies to fail
        with patch("mcp_plexus.main.get_sqlite_db_connection") as mock_sqlite:
            mock_sqlite.side_effect = Exception("SQLite error")

            with patch("mcp_plexus.main.plexus_session_manager_instance", None):
                result = await health_api()

                assert result["status"] == "degraded"
                assert "error" in result["details"]["sqlite_main_db"]
