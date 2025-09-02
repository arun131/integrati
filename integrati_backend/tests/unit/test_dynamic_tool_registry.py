"""Unit tests for DynamicToolRegistry."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mcp_plexus.dynamic_tool_registry import (
    DynamicToolRegistry,
    get_dynamic_tool_registry,
    register_tool_with_tenant_check,
)
from mcp_plexus.oauth.unified_token_service import TenantOAuthTokenService


class TestDynamicToolRegistry:
    """Test cases for DynamicToolRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry instance for each test."""
        return DynamicToolRegistry()

    @pytest.fixture
    def mock_unified_service(self):
        """Mock unified OAuth token service."""
        service = AsyncMock(spec=TenantOAuthTokenService)
        return service

    def test_initialization(self, registry):
        """Test that the registry initializes with correct default values."""
        assert registry.registered_tools == {}
        assert "gmail" in registry.integration_tools
        assert "calendar" in registry.integration_tools
        # Should have 2 common tools: web_search and local_search
        assert len(registry.common_tools) == 2
        assert "web_search" in registry.common_tools
        assert "local_search" in registry.common_tools

    def test_integration_tools_structure(self, registry):
        """Test that integration tools are properly structured."""
        gmail_tools = registry.integration_tools["gmail"]
        calendar_tools = registry.integration_tools["calendar"]

        assert "search_emails" in gmail_tools
        assert "send_gmail_message" in gmail_tools
        assert "get_events" in calendar_tools
        assert "create_event" in calendar_tools

    def test_common_tools_list(self, registry):
        """Test that common tools are properly defined."""
        expected_common_tools = ["web_search", "local_search"]

        for tool in expected_common_tools:
            assert tool in registry.common_tools

    @pytest.mark.asyncio
    async def test_get_tenant_integrations_success(
        self, registry, mock_unified_service
    ):
        """Test getting tenant integrations successfully."""
        # Mock token data for gmail and calendar
        mock_unified_service.get_oauth_tokens.side_effect = [
            {"access_token": "gmail_token"},  # gmail
            {"access_token": "calendar_token"},  # calendar
        ]

        with patch(
            "mcp_plexus.dynamic_tool_registry.get_unified_oauth_token_service",
            return_value=mock_unified_service,
        ):
            result = await registry.get_tenant_integrations("tenant_123", "user_456")

        assert result == ["gmail", "calendar"]
        assert mock_unified_service.get_oauth_tokens.call_count == 2

    @pytest.mark.asyncio
    async def test_get_tenant_integrations_partial_connection(
        self, registry, mock_unified_service
    ):
        """Test getting tenant integrations with only some connected."""
        # Mock token data - only gmail connected
        mock_unified_service.get_oauth_tokens.side_effect = [
            {"access_token": "gmail_token"},  # gmail
            None,  # calendar not connected
        ]

        with patch(
            "mcp_plexus.dynamic_tool_registry.get_unified_oauth_token_service",
            return_value=mock_unified_service,
        ):
            result = await registry.get_tenant_integrations("tenant_123", "user_456")

        assert result == ["gmail"]

    @pytest.mark.asyncio
    async def test_get_tenant_integrations_no_connections(
        self, registry, mock_unified_service
    ):
        """Test getting tenant integrations when none are connected."""
        # Mock no token data
        mock_unified_service.get_oauth_tokens.return_value = None

        with patch(
            "mcp_plexus.dynamic_tool_registry.get_unified_oauth_token_service",
            return_value=mock_unified_service,
        ):
            result = await registry.get_tenant_integrations("tenant_123", "user_456")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_tenant_integrations_exception_handling(
        self, registry, mock_unified_service
    ):
        """Test that exceptions are handled gracefully."""
        mock_unified_service.get_oauth_tokens.side_effect = Exception("Service error")

        with patch(
            "mcp_plexus.dynamic_tool_registry.get_unified_oauth_token_service",
            return_value=mock_unified_service,
        ):
            result = await registry.get_tenant_integrations("tenant_123", "user_456")

        assert result == []

    def test_get_available_tools_common_only(self, registry):
        """Test getting available tools when only common tools are available."""
        connected_integrations = []
        result = registry.get_available_tools(
            "tenant_123", "user_456", connected_integrations
        )

        assert result == registry.common_tools
        assert len(result) == 2
        assert "web_search" in result
        assert "local_search" in result

    def test_get_available_tools_with_gmail(self, registry):
        """Test getting available tools when Gmail is connected."""
        connected_integrations = ["gmail"]
        result = registry.get_available_tools(
            "tenant_123", "user_456", connected_integrations
        )

        # Should include common tools + gmail tools
        expected_tools = registry.common_tools + registry.integration_tools["gmail"]
        assert result == expected_tools
        assert "search_emails" in result
        assert "send_gmail_message" in result

    def test_get_available_tools_with_calendar(self, registry):
        """Test getting available tools when Calendar is connected."""
        connected_integrations = ["calendar"]
        result = registry.get_available_tools(
            "tenant_123", "user_456", connected_integrations
        )

        # Should include common tools + calendar tools
        expected_tools = registry.common_tools + registry.integration_tools["calendar"]
        assert result == expected_tools
        assert "get_events" in result
        assert "create_event" in result

    def test_get_available_tools_with_multiple_integrations(self, registry):
        """Test getting available tools when multiple integrations are connected."""
        connected_integrations = ["gmail", "calendar"]
        result = registry.get_available_tools(
            "tenant_123", "user_456", connected_integrations
        )

        # Should include common tools + gmail tools + calendar tools
        expected_tools = (
            registry.common_tools
            + registry.integration_tools["gmail"]
            + registry.integration_tools["calendar"]
        )
        assert result == expected_tools
        assert "search_emails" in result
        assert "get_events" in result

    def test_get_available_tools_unknown_integration(self, registry):
        """Test getting available tools with unknown integration."""
        connected_integrations = ["unknown_integration"]
        result = registry.get_available_tools(
            "tenant_123", "user_456", connected_integrations
        )

        # Should only include common tools
        assert result == registry.common_tools

    @pytest.mark.asyncio
    async def test_register_tools_for_tenant_success(
        self, registry, mock_unified_service
    ):
        """Test registering tools for a tenant successfully."""
        # Mock connected integrations
        mock_unified_service.get_oauth_tokens.side_effect = [
            {"access_token": "gmail_token"},  # gmail
            None,  # calendar not connected
        ]

        with patch(
            "mcp_plexus.dynamic_tool_registry.get_unified_oauth_token_service",
            return_value=mock_unified_service,
        ):
            result = await registry.register_tools_for_tenant("tenant_123", "user_456")

        # Should include common tools + gmail tools
        expected_tools = registry.common_tools + registry.integration_tools["gmail"]
        assert result == expected_tools

        # Check that tools are stored in registry
        tenant_key = "tenant_123:user_456"
        assert tenant_key in registry.registered_tools
        assert registry.registered_tools[tenant_key]["integrations"] == ["gmail"]
        assert registry.registered_tools[tenant_key]["tools"] == expected_tools

    @pytest.mark.asyncio
    async def test_register_tools_for_tenant_exception_fallback(
        self, registry, mock_unified_service
    ):
        """Test that exceptions during registration fall back to common tools."""
        mock_unified_service.get_oauth_tokens.side_effect = Exception("Service error")

        with patch(
            "mcp_plexus.dynamic_tool_registry.get_unified_oauth_token_service",
            return_value=mock_unified_service,
        ):
            result = await registry.register_tools_for_tenant("tenant_123", "user_456")

        assert result == registry.common_tools

    def test_get_tenant_tools_registered(self, registry):
        """Test getting registered tools for a tenant."""
        # Pre-populate registry
        tenant_key = "tenant_123:user_456"
        registry.registered_tools[tenant_key] = {
            "integrations": ["gmail"],
            "tools": ["tool1", "tool2", "tool3"],
        }

        result = registry.get_tenant_tools("tenant_123", "user_456")
        assert result == ["tool1", "tool2", "tool3"]

    def test_get_tenant_tools_not_registered(self, registry):
        """Test getting tools for a tenant that hasn't been registered."""
        result = registry.get_tenant_tools("tenant_123", "user_456")
        assert result == registry.common_tools

    def test_is_tool_available_true(self, registry):
        """Test checking if a tool is available when it is."""
        # Pre-populate registry
        tenant_key = "tenant_123:user_456"
        registry.registered_tools[tenant_key] = {
            "integrations": ["gmail"],
            "tools": ["search_emails"] + registry.common_tools,
        }

        assert (
            registry.is_tool_available("tenant_123", "user_456", "search_emails")
            is True
        )
        # Should have common tools available
        assert (
            registry.is_tool_available("tenant_123", "user_456", "web_search") is True
        )
        assert (
            registry.is_tool_available("tenant_123", "user_456", "local_search") is True
        )

    def test_is_tool_available_false(self, registry):
        """Test checking if a tool is available when it isn't."""
        # Pre-populate registry
        tenant_key = "tenant_123:user_456"
        registry.registered_tools[tenant_key] = {
            "integrations": ["gmail"],
            "tools": ["search_emails"],
        }

        assert (
            registry.is_tool_available("tenant_123", "user_456", "unknown_tool")
            is False
        )

    def test_is_tool_available_not_registered(self, registry):
        """Test checking tool availability for unregistered tenant."""
        # Should fall back to common tools
        # Should have common tools available
        assert (
            registry.is_tool_available("tenant_123", "user_456", "web_search") is True
        )
        assert (
            registry.is_tool_available("tenant_123", "user_456", "local_search") is True
        )
        assert (
            registry.is_tool_available("tenant_123", "user_456", "unknown_tool")
            is False
        )


