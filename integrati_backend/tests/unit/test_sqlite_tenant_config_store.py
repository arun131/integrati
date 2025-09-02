"""Unit tests for SQLiteTenantConfigStore."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from mcp_plexus.tenants.sqlite_tenant_config_store import (
    SQLiteTenantConfigStore,
    get_sqlite_tenant_config_store,
)
from mcp_plexus.tenants.models import (
    TenantConfigCreate,
    TenantConfigUpdate,
    TenantConfigInDB,
)


class TestSQLiteTenantConfigStore:
    """Test cases for SQLiteTenantConfigStore."""

    @pytest.fixture
    def store(self):
        """Create a fresh store instance for each test."""
        return SQLiteTenantConfigStore()

    @pytest.fixture
    def sample_config_create(self):
        """Sample config creation data."""
        return TenantConfigCreate(
            entity_id="tenant_123",
            config_id="config_456",
            config_name="Test Config",
            config_type="profile",
            is_default=True,
            settings_json={"setting1": "value1", "setting2": "value2"},
        )

    @pytest.fixture
    def sample_config_update(self):
        """Sample config update data."""
        return TenantConfigUpdate(
            config_name="Updated Config",
            is_default=False,
            settings_json={"setting1": "updated_value"},
        )

    @pytest.mark.asyncio
    async def test_initialize(self, store):
        """Test store initialization."""
        with patch(
            "mcp_plexus.tenants.sqlite_tenant_config_store.get_sqlite_db_connection"
        ) as mock_get_conn:
            await store.initialize()
            mock_get_conn.assert_called_once()

    @pytest.mark.asyncio
    async def test_teardown(self, store):
        """Test store teardown."""
        await store.teardown()
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_create_config_success(self, store, sample_config_create):
        """Test successful config creation."""
        with patch.object(store, "_execute_query"):
            result = await store.create_config(sample_config_create)

        assert result.entity_id == "tenant_123"
        assert result.config_id == "config_456"
        assert result.config_name == "Test Config"
        assert result.config_type == "profile"
        assert result.is_default is True
        assert result.settings_json == {"setting1": "value1", "setting2": "value2"}
        assert isinstance(result.created_at, datetime)
        assert isinstance(result.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_create_config_duplicate_id(self, store, sample_config_create):
        """Test config creation with duplicate ID."""
        # Mock existing config
        with patch.object(
            store,
            "get_config_by_id",
            return_value=TenantConfigInDB(
                entity_id="tenant_123",
                config_id="config_456",
                config_name="Existing Config",
                config_type="profile",
                is_default=False,
                settings_json={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ):
            with pytest.raises(
                ValueError, match="Config with ID 'config_456' already exists"
            ):
                await store.create_config(sample_config_create)

    @pytest.mark.asyncio
    async def test_get_config_by_id_success(self, store):
        """Test successful config retrieval by ID."""
        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda key: {
            "entity_id": "tenant_123",
            "config_id": "config_456",
            "config_name": "Test Config",
            "config_type": "profile",
            "is_default": True,
            "settings_json": '{"setting1": "value1"}',
            "created_at": "2023-01-01T00:00:00+00:00",
            "updated_at": "2023-01-01T00:00:00+00:00",
        }[key]

        with patch.object(store, "_fetchone", return_value=mock_row):
            result = await store.get_config_by_id("tenant_123", "config_456")

        assert result is not None
        assert result.entity_id == "tenant_123"
        assert result.config_id == "config_456"
        assert result.config_name == "Test Config"
        assert result.is_default is True
        assert result.settings_json == {"setting1": "value1"}

    @pytest.mark.asyncio
    async def test_get_config_by_id_not_found(self, store):
        """Test config retrieval when config doesn't exist."""
        with patch.object(store, "_fetchone", return_value=None):
            result = await store.get_config_by_id("tenant_123", "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_configs_for_tenant_success(self, store):
        """Test successful listing of configs for a tenant."""
        # Create mock configs that would be returned by _row_to_config_in_db
        mock_config1 = TenantConfigInDB(
            entity_id="tenant_123",
            config_id="config_1",
            config_name="Config 1",
            config_type="profile",
            is_default=True,
            settings_json={"setting1": "value1"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_config2 = TenantConfigInDB(
            entity_id="tenant_123",
            config_id="config_2",
            config_name="Config 2",
            config_type="profile",
            is_default=False,
            settings_json={"setting2": "value2"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Mock the _row_to_config_in_db method to return our test configs
        with (
            patch.object(
                store, "_row_to_config_in_db", side_effect=[mock_config1, mock_config2]
            ),
            patch.object(store, "_fetchall", return_value=[MagicMock(), MagicMock()]),
        ):
            result = await store.list_configs_for_tenant("tenant_123", skip=0, limit=10)

        assert len(result) == 2
        assert result[0].config_id == "config_1"
        assert result[0].is_default is True
        assert result[1].config_id == "config_2"
        assert result[1].is_default is False

    @pytest.mark.asyncio
    async def test_list_configs_for_tenant_empty(self, store):
        """Test listing configs when tenant has no configs."""
        with patch.object(store, "_fetchall", return_value=[]):
            result = await store.list_configs_for_tenant("tenant_123")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_default_config_for_tenant_success(self, store):
        """Test successful retrieval of default config."""
        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda key: {
            "entity_id": "tenant_123",
            "config_id": "default_config",
            "config_name": "Default Config",
            "config_type": "profile",
            "is_default": True,
            "settings_json": '{"default": true}',
            "created_at": "2023-01-01T00:00:00+00:00",
            "updated_at": "2023-01-01T00:00:00+00:00",
        }[key]

        with patch.object(store, "_fetchone", return_value=mock_row):
            result = await store.get_default_config_for_tenant("tenant_123")

        assert result is not None
        assert result.config_id == "default_config"
        assert result.is_default is True

    @pytest.mark.asyncio
    async def test_get_default_config_for_tenant_not_found(self, store):
        """Test default config retrieval when no default exists."""
        with patch.object(store, "_fetchone", return_value=None):
            result = await store.get_default_config_for_tenant("tenant_123")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_config_success(self, store, sample_config_update):
        """Test successful config update."""
        # Mock existing config
        existing_config = TenantConfigInDB(
            entity_id="tenant_123",
            config_id="config_456",
            config_name="Original Config",
            config_type="profile",
            is_default=True,
            settings_json={"original": "value"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Mock updated config
        updated_config = TenantConfigInDB(
            entity_id="tenant_123",
            config_id="config_456",
            config_name="Updated Config",
            config_type="profile",
            is_default=False,
            settings_json={"setting1": "updated_value"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with (
            patch.object(
                store, "get_config_by_id", side_effect=[existing_config, updated_config]
            ),
            patch.object(store, "_execute_query"),
        ):
            result = await store.update_config(
                "tenant_123", "config_456", sample_config_update
            )

        assert result is not None
        assert result.config_name == "Updated Config"
        assert result.is_default is False
        assert result.settings_json == {"setting1": "updated_value"}

    @pytest.mark.asyncio
    async def test_update_config_not_found(self, store, sample_config_update):
        """Test config update when config doesn't exist."""
        with patch.object(store, "get_config_by_id", return_value=None):
            result = await store.update_config(
                "tenant_123", "nonexistent", sample_config_update
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_config_success(self, store):
        """Test successful config deletion."""
        with patch.object(store, "_execute_query") as mock_execute:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_execute.return_value = mock_cursor

            result = await store.delete_config("tenant_123", "config_456")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_config_not_found(self, store):
        """Test config deletion when config doesn't exist."""
        with patch.object(store, "_execute_query") as mock_execute:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 0
            mock_execute.return_value = mock_cursor

            result = await store.delete_config("tenant_123", "nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_set_default_config_success(self, store):
        """Test successful setting of default config."""
        # Mock existing config
        existing_config = TenantConfigInDB(
            entity_id="tenant_123",
            config_id="config_456",
            config_name="Test Config",
            config_type="profile",
            is_default=False,
            settings_json={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with (
            patch.object(store, "get_config_by_id", return_value=existing_config),
            patch.object(store, "_unset_default_configs") as mock_unset,
            patch.object(store, "_execute_query"),
            patch.object(store, "get_config_by_id", return_value=existing_config),
        ):
            result = await store.set_default_config("tenant_123", "config_456")

        assert result is not None
        mock_unset.assert_called_once_with("tenant_123")

    @pytest.mark.asyncio
    async def test_set_default_config_not_found(self, store):
        """Test setting default config when config doesn't exist."""
        with patch.object(store, "get_config_by_id", return_value=None):
            result = await store.set_default_config("tenant_123", "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_row_to_config_in_db_success(self, store):
        """Test successful row to config conversion."""
        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda key: {
            "entity_id": "tenant_123",
            "config_id": "config_456",
            "config_name": "Test Config",
            "config_type": "profile",
            "is_default": True,
            "settings_json": '{"setting1": "value1"}',
            "created_at": "2023-01-01T00:00:00+00:00",
            "updated_at": "2023-01-01T00:00:00+00:00",
        }[key]

        result = store._row_to_config_in_db(mock_row)

        assert result is not None
        assert result.entity_id == "tenant_123"
        assert result.config_id == "config_456"
        assert result.config_name == "Test Config"
        assert result.is_default is True
        assert result.settings_json == {"setting1": "value1"}

    @pytest.mark.asyncio
    async def test_row_to_config_in_db_none_row(self, store):
        """Test row conversion with None row."""
        result = store._row_to_config_in_db(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_row_to_config_in_db_invalid_json(self, store):
        """Test row conversion with invalid JSON."""
        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda key: {
            "entity_id": "tenant_123",
            "config_id": "config_456",
            "config_name": "Test Config",
            "config_type": "profile",
            "is_default": True,
            "settings_json": "invalid json",
            "created_at": "2023-01-01T00:00:00+00:00",
            "updated_at": "2023-01-01T00:00:00+00:00",
        }[key]

        result = store._row_to_config_in_db(mock_row)
        assert result is None


class TestSQLiteTenantConfigStoreGlobal:
    """Test cases for global store functionality."""

    @pytest.mark.asyncio
    async def test_get_sqlite_tenant_config_store_singleton(self):
        """Test that get_sqlite_tenant_config_store returns a singleton."""
        with patch(
            "mcp_plexus.tenants.sqlite_tenant_config_store.get_sqlite_db_connection"
        ):
            store1 = await get_sqlite_tenant_config_store()
            store2 = await get_sqlite_tenant_config_store()

            assert store1 is store2
            assert isinstance(store1, SQLiteTenantConfigStore)
