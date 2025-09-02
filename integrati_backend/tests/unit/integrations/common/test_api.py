"""Unit tests for Google Search API wrapper."""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from googleapiclient.errors import HttpError
from httpx import TimeoutException, HTTPStatusError

from integrations.common.api import GoogleSearchAPI


class TestGoogleSearchAPI:
    """Test GoogleSearchAPI functionality."""

    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for testing."""
        env_vars = {
            "GOOGLE_API_KEY": "test_api_key_123",
            "GOOGLE_CSE_ID": "test_cse_id_456",
            "GOOGLE_PLACES_API_KEY": "test_places_key_789",
            "GOOGLE_DIRECTIONS_API_KEY": "test_directions_key_101",
        }
        with patch.dict(os.environ, env_vars):
            yield env_vars

    @pytest.fixture
    def search_api(self, mock_env_vars):
        """Create GoogleSearchAPI instance with mocked environment."""
        return GoogleSearchAPI()

    def test_init_success(self, mock_env_vars):
        """Test successful initialization."""
        api = GoogleSearchAPI()

        assert api.google_api_key == "test_api_key_123"
        assert api.google_cse_id == "test_cse_id_456"
        assert api.google_places_api_key == "test_places_key_789"
        assert api.google_directions_api_key == "test_directions_key_101"

    def test_init_missing_api_key(self):
        """Test initialization with missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="GOOGLE_API_KEY environment variable is required"
            ):
                GoogleSearchAPI()

    def test_init_missing_cse_id(self):
        """Test initialization with missing CSE ID."""
        env_vars = {"GOOGLE_API_KEY": "test_key"}
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(
                ValueError, match="GOOGLE_CSE_ID environment variable is required"
            ):
                GoogleSearchAPI()

    def test_init_missing_places_key(self):
        """Test initialization with missing Places API key."""
        env_vars = {"GOOGLE_API_KEY": "test_key", "GOOGLE_CSE_ID": "test_cse"}
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(
                ValueError,
                match="GOOGLE_PLACES_API_KEY environment variable is required",
            ):
                GoogleSearchAPI()

    @patch("integrations.common.api.build")
    def test_get_custom_search_service(self, mock_build, search_api):
        """Test getting custom search service instance."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # First call should create service
        service1 = search_api._get_custom_search_service()
        assert service1 == mock_service
        mock_build.assert_called_once_with(
            "customsearch", "v1", developerKey="test_api_key_123"
        )

        # Second call should return cached service
        mock_build.reset_mock()
        service2 = search_api._get_custom_search_service()
        assert service2 == mock_service
        mock_build.assert_not_called()  # Should not be called again

    @patch("integrations.common.api.build")
    @pytest.mark.asyncio
    async def test_web_search_success(self, mock_build, search_api):
        """Test successful web search."""
        # Mock the service and response
        mock_service = MagicMock()
        mock_cse = MagicMock()
        mock_list = MagicMock()

        mock_service.cse.return_value = mock_cse
        mock_cse.list.return_value = mock_list

        # Mock response data
        mock_list.execute.return_value = {
            "items": [
                {
                    "title": "Test Result 1",
                    "link": "https://example1.com",
                    "snippet": "This is test result 1",
                    "displayLink": "example1.com",
                    "formattedUrl": "https://example1.com/test",
                },
                {
                    "title": "Test Result 2",
                    "link": "https://example2.com",
                    "snippet": "This is test result 2",
                    "displayLink": "example2.com",
                    "formattedUrl": "https://example2.com/test",
                },
            ]
        }

        mock_build.return_value = mock_service

        # Execute search
        results = await search_api.web_search("test query", 5, "New York")

        # Assertions
        assert len(results) == 2
        assert results[0]["title"] == "Test Result 1"
        assert results[0]["url"] == "https://example1.com"
        assert results[0]["snippet"] == "This is test result 1"
        assert results[1]["title"] == "Test Result 2"

        # Verify API call
        mock_cse.list.assert_called_once_with(
            q="test query in New York", cx="test_cse_id_456", num=5
        )

    @patch("integrations.common.api.build")
    @pytest.mark.asyncio
    async def test_web_search_no_location(self, mock_build, search_api):
        """Test web search without location parameter."""
        mock_service = MagicMock()
        mock_cse = MagicMock()
        mock_list = MagicMock()
        mock_execute = MagicMock()

        mock_service.cse.return_value = mock_cse
        mock_cse.list.return_value = mock_list
        mock_list.execute.return_value = mock_execute
        mock_execute.return_value = {"items": []}

        mock_build.return_value = mock_service

        # Execute search without location
        _results = await search_api.web_search("test query", 10)

        # Verify query doesn't include location
        mock_cse.list.assert_called_once_with(
            q="test query", cx="test_cse_id_456", num=10
        )

    @patch("integrations.common.api.build")
    @pytest.mark.asyncio
    async def test_web_search_empty_results(self, mock_build, search_api):
        """Test web search with empty results."""
        mock_service = MagicMock()
        mock_cse = MagicMock()
        mock_list = MagicMock()
        mock_execute = MagicMock()

        mock_service.cse.return_value = mock_cse
        mock_cse.list.return_value = mock_list
        mock_list.execute.return_value = mock_execute
        mock_execute.return_value = {"items": []}  # No results

        mock_build.return_value = mock_service

        results = await search_api.web_search("test query")

        assert results == []

    @patch("integrations.common.api.build")
    @pytest.mark.asyncio
    async def test_web_search_api_error(self, mock_build, search_api):
        """Test web search with API error."""
        mock_service = MagicMock()
        mock_cse = MagicMock()
        mock_list = MagicMock()

        mock_service.cse.return_value = mock_cse
        mock_cse.list.return_value = mock_list
        mock_list.execute.side_effect = HttpError(
            resp=MagicMock(status=403), content=b'{"error": "API key invalid"}'
        )

        mock_build.return_value = mock_service

        with pytest.raises(Exception, match="Google Search API error"):
            await search_api.web_search("test query")

    @patch("integrations.common.api.build")
    @pytest.mark.asyncio
    async def test_web_search_generic_error(self, mock_build, search_api):
        """Test web search with generic error."""
        mock_service = MagicMock()
        mock_cse = MagicMock()
        mock_list = MagicMock()

        mock_service.cse.return_value = mock_cse
        mock_cse.list.return_value = mock_list
        mock_list.execute.side_effect = Exception("Network error")

        mock_build.return_value = mock_service

        with pytest.raises(Exception, match="Web search failed: Network error"):
            await search_api.web_search("test query")

    @patch("integrations.common.api.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_local_search_success(self, mock_client_class, search_api):
        """Test successful local search."""
        # Mock httpx client
        mock_client = AsyncMock()

        # Create mock response with json method
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "status": "OK",
                "results": [
                    {
                        "name": "Test Restaurant",
                        "formatted_address": "123 Main St, New York, NY",
                        "rating": 4.5,
                        "price_level": 2,
                        "user_ratings_total": 150,
                        "business_status": "OPERATIONAL",
                        "types": ["restaurant", "food"],
                        "place_id": "ChIJ123456789",
                        "geometry": {"location": {"lat": 40.7128, "lng": -74.0060}},
                        "photos": [
                            {
                                "photo_reference": "photo_ref_1",
                                "width": 800,
                                "height": 600,
                            }
                        ],
                    }
                ],
            }
        )

        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        # Execute search
        results = await search_api.local_search("restaurants", "New York", 5)

        # Assertions
        assert len(results) == 1
        result = results[0]
        assert result["name"] == "Test Restaurant"
        assert result["address"] == "123 Main St, New York, NY"
        assert result["rating"] == 4.5
        assert result["price_level"] == 2
        assert result["business_status"] == "OPERATIONAL"
        assert result["location"]["lat"] == 40.7128
        assert result["location"]["lng"] == -74.0060
        assert len(result["photos"]) == 1

        # Verify HTTP call
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "restaurants in New York" in call_args[1]["params"]["query"]
        assert call_args[1]["params"]["key"] == "test_places_key_789"

    @patch("integrations.common.api.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_local_search_no_location(self, mock_client_class, search_api):
        """Test local search without location parameter."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"status": "OK", "results": []})

        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        # Execute search without location
        _results = await search_api.local_search("restaurants")

        # Verify query doesn't include location
        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["query"] == "restaurants"

    @patch("integrations.common.api.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_local_search_api_error_status(self, mock_client_class, search_api):
        """Test local search with API error status."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(
            return_value={"status": "REQUEST_DENIED", "results": []}
        )

        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        results = await search_api.local_search("restaurants")

        # Should return empty results for non-OK status
        assert results == []

    @patch("integrations.common.api.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_local_search_http_error(self, mock_client_class, search_api):
        """Test local search with HTTP error."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPStatusError(
            "403 Forbidden", request=MagicMock(), response=MagicMock(status_code=403)
        )

        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        with pytest.raises(Exception, match="Places API error: 403"):
            await search_api.local_search("restaurants")

    @patch("integrations.common.api.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_local_search_timeout(self, mock_client_class, search_api):
        """Test local search with timeout."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = TimeoutException("Request timed out")

        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        with pytest.raises(Exception, match="Local search request timed out"):
            await search_api.local_search("restaurants")
