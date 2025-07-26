"""
This module contains the MCP server for the Google Calendar integration.
"""

from collections.abc import AsyncIterator
import contextlib
import logging

import click
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
import mcp.types as types
from sqlalchemy.orm import Session
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send
import uvicorn

from app.crud.user import get_user_by_id
from app.database.connection import SessionLocal
from app.models.user import UserInDB

from .tools import (
    create_calendar_event,
    delete_calendar_event,
    get_calendar_events,
    get_calendar_service,
    get_google_credentials,
)

logger = logging.getLogger(__name__)


def get_db():
    """Create a new database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@click.command()
@click.option("--port", default=9002, help="Port to listen on for HTTP")
@click.option(
    "--log-level",
    default="INFO",
    help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
)
def main(port: int, log_level: str):
    """Main function to run the MCP server."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app = Server("calendar-integration")

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.ContentBlock]:
        """Handles tool calls from the MCP client."""
        db: Session = next(get_db())
        user_id = arguments.pop("user_id", None)
        if not user_id:
            return [
                types.TextContent(type="text", text="user_id is a required argument")
            ]

        user = get_user_by_id(db, user_id)
        if not user:
            return [
                types.TextContent(type="text", text=f"User with id {user_id} not found")
            ]

        creds = get_google_credentials(user.dict(), user.id, db)
        if not creds:
            return [
                types.TextContent(
                    type="text", text="Could not refresh Google credentials."
                )
            ]

        service = get_calendar_service(creds)

        if name == "get_calendar_events":
            events = get_calendar_events(service)
            return [types.JsonContent(data=events)]
        elif name == "create_calendar_event":
            event = create_calendar_event(
                service=service,
                summary=arguments.get("summary"),
                start_time=arguments.get("start_time"),
                end_time=arguments.get("end_time"),
                description=arguments.get("description"),
                attendees=arguments.get("attendees"),
            )
            return [types.JsonContent(data=event)]
        elif name == "delete_calendar_event":
            delete_calendar_event(service, arguments.get("event_id"))
            return [types.TextContent(text="Event deleted successfully.")]

        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """Lists the available tools for the Calendar integration."""
        return [
            types.Tool(
                name="get_calendar_events",
                description="Get events from the user's primary Google Calendar.",
                inputSchema={
                    "type": "object",
                    "properties": {"user_id": {"type": "integer"}},
                    "required": ["user_id"],
                },
            ),
            types.Tool(
                name="create_calendar_event",
                description="Creates a new event on the user's primary Google Calendar.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "start_time": {"type": "string", "format": "date-time"},
                        "end_time": {"type": "string", "format": "date-time"},
                        "description": {"type": "string"},
                        "attendees": {"type": "array", "items": {"type": "string"}},
                        "user_id": {"type": "integer"},
                    },
                    "required": ["summary", "start_time", "end_time", "user_id"],
                },
            ),
            types.Tool(
                name="delete_calendar_event",
                description="Deletes an event from the user's primary Google Calendar.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string"},
                        "user_id": {"type": "integer"},
                    },
                    "required": ["event_id", "user_id"],
                },
            ),
        ]

    session_manager = StreamableHTTPSessionManager(app=app)

    async def handle_streamable_http(
        scope: Scope, receive: Receive, send: Send
    ) -> None:
        """Handle streamable HTTP connections."""
        await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Context manager for managing session manager lifecycle."""
        async with session_manager.run():
            logger.info("Application started with StreamableHTTP session manager!")
            try:
                yield
            finally:
                logger.info("Application shutting down...")

    starlette_app = Starlette(
        debug=True,
        routes=[Mount("/mcp", app=handle_streamable_http)],
        lifespan=lifespan,
    )

    uvicorn.run(starlette_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
