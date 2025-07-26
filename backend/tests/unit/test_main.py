from fastapi.testclient import TestClient
import pytest

from app.main import app


class TestMainApp:
    """Test cases for main application"""

    def test_read_root(self, client):
        """Test the root endpoint"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Welcome to the Gmail & Calendar Manager Backend MVP!"

    def test_app_title(self):
        """Test that the app has the correct title"""
        assert app.title == "Gmail & Calendar Manager Backend MVP"

    def test_app_version(self):
        """Test that the app has the correct version"""
        assert app.version == "0.1.0"

    def test_app_description(self):
        """Test that the app has the correct description"""
        assert (
            "FastAPI backend for managing Gmail and Calendar interactions"
            in app.description
        )

    def test_cors_middleware(self):
        """Test that CORS middleware is configured"""
        # Check that CORS middleware is in the middleware stack
        middleware_found = False
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                middleware_found = True
                break

        assert middleware_found, "CORS middleware should be configured"

    def test_routers_included(self):
        """Test that all required routers are included"""
        # Check that all expected routers are included
        router_paths = [
            "/api/auth",
            "/integrations/gmail/api",
            "/integrations/gmail/auth",
            "/integrations/calendar/api",
            "/integrations/calendar/auth",
            "/api/integration",
        ]

        for router_path in router_paths:
            # Check if any route starts with this path
            routes_found = False
            for route in app.routes:
                if (
                    hasattr(route, "prefix")
                    and route.prefix == router_path
                    or hasattr(route, "path")
                    and route.path.startswith(router_path)
                ):
                    routes_found = True
                    break

            assert routes_found, f"Router for {router_path} should be included"

    def test_health_check_endpoint(self, client):
        """Test that the health check endpoint returns 200"""
        response = client.get("/")
        assert response.status_code == 200

    def test_404_for_unknown_endpoint(self, client):
        """Test that unknown endpoints return 404"""
        response = client.get("/unknown-endpoint")
        assert response.status_code == 404
