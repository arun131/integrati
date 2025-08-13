"""Calendar MCP tools for calendar operations."""

import logging
from typing import Dict, Any, List, Optional
from fastmcp import Context as FastMCPBaseContext
from fastmcp.exceptions import ToolError
from mcp_plexus.core.global_registry import PLEXUS_SERVER_INSTANCE
from mcp_plexus.plexus_context import PlexusContext
from mcp_plexus.oauth.errors import PlexusExternalAuthRequiredError

from .api import CalendarAPI

logger = logging.getLogger(__name__)


class CalendarTools:
    """Class containing Calendar operations as MCP tools."""

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def get_calendar_events(
        ctx: FastMCPBaseContext,
        max_results: int = 10,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get calendar events for the specified time range."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            calendar_api = CalendarAPI(entity_id, user_id)
            events = await calendar_api.get_events(max_results, time_min, time_max)

            return {
                "events": events,
                "count": len(events),
                "max_results": max_results,
                "time_min": time_min,
                "time_max": time_max,
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error getting calendar events: {e}")
            raise ToolError(f"Error getting calendar events: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def create_calendar_event(
        ctx: FastMCPBaseContext,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        attendees: Optional[List[str]] = None,
        location: str = "",
    ) -> Dict[str, Any]:
        """Create a new calendar event."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            calendar_api = CalendarAPI(entity_id, user_id)
            event = await calendar_api.create_event(
                summary, start_time, end_time, description, attendees, location
            )

            return {
                "event": event,
                "status": "created",
                "message": "Calendar event created successfully",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            raise ToolError(f"Error creating calendar event: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def update_calendar_event(
        ctx: FastMCPBaseContext,
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing calendar event."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            calendar_api = CalendarAPI(entity_id, user_id)
            event = await calendar_api.update_event(
                event_id, summary, start_time, end_time, description, location
            )

            return {
                "event": event,
                "status": "updated",
                "message": "Calendar event updated successfully",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error updating calendar event: {e}")
            raise ToolError(f"Error updating calendar event: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def delete_calendar_event(
        ctx: FastMCPBaseContext, event_id: str
    ) -> Dict[str, Any]:
        """Delete a calendar event."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            calendar_api = CalendarAPI(entity_id, user_id)
            success = await calendar_api.delete_event(event_id)

            if success:
                return {
                    "status": "deleted",
                    "event_id": event_id,
                    "message": "Calendar event deleted successfully",
                }
            else:
                raise ToolError("Failed to delete calendar event")
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error deleting calendar event: {e}")
            raise ToolError(f"Error deleting calendar event: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def get_calendar_event(
        ctx: FastMCPBaseContext, event_id: str
    ) -> Dict[str, Any]:
        """Get a specific calendar event by ID."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            calendar_api = CalendarAPI(entity_id, user_id)
            event = await calendar_api.get_event(event_id)

            if event:
                return {"event": event, "found": True}
            else:
                return {"event": None, "found": False, "message": "Event not found"}
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error getting calendar event: {e}")
            raise ToolError(f"Error getting calendar event: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def search_calendar_events(
        ctx: FastMCPBaseContext, query: str, max_results: int = 10
    ) -> Dict[str, Any]:
        """Search calendar events by query."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            calendar_api = CalendarAPI(entity_id, user_id)
            events = await calendar_api.search_events(query, max_results)

            return {
                "events": events,
                "count": len(events),
                "query": query,
                "max_results": max_results,
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error searching calendar events: {e}")
            raise ToolError(f"Error searching calendar events: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def get_upcoming_events(
        ctx: FastMCPBaseContext, days: int = 7
    ) -> Dict[str, Any]:
        """Get upcoming events for the next N days."""
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            calendar_api = CalendarAPI(entity_id, user_id)
            events = await calendar_api.get_upcoming_events(days)

            return {
                "events": events,
                "count": len(events),
                "days": days,
                "message": f"Upcoming events for the next {days} days",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            raise ToolError(f"Error getting upcoming events: {str(e)}")
