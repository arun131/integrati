"""Unit tests for SQLiteTenantExternalTokenStore."""

import pytest
import json
from unittest.mock import patch, MagicMock

from mcp_plexus.oauth.sqlite_tenant_external_token_store import (
    SQLiteTenantExternalTokenStore,
    get_sqlite_tenant_external_token_store,
)


class TestSQLiteTenantExternalTokenStore:
    """Test cases for SQLiteTenantExternalTokenStore."""

    @pytest.fixture
    def store(self):
        """Create a fresh store instance for each test."""
        return SQLiteTenantExternalTokenStore()

    @pytest.fixture
    def sample_token_data(self):
        """Sample token data for testing."""
        return {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/gmail.readonly",
        }

    @pytest.mark.asyncio
    async def test_initialize(self, store):
        """Test store initialization."""
        with patch(
            "mcp_plexus.oauth.sqlite_tenant_external_token_store.get_sqlite_db_connection"
        ) as mock_get_conn:
            await store.initialize()
            mock_get_conn.assert_called_once()

    @pytest.mark.asyncio
    async def test_teardown(self, store):
        """Test store teardown."""
        await store.teardown()
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_save_tenant_external_token_success(self, store, sample_token_data):
        """Test successful token saving."""
        with patch.object(store, "_execute_query") as mock_execute:
            await store.save_tenant_external_token(
                "tenant_123", "gmail", sample_token_data
            )

        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        assert (
            call_args[0][0]
            == """
            INSERT INTO tenant_external_oauth_tokens (entity_id, provider_name, token_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(entity_id, provider_name) DO UPDATE SET
                token_data=excluded.token_data,
                updated_at=excluded.updated_at
        """
        )
        assert call_args[0][1][0] == "tenant_123"  # entity_id
        assert call_args[0][1][1] == "gmail"  # provider_name
        assert json.loads(call_args[0][1][2]) == sample_token_data  # token_data

    @pytest.mark.asyncio
    async def test_save_tenant_external_token_exception_handling(
        self, store, sample_token_data
    ):
        """Test that save exceptions are handled gracefully."""
        with patch.object(
            store, "_execute_query", side_effect=Exception("Database error")
        ):
            with pytest.raises(Exception, match="Database error"):
                await store.save_tenant_external_token(
                    "tenant_123", "gmail", sample_token_data
                )

    @pytest.mark.asyncio
    async def test_load_tenant_external_token_success(self, store, sample_token_data):
        """Test successful token loading."""
        mock_row = MagicMock()
        mock_row.__getitem__.return_value = json.dumps(sample_token_data)

        with patch.object(store, "_fetchone", return_value=mock_row):
            result = await store.load_tenant_external_token("tenant_123", "gmail")

        assert result == sample_token_data
        # The method calls __getitem__ twice: once to check if row exists, once to get token_data
        assert mock_row.__getitem__.call_count >= 1
        mock_row.__getitem__.assert_any_call("token_data")

    @pytest.mark.asyncio
    async def test_load_tenant_external_token_not_found(self, store):
        """Test token loading when token doesn't exist."""
        with patch.object(store, "_fetchone", return_value=None):
            result = await store.load_tenant_external_token("tenant_123", "gmail")

        assert result is None

    @pytest.mark.asyncio
    async def test_load_tenant_external_token_invalid_json(self, store):
        """Test token loading with invalid JSON."""
        mock_row = MagicMock()
        mock_row.__getitem__.return_value = "invalid json"

        with patch.object(store, "_fetchone", return_value=mock_row):
            result = await store.load_tenant_external_token("tenant_123", "gmail")

        assert result is None

    @pytest.mark.asyncio
    async def test_load_tenant_external_token_empty_token_data(self, store):
        """Test token loading with empty token data."""
        mock_row = MagicMock()
        mock_row.__getitem__.return_value = ""

        with patch.object(store, "_fetchone", return_value=mock_row):
            result = await store.load_tenant_external_token("tenant_123", "gmail")

        assert result is None

    @pytest.mark.asyncio
    async def test_load_tenant_external_token_exception_handling(self, store):
        """Test that load exceptions are handled gracefully."""
        with patch.object(store, "_fetchone", side_effect=Exception("Database error")):
            with pytest.raises(Exception, match="Database error"):
                await store.load_tenant_external_token("tenant_123", "gmail")

    @pytest.mark.asyncio
    async def test_delete_tenant_external_token_success(self, store):
        """Test successful token deletion."""
        with patch.object(store, "_execute_query") as mock_execute:
            await store.delete_tenant_external_token("tenant_123", "gmail")

        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        # Check that the query contains the expected SQL (allowing for whitespace differences)
        query = call_args[0][0].strip()
        expected_query = """
            DELETE FROM tenant_external_oauth_tokens
            WHERE entity_id = ? AND provider_name = ?
        """.strip()
        assert query == expected_query
        assert call_args[0][1] == ("tenant_123", "gmail")

    @pytest.mark.asyncio
    async def test_delete_tenant_external_token_exception_handling(self, store):
        """Test that delete exceptions are handled gracefully."""
        with patch.object(
            store, "_execute_query", side_effect=Exception("Database error")
        ):
            with pytest.raises(Exception, match="Database error"):
                await store.delete_tenant_external_token("tenant_123", "gmail")

    @pytest.mark.asyncio
    async def test_list_tenant_providers_success(self, store):
        """Test successful provider listing."""
        mock_rows = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        # Set up the mock rows to return the expected provider names
        mock_rows[0].__getitem__.return_value = "gmail"
        mock_rows[1].__getitem__.return_value = "calendar"
        mock_rows[2].__getitem__.return_value = "twitter"

        with patch.object(store, "_fetchall", return_value=mock_rows):
            result = await store.list_tenant_providers("tenant_123")

        assert result == ["gmail", "calendar", "twitter"]

    @pytest.mark.asyncio
    async def test_list_tenant_providers_empty(self, store):
        """Test provider listing when tenant has no providers."""
        with patch.object(store, "_fetchall", return_value=[]):
            result = await store.list_tenant_providers("tenant_123")

        assert result == []

    @pytest.mark.asyncio
    async def test_list_tenant_providers_exception_handling(self, store):
        """Test that list exceptions are handled gracefully."""
        with patch.object(store, "_fetchall", side_effect=Exception("Database error")):
            with pytest.raises(Exception, match="Database error"):
                await store.list_tenant_providers("tenant_123")

    @pytest.mark.asyncio
    async def test_execute_query_success(self, store):
        """Test successful query execution."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch(
            "mcp_plexus.oauth.sqlite_tenant_external_token_store.get_sqlite_db_connection",
            return_value=mock_conn,
        ):
            await store._execute_query("SELECT * FROM test", ("param1",))

        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test", ("param1",))

    @pytest.mark.asyncio
    async def test_execute_query_exception_handling(self, store):
        """Test that query execution exceptions are handled gracefully."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("SQL error")
        mock_conn.cursor.return_value = mock_cursor

        with patch(
            "mcp_plexus.oauth.sqlite_tenant_external_token_store.get_sqlite_db_connection",
            return_value=mock_conn,
        ):
            with pytest.raises(Exception, match="SQL error"):
                await store._execute_query("SELECT * FROM test")

        # Note: The actual implementation doesn't call rollback in the exception handler
        # so we don't expect it to be called

    @pytest.mark.asyncio
    async def test_fetchone_success(self, store):
        """Test successful fetchone execution."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"test": "data"}
        mock_conn.cursor.return_value = mock_cursor

        with patch(
            "mcp_plexus.oauth.sqlite_tenant_external_token_store.get_sqlite_db_connection",
            return_value=mock_conn,
        ):
            result = await store._fetchone("SELECT * FROM test", ("param1",))

        mock_cursor.execute.assert_called_once_with("SELECT * FROM test", ("param1",))
        assert result == {"test": "data"}

    @pytest.mark.asyncio
    async def test_fetchone_exception_handling(self, store):
        """Test that fetchone exceptions are handled gracefully."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("SQL error")
        mock_conn.cursor.return_value = mock_cursor

        with patch(
            "mcp_plexus.oauth.sqlite_tenant_external_token_store.get_sqlite_db_connection",
            return_value=mock_conn,
        ):
            with pytest.raises(Exception, match="SQL error"):
                await store._fetchone("SELECT * FROM test")

    @pytest.mark.asyncio
    async def test_fetchall_success(self, store):
        """Test successful fetchall execution."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{"test1": "data1"}, {"test2": "data2"}]
        mock_conn.cursor.return_value = mock_cursor

        with patch(
            "mcp_plexus.oauth.sqlite_tenant_external_token_store.get_sqlite_db_connection",
            return_value=mock_conn,
        ):
            result = await store._fetchall("SELECT * FROM test", ("param1",))

        mock_cursor.execute.assert_called_once_with("SELECT * FROM test", ("param1",))
        assert result == [{"test1": "data1"}, {"test2": "data2"}]

    @pytest.mark.asyncio
    async def test_fetchall_exception_handling(self, store):
        """Test that fetchall exceptions are handled gracefully."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("SQL error")
        mock_conn.cursor.return_value = mock_cursor

        with patch(
            "mcp_plexus.oauth.sqlite_tenant_external_token_store.get_sqlite_db_connection",
            return_value=mock_conn,
        ):
            with pytest.raises(Exception, match="SQL error"):
                await store._fetchall("SELECT * FROM test")


class TestSQLiteTenantExternalTokenStoreGlobal:
    """Test cases for global store functionality."""

    @pytest.mark.asyncio
    async def test_get_sqlite_tenant_external_token_store_singleton(self):
        """Test that get_sqlite_tenant_external_token_store returns a singleton."""
        with patch(
            "mcp_plexus.oauth.sqlite_tenant_external_token_store.get_sqlite_db_connection"
        ):
            store1 = await get_sqlite_tenant_external_token_store()
            store2 = await get_sqlite_tenant_external_token_store()

            assert store1 is store2
            assert isinstance(store1, SQLiteTenantExternalTokenStore)
