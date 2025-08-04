"""Unit tests for UnifiedOAuthTokenService."""

import pytest
from unittest.mock import AsyncMock, patch

from mcp_plexus.oauth.unified_token_service import (
    UnifiedOAuthTokenService,
    get_unified_oauth_token_service,
)
from mcp_plexus.oauth.storage_interfaces import (
    AbstractUserExternalTokenStore,
    AbstractTenantExternalTokenStore,
)


class TestUnifiedOAuthTokenService:
    """Test cases for UnifiedOAuthTokenService."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance for each test."""
        return UnifiedOAuthTokenService()

    @pytest.fixture
    def mock_user_store(self):
        """Mock user token store."""
        store = AsyncMock(spec=AbstractUserExternalTokenStore)
        return store

    @pytest.fixture
    def mock_tenant_store(self):
        """Mock tenant token store."""
        store = AsyncMock(spec=AbstractTenantExternalTokenStore)
        return store

    @pytest.mark.asyncio
    async def test_get_oauth_tokens_tenant_level_success(
        self, service, mock_tenant_store
    ):
        """Test getting OAuth tokens from tenant-level storage successfully."""
        # Mock tenant-level tokens
        mock_tenant_store.load_tenant_external_token.return_value = {
            "access_token": "tenant_token",
            "refresh_token": "tenant_refresh",
        }

        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.get_oauth_tokens(
                "tenant_123", "user_456", "gmail", prefer_tenant_level=True
            )

        assert result == {
            "access_token": "tenant_token",
            "refresh_token": "tenant_refresh",
        }
        mock_tenant_store.load_tenant_external_token.assert_called_once_with(
            "tenant_123", "gmail"
        )

    @pytest.mark.asyncio
    async def test_get_oauth_tokens_tenant_level_fallback_to_user(
        self, service, mock_tenant_store, mock_user_store
    ):
        """Test getting OAuth tokens with tenant-level fallback to user-level."""
        # Mock no tenant-level tokens, but user-level tokens exist
        mock_tenant_store.load_tenant_external_token.return_value = None
        mock_user_store.load_user_external_token.return_value = {
            "access_token": "user_token",
            "refresh_token": "user_refresh",
        }

        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ), patch.object(service, "_get_user_token_store", return_value=mock_user_store):
            result = await service.get_oauth_tokens(
                "tenant_123", "user_456", "gmail", prefer_tenant_level=True
            )

        assert result == {"access_token": "user_token", "refresh_token": "user_refresh"}
        mock_tenant_store.load_tenant_external_token.assert_called_once_with(
            "tenant_123", "gmail"
        )
        mock_user_store.load_user_external_token.assert_called_once_with(
            "tenant_123", "user_456", "gmail"
        )

    @pytest.mark.asyncio
    async def test_get_oauth_tokens_user_level_success(self, service, mock_user_store):
        """Test getting OAuth tokens from user-level storage successfully."""
        # Mock user-level tokens
        mock_user_store.load_user_external_token.return_value = {
            "access_token": "user_token",
            "refresh_token": "user_refresh",
        }

        with patch.object(
            service, "_get_user_token_store", return_value=mock_user_store
        ):
            result = await service.get_oauth_tokens(
                "tenant_123", "user_456", "gmail", prefer_tenant_level=False
            )

        assert result == {"access_token": "user_token", "refresh_token": "user_refresh"}
        mock_user_store.load_user_external_token.assert_called_once_with(
            "tenant_123", "user_456", "gmail"
        )

    @pytest.mark.asyncio
    async def test_get_oauth_tokens_user_level_fallback_to_tenant(
        self, service, mock_user_store, mock_tenant_store
    ):
        """Test getting OAuth tokens with user-level fallback to tenant-level."""
        # Mock no user-level tokens, but tenant-level tokens exist
        mock_user_store.load_user_external_token.return_value = None
        mock_tenant_store.load_tenant_external_token.return_value = {
            "access_token": "tenant_token",
            "refresh_token": "tenant_refresh",
        }

        with patch.object(
            service, "_get_user_token_store", return_value=mock_user_store
        ), patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.get_oauth_tokens(
                "tenant_123", "user_456", "gmail", prefer_tenant_level=False
            )

        assert result == {
            "access_token": "tenant_token",
            "refresh_token": "tenant_refresh",
        }
        mock_user_store.load_user_external_token.assert_called_once_with(
            "tenant_123", "user_456", "gmail"
        )
        mock_tenant_store.load_tenant_external_token.assert_called_once_with(
            "tenant_123", "gmail"
        )

    @pytest.mark.asyncio
    async def test_get_oauth_tokens_no_tokens_found(
        self, service, mock_tenant_store, mock_user_store
    ):
        """Test getting OAuth tokens when no tokens are found."""
        # Mock no tokens in either store
        mock_tenant_store.load_tenant_external_token.return_value = None
        mock_user_store.load_user_external_token.return_value = None

        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ), patch.object(service, "_get_user_token_store", return_value=mock_user_store):
            result = await service.get_oauth_tokens(
                "tenant_123", "user_456", "gmail", prefer_tenant_level=True
            )

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
            result = await service.get_oauth_tokens(
                "tenant_123", "user_456", "gmail", prefer_tenant_level=True
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_save_oauth_tokens_tenant_level(self, service, mock_tenant_store):
        """Test saving OAuth tokens to tenant-level storage."""
        token_data = {"access_token": "new_token", "refresh_token": "new_refresh"}

        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.save_oauth_tokens(
                "tenant_123", "user_456", "gmail", token_data, use_tenant_level=True
            )

        assert result is True
        mock_tenant_store.save_tenant_external_token.assert_called_once_with(
            "tenant_123", "gmail", token_data
        )

    @pytest.mark.asyncio
    async def test_save_oauth_tokens_user_level(self, service, mock_user_store):
        """Test saving OAuth tokens to user-level storage."""
        token_data = {"access_token": "new_token", "refresh_token": "new_refresh"}

        with patch.object(
            service, "_get_user_token_store", return_value=mock_user_store
        ):
            result = await service.save_oauth_tokens(
                "tenant_123", "user_456", "gmail", token_data, use_tenant_level=False
            )

        assert result is True
        mock_user_store.save_user_external_token.assert_called_once_with(
            "tenant_123", "user_456", "gmail", token_data
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
                use_tenant_level=True,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_oauth_tokens_tenant_level_only(
        self, service, mock_tenant_store
    ):
        """Test deleting OAuth tokens from tenant-level storage only."""
        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.delete_oauth_tokens(
                "tenant_123",
                "user_456",
                "gmail",
                delete_tenant_level=True,
                delete_user_level=False,
            )

        assert result is True
        mock_tenant_store.delete_tenant_external_token.assert_called_once_with(
            "tenant_123", "gmail"
        )

    @pytest.mark.asyncio
    async def test_delete_oauth_tokens_user_level_only(self, service, mock_user_store):
        """Test deleting OAuth tokens from user-level storage only."""
        with patch.object(
            service, "_get_user_token_store", return_value=mock_user_store
        ):
            result = await service.delete_oauth_tokens(
                "tenant_123",
                "user_456",
                "gmail",
                delete_tenant_level=False,
                delete_user_level=True,
            )

        assert result is True
        mock_user_store.delete_user_external_token.assert_called_once_with(
            "tenant_123", "user_456", "gmail"
        )

    @pytest.mark.asyncio
    async def test_delete_oauth_tokens_both_levels(
        self, service, mock_tenant_store, mock_user_store
    ):
        """Test deleting OAuth tokens from both storage levels."""
        with patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ), patch.object(service, "_get_user_token_store", return_value=mock_user_store):
            result = await service.delete_oauth_tokens(
                "tenant_123",
                "user_456",
                "gmail",
                delete_tenant_level=True,
                delete_user_level=True,
            )

        assert result is True
        mock_tenant_store.delete_tenant_external_token.assert_called_once_with(
            "tenant_123", "gmail"
        )
        mock_user_store.delete_user_external_token.assert_called_once_with(
            "tenant_123", "user_456", "gmail"
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
                "tenant_123",
                "user_456",
                "gmail",
                delete_tenant_level=True,
                delete_user_level=False,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_migrate_user_tokens_to_tenant_success(
        self, service, mock_user_store, mock_tenant_store
    ):
        """Test successful migration of user tokens to tenant level."""
        # Mock user-level tokens exist
        user_tokens = {"access_token": "user_token", "refresh_token": "user_refresh"}
        mock_user_store.load_user_external_token.return_value = user_tokens

        with patch.object(
            service, "_get_user_token_store", return_value=mock_user_store
        ), patch.object(
            service, "_get_tenant_token_store", return_value=mock_tenant_store
        ):
            result = await service.migrate_user_tokens_to_tenant(
                "tenant_123", "user_456", "gmail"
            )

        assert result is True
        mock_user_store.load_user_external_token.assert_called_once_with(
            "tenant_123", "user_456", "gmail"
        )
        mock_tenant_store.save_tenant_external_token.assert_called_once_with(
            "tenant_123", "gmail", user_tokens
        )

    @pytest.mark.asyncio
    async def test_migrate_user_tokens_to_tenant_no_user_tokens(
        self, service, mock_user_store
    ):
        """Test migration when no user tokens exist."""
        mock_user_store.load_user_external_token.return_value = None

        with patch.object(
            service, "_get_user_token_store", return_value=mock_user_store
        ):
            result = await service.migrate_user_tokens_to_tenant(
                "tenant_123", "user_456", "gmail"
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_migrate_user_tokens_to_tenant_exception_handling(
        self, service, mock_user_store
    ):
        """Test that migration exceptions are handled gracefully."""
        mock_user_store.load_user_external_token.side_effect = Exception(
            "Migration error"
        )

        with patch.object(
            service, "_get_user_token_store", return_value=mock_user_store
        ):
            result = await service.migrate_user_tokens_to_tenant(
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


class TestUnifiedOAuthTokenServiceGlobal:
    """Test cases for global service functionality."""

    @pytest.mark.asyncio
    async def test_get_unified_oauth_token_service_singleton(self):
        """Test that get_unified_oauth_token_service returns a singleton."""
        service1 = await get_unified_oauth_token_service()
        service2 = await get_unified_oauth_token_service()

        assert service1 is service2
        assert isinstance(service1, UnifiedOAuthTokenService)
