# mcp_plexus/tenants/sqlite_tenant_config_store.py
import sqlite3
import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .storage_interfaces import AbstractTenantConfigStore
from .models import TenantConfigInDB, TenantConfigCreate, TenantConfigUpdate
from ..storage.sqlite_base import get_sqlite_db_connection

logger = logging.getLogger(__name__)


class SQLiteTenantConfigStore(AbstractTenantConfigStore):
    """SQLite implementation of the tenant config storage interface."""

    async def initialize(self) -> None:
        """Initialize the tenant config store by ensuring database and table exist."""
        await get_sqlite_db_connection()
        logger.info("SQLiteTenantConfigStore initialized.")

    async def teardown(self) -> None:
        """Clean up resources. Connection is managed globally so no action needed."""
        logger.info("SQLiteTenantConfigStore teardown (connection managed globally).")

    async def _execute_query(self, query: str, params: tuple = (), commit: bool = True) -> sqlite3.Cursor:
        """
        Execute a SQL query with proper error handling and transaction management.
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            commit: Whether to commit the transaction
            
        Returns:
            sqlite3.Cursor: The cursor after query execution
            
        Raises:
            sqlite3.Error: If query execution fails
        """
        conn = await get_sqlite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit:
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"SQLite error executing query '{query}': {e}", exc_info=True)
            if commit:
                conn.rollback()
            raise
        return cursor

    async def _fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute a query and return a single row."""
        cursor = await self._execute_query(query, params, commit=False)
        return cursor.fetchone()

    async def _fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute a query and return all matching rows."""
        cursor = await self._execute_query(query, params, commit=False)
        return cursor.fetchall()

    def _row_to_config_in_db(self, row: Optional[sqlite3.Row]) -> Optional[TenantConfigInDB]:
        """
        Convert a database row to a TenantConfigInDB object.
        
        Handles datetime parsing and JSON deserialization with error recovery.
        """
        if not row:
            return None
        
        try:
            # Handle datetime conversion - SQLite may store as string or datetime
            created_at = row["created_at"]
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            
            updated_at = row["updated_at"]
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            
            return TenantConfigInDB(
                entity_id=row["entity_id"],
                config_id=row["config_id"],
                config_name=row["config_name"],
                config_type=row["config_type"],
                is_default=bool(row["is_default"]),
                settings_json=json.loads(row["settings_json"]) if row["settings_json"] else {},
                created_at=created_at,
                updated_at=updated_at
            )
        except Exception as e:
            logger.error(f"Error converting row to TenantConfigInDB: {row}. Error: {e}", exc_info=True)
            return None

    async def create_config(self, config_create: TenantConfigCreate) -> TenantConfigInDB:
        """
        Create a new tenant config in the database.
        
        Args:
            config_create: Config creation data
            
        Returns:
            TenantConfigInDB: The created config with generated timestamps
            
        Raises:
            ValueError: If config with same ID already exists for the tenant
        """
        # Check for existing config to prevent duplicates
        existing = await self.get_config_by_id(config_create.entity_id, config_create.config_id)
        if existing:
            raise ValueError(f"Config with ID '{config_create.config_id}' already exists for tenant '{config_create.entity_id}'.")

        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        settings_str = json.dumps(config_create.settings_json or {})

        # If this is being set as default, unset any existing default
        if config_create.is_default:
            await self._unset_default_configs(config_create.entity_id)

        query = """
            INSERT INTO tenant_configs (entity_id, config_id, config_name, config_type, is_default, settings_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            config_create.entity_id,
            config_create.config_id,
            config_create.config_name,
            config_create.config_type,
            config_create.is_default,
            settings_str,
            now_iso,
            now_iso
        )
        
        await self._execute_query(query, params)
        
        return TenantConfigInDB(
            entity_id=config_create.entity_id,
            config_id=config_create.config_id,
            config_name=config_create.config_name,
            config_type=config_create.config_type,
            is_default=config_create.is_default,
            settings_json=config_create.settings_json or {},
            created_at=now_dt,
            updated_at=now_dt
        )

    async def get_config_by_id(self, entity_id: str, config_id: str) -> Optional[TenantConfigInDB]:
        """Retrieve a config by its entity ID and config ID."""
        query = """
            SELECT entity_id, config_id, config_name, config_type, is_default, settings_json, created_at, updated_at
            FROM tenant_configs 
            WHERE entity_id = ? AND config_id = ?
        """
        row = await self._fetchone(query, (entity_id, config_id))
        return self._row_to_config_in_db(row)

    async def list_configs_for_tenant(self, entity_id: str, skip: int = 0, limit: int = 100) -> List[TenantConfigInDB]:
        """
        Retrieve a paginated list of configs for a tenant ordered by creation date (newest first).
        
        Args:
            entity_id: The tenant's entity ID
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of TenantConfigInDB objects, excluding any that failed to parse
        """
        query = """
            SELECT entity_id, config_id, config_name, config_type, is_default, settings_json, created_at, updated_at
            FROM tenant_configs 
            WHERE entity_id = ?
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """
        rows = await self._fetchall(query, (entity_id, limit, skip))
        
        # Filter out None values from failed conversions
        return [
            config for row in rows 
            if (config := self._row_to_config_in_db(row)) is not None
        ]

    async def get_default_config_for_tenant(self, entity_id: str) -> Optional[TenantConfigInDB]:
        """Get the default config for a tenant."""
        query = """
            SELECT entity_id, config_id, config_name, config_type, is_default, settings_json, created_at, updated_at
            FROM tenant_configs 
            WHERE entity_id = ? AND is_default = 1
        """
        row = await self._fetchone(query, (entity_id,))
        return self._row_to_config_in_db(row)

    async def _unset_default_configs(self, entity_id: str) -> None:
        """Helper method to unset all default configs for a tenant."""
        query = "UPDATE tenant_configs SET is_default = 0 WHERE entity_id = ? AND is_default = 1"
        await self._execute_query(query, (entity_id,))

    async def update_config(self, entity_id: str, config_id: str, config_update: TenantConfigUpdate) -> Optional[TenantConfigInDB]:
        """
        Update an existing config with partial data.
        
        Args:
            entity_id: The tenant's entity ID
            config_id: The config ID to update
            config_update: Partial update data (only set fields will be updated)
            
        Returns:
            Updated TenantConfigInDB object or None if config not found
        """
        current_config = await self.get_config_by_id(entity_id, config_id)
        if not current_config:
            return None

        # Extract only the fields that were explicitly set
        update_fields: Dict[str, Any] = config_update.model_dump(exclude_unset=True)
        if not update_fields:
            return current_config

        # If setting as default, unset any existing default first
        if update_fields.get("is_default") is True:
            await self._unset_default_configs(entity_id)

        # Build dynamic UPDATE query based on provided fields
        set_clauses = []
        params = []
        for key, value in update_fields.items():
            set_clauses.append(f"{key} = ?")
            if key == "settings_json":
                params.append(json.dumps(value or {}))
            else:
                params.append(value)

        # Always update the updated_at timestamp
        set_clauses.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())

        query = f"UPDATE tenant_configs SET {', '.join(set_clauses)} WHERE entity_id = ? AND config_id = ?"
        params.extend([entity_id, config_id])

        await self._execute_query(query, tuple(params))
        return await self.get_config_by_id(entity_id, config_id)

    async def delete_config(self, entity_id: str, config_id: str) -> bool:
        """
        Delete a config by entity ID and config ID.
        
        Returns:
            bool: True if a config was deleted, False if no config found
        """
        query = "DELETE FROM tenant_configs WHERE entity_id = ? AND config_id = ?"
        cursor = await self._execute_query(query, (entity_id, config_id))
        return cursor.rowcount > 0

    async def set_default_config(self, entity_id: str, config_id: str) -> Optional[TenantConfigInDB]:
        """
        Set a specific config as the default for a tenant.
        This will unset any previous default config.
        
        Args:
            entity_id: The tenant's entity ID
            config_id: The config ID to set as default
            
        Returns:
            Updated config or None if not found
        """
        # Check if config exists
        config = await self.get_config_by_id(entity_id, config_id)
        if not config:
            return None

        # Unset all defaults for this tenant first
        await self._unset_default_configs(entity_id)

        # Set this config as default
        query = "UPDATE tenant_configs SET is_default = 1, updated_at = ? WHERE entity_id = ? AND config_id = ?"
        params = (datetime.now(timezone.utc).isoformat(), entity_id, config_id)
        await self._execute_query(query, params)
        
        return await self.get_config_by_id(entity_id, config_id)


# Singleton instance management
_sqlite_tenant_config_store_instance: Optional[SQLiteTenantConfigStore] = None


async def get_sqlite_tenant_config_store() -> SQLiteTenantConfigStore:
    """
    Get or create the singleton SQLiteTenantConfigStore instance.
    
    Ensures only one instance exists and is properly initialized.
    """
    global _sqlite_tenant_config_store_instance
    if _sqlite_tenant_config_store_instance is None:
        _sqlite_tenant_config_store_instance = SQLiteTenantConfigStore()
        await _sqlite_tenant_config_store_instance.initialize()
    return _sqlite_tenant_config_store_instance 