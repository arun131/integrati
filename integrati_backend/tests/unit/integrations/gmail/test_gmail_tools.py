"""Unit-ish tests for Gmail tool wrappers.

We mock GmailAPI so the tool coroutine can execute without hitting Google.
Only logic internal to the tool function is exercised: context extraction,
error handling around missing user_id, and correct return formatting.
"""

from types import SimpleNamespace
from typing import Any, Dict

import pytest

# Patch global PLEXUS_SERVER_INSTANCE before importing tools
from mcp_plexus.core import global_registry


class _StubServer:
    def tool(self):
        def _decorator(fn):
            return fn

        return _decorator


global_registry.PLEXUS_SERVER_INSTANCE = _StubServer()

# target module
from integrations.gmail import tools as gmail_tools  # noqa: E402


# Helpers ---------------------------------------------------------------
class DummyFastMCP:  # minimal object with .__init__ signature
    pass


class FakeCtx(SimpleNamespace):
    """Fake FastMCP Context providing only fastmcp attribute."""

    def __init__(self):
        super().__init__(fastmcp=DummyFastMCP())


@pytest.fixture()
def patched_gmail_api(monkeypatch):
    """Patch GmailAPI used inside tool functions to a stub class."""

    class _Stub:
        def __init__(self, *_, **__):
            pass

        async def get_unread_count(self):
            return 7

        async def get_last_received_email(self):
            return {"id": "123", "snippet": "Hello"}

    monkeypatch.setattr(gmail_tools, "GmailAPI", _Stub)
    return _Stub


# Tests ----------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_unread_email_count_ok(monkeypatch, patched_gmail_api):
    ctx = FakeCtx()

    # patch PlexusContext so .entity_id and .user_id present
    class DummyPlexus(SimpleNamespace):
        entity_id = "tenant_1"
        user_id = "user_1"

    monkeypatch.setattr(gmail_tools, "PlexusContext", lambda _: DummyPlexus)

    result: Dict[str, Any] = await gmail_tools.GmailTools.get_unread_email_count(ctx)
    assert result == {"unread_count": 7, "status": "success"}


@pytest.mark.asyncio
async def test_get_unread_email_count_missing_user(monkeypatch):
    ctx = FakeCtx()

    class DummyPlexus(SimpleNamespace):
        entity_id = "tenant_1"
        user_id = None  # simulate missing

    monkeypatch.setattr(gmail_tools, "PlexusContext", lambda _: DummyPlexus)

    with pytest.raises(gmail_tools.ToolError):
        await gmail_tools.GmailTools.get_unread_email_count(ctx)
