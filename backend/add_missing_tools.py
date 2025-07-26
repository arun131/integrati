#!/usr/bin/env python3
"""
Script to add missing tools for existing integrations.
"""

from app.crud.integration import get_user_integrations
from app.crud.tool import create_user_tool, get_user_tools
from app.database.connection import SessionLocal
from app.models.user import User


def add_missing_tools():
    db = SessionLocal()
    try:
        # Get all users
        users = db.query(User).all()

        for user in users:
            print(f"Processing user: {user.email}")

            # Get user's integrations
            integrations = get_user_integrations(db, user.id)

            for integration in integrations:
                print(f"  Processing integration: {integration.integration_name}")

                # Get existing tools for this integration
                existing_tools = get_user_tools(
                    db, user.id, integration.integration_name
                )
                existing_tool_names = [tool.tool_name for tool in existing_tools]

                # Define tools to create based on integration
                tools_to_create = []
                if integration.integration_name == "gmail":
                    tools_to_create = ["search_emails", "get_last_email", "send_email"]
                elif integration.integration_name == "calendar":
                    tools_to_create = [
                        "get_calendar_events",
                        "create_calendar_event",
                        "delete_calendar_event",
                    ]

                # Create missing tools
                for tool_name in tools_to_create:
                    if tool_name not in existing_tool_names:
                        print(f"    Creating tool: {tool_name}")
                        create_user_tool(
                            db,
                            user.id,
                            integration.integration_name,
                            tool_name,
                            "enabled",
                        )
                    else:
                        print(f"    Tool already exists: {tool_name}")

        print("Finished adding missing tools.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    add_missing_tools()
