"""Pure unit tests for mcp_plexus.storage.sqlite_base.

These tests purposely avoid going through higher-level server code so they
exercise individual helper functions only.
"""

import importlib

import pytest

# Reload module under modified settings each time so the global connection is
# recreated against a fresh DB file.
MODULE_PATH = "mcp_plexus.storage.sqlite_base"


def _load_module(db_path: str):  # helper
    """Reload the storage module with a patched settings.sqlite_db_path."""
    from mcp_plexus.settings import settings as plexus_settings

    plexus_settings.sqlite_db_path = db_path  # type: ignore[attr-defined]
    if MODULE_PATH in importlib.sys.modules:
        del importlib.sys.modules[MODULE_PATH]
    return importlib.import_module(MODULE_PATH)


@pytest.fixture()
def fresh_storage_module(tmp_path):
    db_file = tmp_path / "unit_test.db"
    mod = _load_module(str(db_file))
    yield mod
    # Close connection after test to release file handle
    importlib.reload(mod)  # ensures close on module reload


@pytest.mark.asyncio
async def test_init_sqlite_creates_tables(fresh_storage_module):
    """Verify that expected core tables are created."""
    storage = fresh_storage_module

    tables_expected = {
        "plexus_user_auth_tokens",
        "tenant_external_oauth_tokens",
        "plexus_tenants",
        "user_integrations",
    }
    conn = await storage.get_sqlite_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    present = {row[0] for row in cursor.fetchall()}

    missing = tables_expected - present
    assert not missing, f"Missing tables: {missing}"