class TestDynamicToolRegistryGlobal:
    """Test cases for global registry functionality."""

    @pytest.mark.asyncio
    async def test_get_dynamic_tool_registry_singleton(self):
        """Test that get_dynamic_tool_registry returns a singleton."""
        registry1 = await get_dynamic_tool_registry()
        registry2 = await get_dynamic_tool_registry()

        assert registry1 is registry2
        assert isinstance(registry1, DynamicToolRegistry)


class TestRegisterToolWithTenantCheck:
    """Test cases for the register_tool_with_tenant_check decorator."""

    def test_register_tool_with_tenant_check_decorator(self):
        """Test the decorator function."""
        # Mock PLEXUS_SERVER_INSTANCE
        mock_server = MagicMock()
        mock_tool_decorator = MagicMock()
        mock_server.tool.return_value = mock_tool_decorator

        with patch(
            "mcp_plexus.dynamic_tool_registry.PLEXUS_SERVER_INSTANCE", mock_server
        ):
            decorator = register_tool_with_tenant_check("test_tool")

            # Test that decorator returns a function
            assert callable(decorator)

            # Test that it calls the server's tool method when applied to a function
            def test_func():
                pass

            _ = decorator(test_func)

            # The tool method should be called when the decorator is applied
            mock_server.tool.assert_called_once()

    def test_register_tool_with_tenant_check_no_server(self):
        """Test decorator when PLEXUS_SERVER_INSTANCE is None."""
        with patch("mcp_plexus.dynamic_tool_registry.PLEXUS_SERVER_INSTANCE", None):
            decorator = register_tool_with_tenant_check("test_tool")

            # Should still return a callable decorator
            assert callable(decorator)
