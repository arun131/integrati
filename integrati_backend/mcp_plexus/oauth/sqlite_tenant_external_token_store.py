# mcp_plexus/oauth/sqlite_tenant_external_token_store.py
import sqlite3
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from .storage_interfaces import AbstractTenantExternalTokenStore 
from ..storage.sqlite_base import get_sqlite_db_connection

logger = logging.getLogger(__name__)


class SQLiteTenantExternalTokenStore(AbstractTenantExternalTokenStore):
    """SQLite implementation for storing tenant-level external OAuth tokens."""
    
    async def initialize(self) -> None:
        """Initialize the token store by ensuring database connection and tables exist."""
        await get_sqlite_db_connection() 
        logger.info("SQLiteTenantExternalTokenStore initialized (tables ensured by sqlite_base).")

    async def teardown(self) -> None:
        """Clean up resources. Connection is managed globally, so no action needed."""
        logger.info("SQLiteTenantExternalTokenStore teardown (connection managed globally).")

    async def _execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a SQL query with proper error handling and transaction management.
        Commits on success, rolls back on error.
        """
        conn = await get_sqlite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"SQLite error executing query '{query}': {e}", exc_info=True)
            conn.rollback()
            raise
        return cursor

    async def _fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute a SELECT query and return a single row result."""
        conn = await get_sqlite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"SQLite error during fetchone for query '{query}': {e}", exc_info=True)
            raise

    async def _fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute a SELECT query and return all matching rows."""
        conn = await get_sqlite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"SQLite error during fetchall for query '{query}': {e}", exc_info=True)
            raise

    async def save_tenant_external_token(
        self, entity_id: str, provider_name: str, token_data: Dict[str, Any]
    ) -> None:
        """
        Save or update tenant external OAuth token data.
        Uses UPSERT pattern to handle both insert and update scenarios.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        
        query = '''
            INSERT INTO tenant_external_oauth_tokens (entity_id, provider_name, token_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(entity_id, provider_name) DO UPDATE SET
                token_data=excluded.token_data,
                updated_at=excluded.updated_at
        '''
        token_data_json = json.dumps(token_data)
        params = (entity_id, provider_name, token_data_json, now_iso, now_iso)
        await self._execute_query(query, params)
        logger.info(f"Saved tenant external token for E:{entity_id}, P:{provider_name}.")

    async def load_tenant_external_token(
        self, entity_id: str, provider_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load tenant external OAuth token data for the specified entity and provider.
        Returns None if token doesn't exist or JSON deserialization fails.
        """
        query = """
            SELECT token_data 
            FROM tenant_external_oauth_tokens 
            WHERE entity_id = ? AND provider_name = ?
        """
        row = await self._fetchone(query, (entity_id, provider_name))
        if row and row["token_data"]:
            try:
                return json.loads(row["token_data"])
            except json.JSONDecodeError as e:
                logger.error(
                    f"Error deserializing tenant external token for "
                    f"E:{entity_id}, P:{provider_name}: {e}", 
                    exc_info=True
                )
                return None
        return None

    async def delete_tenant_external_token(
        self, entity_id: str, provider_name: str
    ) -> None:
        """Delete tenant external OAuth token for the specified entity and provider."""
        query = """
            DELETE FROM tenant_external_oauth_tokens 
            WHERE entity_id = ? AND provider_name = ?
        """
        await self._execute_query(query, (entity_id, provider_name))
        logger.info(f"Deleted tenant external token for E:{entity_id}, P:{provider_name}.")

    async def list_tenant_providers(self, entity_id: str) -> List[str]:
        """Get list of OAuth providers configured for a tenant."""
        query = """
            SELECT provider_name 
            FROM tenant_external_oauth_tokens 
            WHERE entity_id = ?
            ORDER BY provider_name
        """
        rows = await self._fetchall(query, (entity_id,))
        return [row["provider_name"] for row in rows]


# Global singleton instance management
_sqlite_tenant_external_token_store_instance: Optional[SQLiteTenantExternalTokenStore] = None


async def get_sqlite_tenant_external_token_store() -> SQLiteTenantExternalTokenStore:
    """
    Get or create the singleton SQLiteTenantExternalTokenStore instance.
    Ensures only one instance exists throughout the application lifecycle.
    """
    global _sqlite_tenant_external_token_store_instance
    if _sqlite_tenant_external_token_store_instance is None:
        _sqlite_tenant_external_token_store_instance = SQLiteTenantExternalTokenStore()
        await _sqlite_tenant_external_token_store_instance.initialize()
    return _sqlite_tenant_external_token_store_instance 