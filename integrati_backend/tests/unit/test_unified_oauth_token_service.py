"""Unit tests for TenantOAuthTokenService."""

import pytest
from unittest.mock import AsyncMock, patch

from mcp_plexus.oauth.unified_token_service import (
    TenantOAuthTokenService,
    get_tenant_oauth_token_service,
    get_unified_oauth_token_service,  # Backward compatibility alias
)
from mcp_plexus.oauth.storage_interfaces import (
    AbstractTenantExternalTokenStore,
)


class TestTenantOAuthTokenService:
    """Test cases for TenantOAuthTokenService."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance for each test."""
        return TenantOAuthTokenService()

    @pytest.fixture
    def mock_tenant_store(self):
        """Mock tenant token store."""
        store = AsyncMock(spec=AbstractTenantExternalTokenStore)
        return store

    @pytest.mark.asyncio
    async def test_get_oauth_tokens_success(self, service, mock_tenant_store):
        """Test getting OAuth tokens from tenant-level storage successfully."""
        # Mock tenant-level tokens
        mock_tenant_store.load_tenant_external_token.return_value = {
            "access_token": "tenant_token",
            "refresh_token": "tenant_refresh",
        }

        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.get_oauth_tokens("tenant_123", "user_456", "gmail")

        assert result == {
            "access_token": "tenant_token",
            "refresh_token": "tenant_refresh",
        }
        mock_tenant_store.load_tenant_external_token.assert_called_once_with(
            "tenant_123", "gmail"
        )

    @pytest.mark.asyncio
    async def test_get_oauth_tokens_no_tokens_found(self, service, mock_tenant_store):
        """Test getting OAuth tokens when no tokens are found."""
        # Mock no tokens in tenant store
        mock_tenant_store.load_tenant_external_token.return_value = None

        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.get_oauth_tokens("tenant_123", "user_456", "gmail")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_oauth_tokens_exception_handling(
        self, service, mock_tenant_store
    ):
        """Test that exceptions are handled gracefully."""
        mock_tenant_store.load_tenant_external_token.side_effect = Exception(
            "Storage error"
        )

        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.get_oauth_tokens("tenant_123", "user_456", "gmail")

        assert result is None

    @pytest.mark.asyncio
    async def test_save_oauth_tokens_success(self, service, mock_tenant_store):
        """Test saving OAuth tokens to tenant-level storage."""
        token_data = {"access_token": "new_token", "refresh_token": "new_refresh"}

        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.save_oauth_tokens(
                "tenant_123", "user_456", "gmail", token_data
            )

        assert result is True
        mock_tenant_store.save_tenant_external_token.assert_called_once_with(
            "tenant_123", "gmail", token_data
        )

    @pytest.mark.asyncio
    async def test_save_oauth_tokens_exception_handling(
        self, service, mock_tenant_store
    ):
        """Test that save exceptions are handled gracefully."""
        mock_tenant_store.save_tenant_external_token.side_effect = Exception(
            "Save error"
        )

        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.save_oauth_tokens(
                "tenant_123",
                "user_456",
                "gmail",
                {"token": "data"},
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_oauth_tokens_success(self, service, mock_tenant_store):
        """Test deleting OAuth tokens from tenant-level storage."""
        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.delete_oauth_tokens(
                "tenant_123", "user_456", "gmail"
            )

        assert result is True
        mock_tenant_store.delete_tenant_external_token.assert_called_once_with(
            "tenant_123", "gmail"
        )

    @pytest.mark.asyncio
    async def test_delete_oauth_tokens_exception_handling(
        self, service, mock_tenant_store
    ):
        """Test that delete exceptions are handled gracefully."""
        mock_tenant_store.delete_tenant_external_token.side_effect = Exception(
            "Delete error"
        )

        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.delete_oauth_tokens(
                "tenant_123", "user_456", "gmail"
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_list_tenant_providers_success(self, service, mock_tenant_store):
        """Test listing tenant providers successfully."""
        mock_tenant_store.list_tenant_providers.return_value = ["gmail", "calendar"]

        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.list_tenant_providers("tenant_123")

        # Order doesn't matter for the list of providers
        assert set(result) == {"gmail", "calendar"}
        mock_tenant_store.list_tenant_providers.assert_called_once_with("tenant_123")

    @pytest.mark.asyncio
    async def test_list_tenant_providers_exception_handling(
        self, service, mock_tenant_store
    ):
        """Test that list providers exceptions are handled gracefully."""
        mock_tenant_store.list_tenant_providers.side_effect = Exception("List error")

        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.list_tenant_providers("tenant_123")

        assert result == []


class TestTenantOAuthTokenServiceGlobal:
    """Test cases for global service functionality."""

    @pytest.mark.asyncio
    async def test_get_tenant_oauth_token_service_singleton(self):
        """Test that get_tenant_oauth_token_service returns a singleton."""
        service1 = await get_tenant_oauth_token_service()
        service2 = await get_tenant_oauth_token_service()

        assert service1 is service2
        assert isinstance(service1, TenantOAuthTokenService)

    @pytest.mark.asyncio
    async def test_backward_compatibility_alias(self):
        """Test that the backward compatibility alias works."""
        service1 = await get_unified_oauth_token_service()
        service2 = await get_tenant_oauth_token_service()

        assert service1 is service2
        assert isinstance(service1, TenantOAuthTokenService)
