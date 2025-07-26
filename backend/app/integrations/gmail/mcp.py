"""
This module contains the MCP server for the Gmail integration.
"""
import contextlib
import logging
from collections.abc import AsyncIterator

import click
import mcp.types as types
import uvicorn
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from sqlalchemy.orm import Session
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

from app.database.connection import SessionLocal
from app.models.user import UserInDB
from app.crud.user import get_user_by_id

from .tools import (
    get_gmail_service,
    get_google_credentials,
    get_last_received_email,
    search_gmail_messages,
    send_gmail_message,
)
import json

logger = logging.getLogger(__name__)

def get_db():
    """Create a new database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@click.command()
@click.option("--port", default=9001, help="Port to listen on for HTTP")
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

    app = Server("gmail-integration")

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.ContentBlock]:
        """Handles tool calls from the MCP client."""
        db: Session = next(get_db())
        user_id = arguments.pop("user_id", None)
        if not user_id:
            return [types.TextContent(type="text", text="user_id is a required argument")]

        user = get_user_by_id(db, user_id)
        if not user:
            return [types.TextContent(type="text", text=f"User with id {user_id} not found")]

        creds = get_google_credentials(user, user.id, db)
        if not creds:
            return [types.TextContent(type="text", text="Could not refresh Google credentials.")]

        service = get_gmail_service(creds)

        if name == "search_emails":
            messages = search_gmail_messages(service, arguments.get("query", ""))
            return [types.TextContent(type="text", text=json.dumps(messages))]
        elif name == "get_last_email":
            email = get_last_received_email(service)
            return [types.TextContent(type="text", text=json.dumps(email))]
        elif name == "send_email":
            result = send_gmail_message(
                service,
                user.email,
                arguments.get("to_email"),
                arguments.get("subject"),
                arguments.get("message_text"),
                arguments.get("thread_id"),
            )
            return [types.TextContent(type="text", text=json.dumps(result))]

        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """Lists the available tools for the Gmail integration."""
        return [
            types.Tool(
                name="search_emails",
                description="Search for emails in the user's Gmail account.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "user_id": {"type": "integer"},
                    },
                    "required": ["query", "user_id"],
                },
            ),
            types.Tool(
                name="get_last_email",
                description="Get the last received email from the user's Gmail account.",
                inputSchema={
                    "type": "object",
                    "properties": {"user_id": {"type": "integer"}},
                    "required": ["user_id"],
                },
            ),
            types.Tool(
                name="send_email",
                description="Send an email using the user's Gmail account.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to_email": {"type": "string"},
                        "subject": {"type": "string"},
                        "message_text": {"type": "string"},
                        "thread_id": {"type": "string"},
                        "user_id": {"type": "integer"},
                    },
                    "required": [
                        "to_email",
                        "subject",
                        "message_text",
                        "user_id",
                    ],
                },
            ),
        ]

    session_manager = StreamableHTTPSessionManager(app=app)

    async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
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
