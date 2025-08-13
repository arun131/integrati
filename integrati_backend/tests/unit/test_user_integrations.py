"""Unit tests covering user integration persistence and schema.

These simple tests exercise the new `user_integrations` table as well as
`get_mcp_tools_list_for_tenant` aggregation behaviour in an isolated,
file-backed SQLite database.  They do **not** touch external services.
"""

from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch

import pytest

# Import after sys.path manipulation is not necessary: tests live under the
# same package root as code. The storage module uses `settings.sqlite_db_path`,
# so we set it to our temporary DB.
from mcp_plexus.storage.sqlite_base import (
    get_sqlite_db_connection,
    init_sqlite_db,
)
from mcp_plexus.core.server import MCPPlexusServer
from fastmcp import FastMCP


@pytest.fixture(name="tmp_db_path")
def _tmp_db_path(monkeypatch):
    """Creates a temporary file and points settings.sqlite_db_path to it."""

    # Create a temporary directory with proper permissions
    temp_dir = tempfile.mkdtemp()
    db_str = str(Path(temp_dir) / "test.db")

    # Patch settings variable used by storage layer
    from mcp_plexus.settings import settings as plexus_settings

    monkeypatch.setattr(plexus_settings, "sqlite_db_path", db_str, raising=False)

    # Clean up the global connection to force a new one
    import mcp_plexus.storage.sqlite_base as sqlite_base

    sqlite_base._db_connection = None

    yield db_str

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_user_integrations_schema(tmp_db_path):
    """Ensure the user_integrations table exists after init."""

    conn: sqlite3.Connection = await get_sqlite_db_connection()
    await init_sqlite_db(conn)

    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_integrations'"
    )
    row = cur.fetchone()
    assert row is not None, "user_integrations table should exist"


@pytest.mark.asyncio
async def test_tool_aggregation_empty(tmp_db_path):
    """Server returns only core tools when no integrations are connected."""

    # Create a new FastMCP instance for testing
    fastmcp_instance = FastMCP()

    # Register common tools manually for testing
    from integrations.common.tools import CommonTools

    # Register the tools with the FastMCP instance
    @fastmcp_instance.tool()
    async def add_numbers(a: float, b: float) -> float:
        return await CommonTools.add_numbers(a, b)

    @fastmcp_instance.tool()
    async def sum_list(numbers: list) -> float:
        return await CommonTools.sum_list(numbers)

    server = MCPPlexusServer()
    server._fastmcp_instance = fastmcp_instance

    tools = await server.get_mcp_tools_list_for_tenant("tenant_abc")
    connector_tool_names = [t.name for t in tools]

    # Expect core math tools at least, connector tools absent
    assert "add_numbers" in connector_tool_names  # core tool
    assert "get_unread_email_count" not in connector_tool_names


@pytest.mark.asyncio
async def test_tool_aggregation_after_integration(tmp_db_path):
    """After inserting a connected integration, Gmail tools appear."""

    # Get a fresh connection and initialize the database
    conn: sqlite3.Connection = await get_sqlite_db_connection()
    await init_sqlite_db(conn)

    # Insert test data
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_integrations (entity_id, connector, status, connected_at)
        VALUES ('tenant_xyz', 'gmail', 'connected', datetime('now'))
        """
    )
    conn.commit()

    # Don't close the connection as it's managed globally

    # Create a new FastMCP instance for testing
    fastmcp_instance = FastMCP()

    # Register common tools manually for testing
    from integrations.common.tools import CommonTools

    # Register the tools with the FastMCP instance
    @fastmcp_instance.tool()
    async def add_numbers(a: float, b: float) -> float:
        return await CommonTools.add_numbers(a, b)

    # Mock Gmail tools for testing
    @fastmcp_instance.tool()
    async def get_unread_email_count(user_id: str) -> int:
        return 5  # Mock return value

    server = MCPPlexusServer()
    server._fastmcp_instance = fastmcp_instance

    # Mock the OAuth status to return Gmail as connected
    with patch.object(
        server,
        "_get_tenant_oauth_status",
        return_value={"gmail": True, "calendar": False},
    ):
        tools = await server.get_mcp_tools_list_for_tenant("tenant_xyz")
        names = [t.name for t in tools]

        assert "get_unread_email_count" in names, "Gmail tools should be aggregated"
