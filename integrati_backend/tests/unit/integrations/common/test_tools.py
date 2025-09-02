"""Unit tests for common integration tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastmcp.exceptions import ToolError

from integrations.common.tools import CommonTools


class TestCommonToolsWebSearch:
    """Test web_search tool functionality."""

    @pytest.mark.asyncio
    @patch("integrations.common.tools.PermissionHelper.check_and_handle_permissions")
    @patch("integrations.common.tools.GoogleSearchAPI")
    @patch("integrations.common.tools.PlexusContext")
    async def test_web_search_full_access_success(
        self, mock_plexus_context_class, mock_search_api_class, mock_permission_helper
    ):
        """Test successful web search with full access."""
        # Setup PlexusContext mock
        mock_plexus_ctx = MagicMock()
        mock_plexus_ctx.entity_id = "test_entity_123"
        mock_plexus_ctx.user_id = "test_user_123"
        mock_plexus_context_class.return_value = mock_plexus_ctx

        # Mock FastMCP context
        mock_ctx = MagicMock()
        mock_ctx.fastmcp = MagicMock()

        # Setup PermissionHelper mock
        mock_permission_helper.return_value = None

        # Setup GoogleSearchAPI mock
        mock_search_api = MagicMock()
        mock_search_api.web_search = AsyncMock(
            return_value=[
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "snippet": "Test snippet",
                }
            ]
        )
        mock_search_api_class.return_value = mock_search_api

        # Execute
        result = await CommonTools.web_search(
            ctx=mock_ctx, query="test query", num_results=5, location="New York"
        )

        # Assertions
        assert result["status"] == "success"
        assert result["status_message"] == "success"
        assert result["total_results"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Test Result"

        # Verify API calls
        mock_permission_helper.assert_called_once()
        mock_search_api.web_search.assert_called_once_with(
            "test query in New York", 5, "New York"
        )

    @pytest.mark.asyncio
    @patch("integrations.common.tools.PermissionHelper.check_and_handle_permissions")
    @patch("integrations.common.tools.PlexusContext")
    async def test_web_search_no_access(
        self, mock_plexus_context_class, mock_permission_helper
    ):
        """Test web search with no access permission."""
        # Setup PlexusContext mock
        mock_plexus_ctx = MagicMock()
        mock_plexus_ctx.entity_id = "test_entity_123"
        mock_plexus_ctx.user_id = "test_user_123"
        mock_plexus_context_class.return_value = mock_plexus_ctx

        # Mock FastMCP context
        mock_ctx = MagicMock()
        mock_ctx.fastmcp = MagicMock()

        # Setup mock to return no access response
        no_access_response = {
            "results": [],
            "total_results": 0,
            "status": "access_denied",
            "status_message": "You don't have permission to use web search tools with this configuration.",
        }
        mock_permission_helper.return_value = no_access_response

        # Execute
        result = await CommonTools.web_search(ctx=mock_ctx, query="test query")

        # Assertions
        assert result == no_access_response
        mock_permission_helper.assert_called_once()

    @pytest.mark.asyncio
    @patch("integrations.common.tools.PermissionHelper.check_and_handle_permissions")
    @patch("integrations.common.tools.PlexusContext")
    async def test_web_search_restricted_access(
        self, mock_plexus_context_class, mock_permission_helper
    ):
        """Test web search with restricted access permission."""
        # Setup PlexusContext mock
        mock_plexus_ctx = MagicMock()
        mock_plexus_ctx.entity_id = "test_entity_123"
        mock_plexus_ctx.user_id = "test_user_123"
        mock_plexus_context_class.return_value = mock_plexus_ctx

        # Mock FastMCP context
        mock_ctx = MagicMock()
        mock_ctx.fastmcp = MagicMock()

        # Setup mock to return restricted access response
        restricted_response = {
            "results": [],
            "total_results": 0,
            "status": "approval_required",
            "status_message": "Your request to search the web for 'test query' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
        }
        mock_permission_helper.return_value = restricted_response

        # Execute
        result = await CommonTools.web_search(ctx=mock_ctx, query="test query")

        # Assertions
        assert result == restricted_response
        mock_permission_helper.assert_called_once()

    @pytest.mark.asyncio
    @patch("integrations.common.tools.PlexusContext")
    async def test_web_search_no_user_id(self, mock_plexus_context_class):
        """Test web search with missing user ID."""
        # Mock FastMCP context
        mock_ctx = MagicMock()
        mock_ctx.fastmcp = MagicMock()

        # Setup PlexusContext mock with no user_id
        mock_plexus_ctx = MagicMock()
        mock_plexus_ctx.entity_id = "test_entity_123"
        mock_plexus_ctx.user_id = None
        mock_plexus_context_class.return_value = mock_plexus_ctx

        # Execute and expect ToolError
        with pytest.raises(ToolError, match="User ID not available in context"):
            await CommonTools.web_search(ctx=mock_ctx, query="test query")

    @pytest.mark.asyncio
    @patch("integrations.common.tools.PermissionHelper.check_and_handle_permissions")
    @patch("integrations.common.tools.GoogleSearchAPI")
    @patch("integrations.common.tools.PlexusContext")
    async def test_web_search_api_error(
        self, mock_plexus_context_class, mock_search_api_class, mock_permission_helper
    ):
        """Test web search with API error."""
        # Setup PlexusContext mock
        mock_plexus_ctx = MagicMock()
        mock_plexus_ctx.entity_id = "test_entity_123"
        mock_plexus_ctx.user_id = "test_user_123"
        mock_plexus_context_class.return_value = mock_plexus_ctx

        # Mock FastMCP context
        mock_ctx = MagicMock()
        mock_ctx.fastmcp = MagicMock()

        # Setup PermissionHelper mock
        mock_permission_helper.return_value = None

        # Setup GoogleSearchAPI mock with error
        mock_search_api = MagicMock()
        mock_search_api.web_search = AsyncMock(side_effect=Exception("API Error"))
        mock_search_api_class.return_value = mock_search_api

        # Execute and expect ToolError
        with pytest.raises(ToolError, match="Error performing web search: API Error"):
            await CommonTools.web_search(ctx=mock_ctx, query="test query")

    @pytest.mark.asyncio
    @patch("integrations.common.tools.PermissionHelper.check_and_handle_permissions")
    @patch("integrations.common.tools.GoogleSearchAPI")
    @patch("integrations.common.tools.PlexusContext")
    async def test_web_search_empty_results(
        self, mock_plexus_context_class, mock_search_api_class, mock_permission_helper
    ):
        """Test web search with empty results."""
        # Setup PlexusContext mock
        mock_plexus_ctx = MagicMock()
        mock_plexus_ctx.entity_id = "test_entity_123"
        mock_plexus_ctx.user_id = "test_user_123"
        mock_plexus_context_class.return_value = mock_plexus_ctx

        # Mock FastMCP context
        mock_ctx = MagicMock()
        mock_ctx.fastmcp = MagicMock()

        # Setup PermissionHelper mock
        mock_permission_helper.return_value = None

        # Setup GoogleSearchAPI mock with empty results
        mock_search_api = MagicMock()
        mock_search_api.web_search = AsyncMock(return_value=[])
        mock_search_api_class.return_value = mock_search_api

        # Execute
        result = await CommonTools.web_search(ctx=mock_ctx, query="test query")

        # Assertions
        assert result["status"] == "success"
        assert result["total_results"] == 0
        assert result["results"] == []


class TestCommonToolsLocalSearch:
    """Test local_search tool functionality."""

    @pytest.mark.asyncio
    @patch("integrations.common.tools.PermissionHelper.check_and_handle_permissions")
    @patch("integrations.common.tools.GoogleSearchAPI")
    @patch("integrations.common.tools.PlexusContext")
    async def test_local_search_full_access_success(
        self, mock_plexus_context_class, mock_search_api_class, mock_permission_helper
    ):
        """Test successful local search with full access."""
        # Setup PlexusContext mock
        mock_plexus_ctx = MagicMock()
        mock_plexus_ctx.entity_id = "test_entity_123"
        mock_plexus_ctx.user_id = "test_user_123"
        mock_plexus_context_class.return_value = mock_plexus_ctx

        # Mock FastMCP context
        mock_ctx = MagicMock()
        mock_ctx.fastmcp = MagicMock()

        # Setup PermissionHelper mock
        mock_permission_helper.return_value = None

        # Setup GoogleSearchAPI mock
        mock_search_api = MagicMock()
        mock_search_api.local_search = AsyncMock(
            return_value=[
                {
                    "name": "Test Restaurant",
                    "address": "123 Main St",
                    "rating": 4.5,
                    "business_status": "OPERATIONAL",
                }
            ]
        )
        mock_search_api_class.return_value = mock_search_api

        # Execute
        result = await CommonTools.local_search(
            ctx=mock_ctx,
            query="restaurants near me",
            location="New York",
            num_results=3,
        )

        # Assertions
        assert result["status"] == "success"
        assert result["status_message"] == "success"
        assert result["total_results"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "Test Restaurant"

        # Verify API calls
        mock_permission_helper.assert_called_once()
        mock_search_api.local_search.assert_called_once_with(
            "restaurants near me in New York", "New York", 3
        )

    @pytest.mark.asyncio
    @patch("integrations.common.tools.PermissionHelper.check_and_handle_permissions")
    @patch("integrations.common.tools.PlexusContext")
    async def test_local_search_no_access(
        self, mock_plexus_context_class, mock_permission_helper
    ):
        """Test local search with no access permission."""
        # Setup PlexusContext mock
        mock_plexus_ctx = MagicMock()
        mock_plexus_ctx.entity_id = "test_entity_123"
        mock_plexus_ctx.user_id = "test_user_123"
        mock_plexus_context_class.return_value = mock_plexus_ctx

        # Mock FastMCP context
        mock_ctx = MagicMock()
        mock_ctx.fastmcp = MagicMock()

        # Setup mock to return no access response
        no_access_response = {
            "results": [],
            "total_results": 0,
            "status": "access_denied",
            "status_message": "You don't have permission to use local search tools with this configuration.",
        }
        mock_permission_helper.return_value = no_access_response

        # Execute
        result = await CommonTools.local_search(ctx=mock_ctx, query="restaurants")

        # Assertions
        assert result == no_access_response

    @pytest.mark.asyncio
    @patch("integrations.common.tools.PlexusContext")
    async def test_local_search_no_user_id(self, mock_plexus_context_class):
        """Test local search with missing user ID."""
        # Setup PlexusContext mock with no user_id
        mock_plexus_ctx = MagicMock()
        mock_plexus_ctx.entity_id = "test_entity_123"
        mock_plexus_ctx.user_id = None
        mock_plexus_context_class.return_value = mock_plexus_ctx

        # Mock FastMCP context
        mock_ctx = MagicMock()
        mock_ctx.fastmcp = MagicMock()

        # Execute and expect ToolError
        with pytest.raises(ToolError, match="User ID not available in context"):
            await CommonTools.local_search(ctx=mock_ctx, query="restaurants")

    @pytest.mark.asyncio
    @patch("integrations.common.tools.PermissionHelper.check_and_handle_permissions")
    @patch("integrations.common.tools.GoogleSearchAPI")
    @patch("integrations.common.tools.PlexusContext")
    async def test_local_search_api_error(
        self, mock_plexus_context_class, mock_search_api_class, mock_permission_helper
    ):
        """Test local search with API error."""
        # Setup PlexusContext mock
        mock_plexus_ctx = MagicMock()
        mock_plexus_ctx.entity_id = "test_entity_123"
        mock_plexus_ctx.user_id = "test_user_123"
        mock_plexus_context_class.return_value = mock_plexus_ctx

        # Mock FastMCP context
        mock_ctx = MagicMock()
        mock_ctx.fastmcp = MagicMock()

        # Setup PermissionHelper mock
        mock_permission_helper.return_value = None

        # Setup GoogleSearchAPI mock with error
        mock_search_api = MagicMock()
        mock_search_api.local_search = AsyncMock(
            side_effect=Exception("Places API Error")
        )
        mock_search_api_class.return_value = mock_search_api

        # Execute and expect ToolError
        with pytest.raises(
            ToolError, match="Error performing local search: Places API Error"
        ):
            await CommonTools.local_search(ctx=mock_ctx, query="restaurants")

    @pytest.mark.asyncio
    @patch("integrations.common.tools.PermissionHelper.check_and_handle_permissions")
    @patch("integrations.common.tools.GoogleSearchAPI")
    @patch("integrations.common.tools.PlexusContext")
    async def test_local_search_empty_results(
        self, mock_plexus_context_class, mock_search_api_class, mock_permission_helper
    ):
        """Test local search with empty results."""
        # Setup PlexusContext mock
        mock_plexus_ctx = MagicMock()
        mock_plexus_ctx.entity_id = "test_entity_123"
        mock_plexus_ctx.user_id = "test_user_123"
        mock_plexus_context_class.return_value = mock_plexus_ctx

        # Mock FastMCP context
        mock_ctx = MagicMock()
        mock_ctx.fastmcp = MagicMock()

        # Setup PermissionHelper mock
        mock_permission_helper.return_value = None

        # Setup GoogleSearchAPI mock with empty results
        mock_search_api = MagicMock()
        mock_search_api.local_search = AsyncMock(return_value=[])
        mock_search_api_class.return_value = mock_search_api

        # Execute
        result = await CommonTools.local_search(ctx=mock_ctx, query="restaurants")

        # Assertions
        assert result["status"] == "success"
        assert result["total_results"] == 0
        assert result["results"] == []
