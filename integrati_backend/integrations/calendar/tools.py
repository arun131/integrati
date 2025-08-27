"""Calendar MCP tools for calendar operations."""

import logging
from typing import Dict, Any, List, Optional
from fastmcp import Context as FastMCPBaseContext
from fastmcp.exceptions import ToolError
from mcp_plexus.core.global_registry import PLEXUS_SERVER_INSTANCE
from mcp_plexus.plexus_context import PlexusContext
from mcp_plexus.oauth.errors import PlexusExternalAuthRequiredError

from .api import CalendarAPI
from ..utils import PermissionHelper

logger = logging.getLogger(__name__)

# Import constants from separate file to avoid circular imports


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

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="get_calendar_events",
                tool_params={
                    "max_results": max_results,
                    "time_min": time_min,
                    "time_max": time_max,
                },
                no_access_response={
                    "events": [],
                    "count": 0,
                    "max_results": max_results,
                    "time_min": time_min,
                    "time_max": time_max,
                    "status_message": "You don't have permission to read calendar events with this configuration.",
                },
                restricted_access_response={
                    "events": [],
                    "count": 0,
                    "max_results": max_results,
                    "time_min": time_min,
                    "time_max": time_max,
                },
                approval_message="Your request to get calendar events was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            events = await calendar_api.get_events(max_results, time_min, time_max)

            return {
                "events": events,
                "count": len(events),
                "max_results": max_results,
                "time_min": time_min,
                "time_max": time_max,
                "status_message": "success",
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

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="create_calendar_event",
                tool_params={
                    "summary": summary,
                    "start_time": start_time,
                    "end_time": end_time,
                    "description": description,
                    "attendees": attendees,
                    "location": location,
                },
                no_access_response={
                    "event": None,
                    "status": "access_denied",
                    "message": "You don't have permission to create calendar events with this configuration.",
                    "status_message": "You don't have permission to create calendar events with this configuration.",
                },
                restricted_access_response={
                    "event": None,
                    "status": "approval_required",
                    "message": "Calendar event creation request sent for approval.",
                },
                approval_message=f"Your request to create calendar event '{summary}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            event = await calendar_api.create_event(
                summary, start_time, end_time, description, attendees, location
            )

            return {
                "event": event,
                "status": "created",
                "message": "Calendar event created successfully",
                "status_message": "success",
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

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="update_calendar_event",
                tool_params={
                    "event_id": event_id,
                    "summary": summary,
                    "start_time": start_time,
                    "end_time": end_time,
                    "description": description,
                    "location": location,
                },
                no_access_response={
                    "event": None,
                    "status": "access_denied",
                    "message": "You don't have permission to update calendar events with this configuration.",
                    "status_message": "You don't have permission to update calendar events with this configuration.",
                },
                restricted_access_response={
                    "event": None,
                    "status": "approval_required",
                    "message": "Calendar event update request sent for approval.",
                },
                approval_message=f"Your request to update calendar event {event_id} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            event = await calendar_api.update_event(
                event_id, summary, start_time, end_time, description, location
            )

            return {
                "event": event,
                "status": "updated",
                "message": "Calendar event updated successfully",
                "status_message": "success",
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

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="delete_calendar_event",
                tool_params={"event_id": event_id},
                no_access_response={
                    "status": "access_denied",
                    "event_id": event_id,
                    "message": "You don't have permission to delete calendar events with this configuration.",
                    "status_message": "You don't have permission to delete calendar events with this configuration.",
                },
                restricted_access_response={
                    "status": "approval_required",
                    "event_id": event_id,
                    "message": "Calendar event deletion request sent for approval.",
                },
                approval_message=f"Your request to delete calendar event {event_id} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            success = await calendar_api.delete_event(event_id)

            if success:
                return {
                    "status": "deleted",
                    "event_id": event_id,
                    "message": "Calendar event deleted successfully",
                    "status_message": "success",
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

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="get_calendar_event",
                tool_params={"event_id": event_id},
                no_access_response={
                    "event": None,
                    "found": False,
                    "message": "You don't have permission to read calendar events with this configuration.",
                    "status_message": "You don't have permission to read calendar events with this configuration.",
                },
                restricted_access_response={
                    "event": None,
                    "found": False,
                    "message": "Calendar event access request sent for approval.",
                },
                approval_message=f"Your request to get calendar event {event_id} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            event = await calendar_api.get_event(event_id)

            if event:
                return {"event": event, "found": True, "status_message": "success"}
            else:
                return {
                    "event": None,
                    "found": False,
                    "message": "Event not found",
                    "status_message": "success",
                }
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

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="search_calendar_events",
                tool_params={"query": query, "max_results": max_results},
                no_access_response={
                    "events": [],
                    "count": 0,
                    "query": query,
                    "max_results": max_results,
                    "status_message": "You don't have permission to search calendar events with this configuration.",
                },
                restricted_access_response={
                    "events": [],
                    "count": 0,
                    "query": query,
                    "max_results": max_results,
                },
                approval_message=f"Your request to search calendar events with query '{query}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            events = await calendar_api.search_events(query, max_results)

            return {
                "events": events,
                "count": len(events),
                "query": query,
                "max_results": max_results,
                "status_message": "success",
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

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="get_upcoming_events",
                tool_params={"days": days},
                no_access_response={
                    "events": [],
                    "count": 0,
                    "days": days,
                    "message": "You don't have permission to read calendar events with this configuration.",
                    "status_message": "You don't have permission to read calendar events with this configuration.",
                },
                restricted_access_response={
                    "events": [],
                    "count": 0,
                    "days": days,
                    "message": "Upcoming events request sent for approval.",
                },
                approval_message=f"Your request to get upcoming events for the next {days} days was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            events = await calendar_api.get_upcoming_events(days)

            return {
                "events": events,
                "count": len(events),
                "days": days,
                "message": f"Upcoming events for the next {days} days",
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            raise ToolError(f"Error getting upcoming events: {str(e)}")
