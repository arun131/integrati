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
    async def get_events(
        ctx: FastMCPBaseContext,
        search_type: str = "upcoming",
        event_id: Optional[str] = None,
        calendar_id: str = "primary",
        max_results: int = 10,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        query: Optional[str] = None,
        show_deleted: bool = False,
        single_events: bool = True,
        order_by: str = "startTime",
        days: int = 7,
    ) -> Dict[str, Any]:
        """Unified function for retrieving calendar events with flexible search options.

        Args:
            search_type: Type of search to perform. Options:
                - "upcoming": Get events for the next N days (default 7 days)
                - "advanced": Advanced filtering with full parameter control
                - "search": Text search across event content
                - "single": Get a specific event by ID
            event_id: Event ID for single event retrieval (required when search_type="single")
            calendar_id: Calendar ID to fetch events from (default: "primary")
            max_results: Maximum number of events to return (default: 10)
            time_min: Start time for events (ISO format, for advanced search)
            time_max: End time for events (ISO format, for advanced search)
            query: Free text search query to filter events (for search type)
            show_deleted: Whether to include deleted events (default: False)
            single_events: Whether to expand recurring events (default: True)
            order_by: Sort order - "startTime" or "updated" (default: "startTime")
            days: Number of days for upcoming events search (default: 7)

        Returns:
            Dict containing:
            - events: List of matching events (for upcoming/advanced/search types)
            - calendar_id: Calendar ID used for the search

        Examples:
            # Get upcoming events for next 7 days
            get_events(search_type="upcoming", days=7)

            # Advanced search with time filters
            get_events(search_type="advanced", time_min="2024-01-01T00:00:00Z", max_results=50)

            # Text search
            get_events(search_type="search", query="meeting", max_results=20)

            # Get single event
            get_events(search_type="single", event_id="event123")
        """
        try:
            # Validate search type
            supported_types = ["upcoming", "advanced", "search", "single"]
            if search_type not in supported_types:
                raise ToolError(
                    f"Unsupported search_type: {search_type}. Supported: {supported_types}"
                )

            # Validate event_id for single search
            if search_type == "single" and not event_id:
                raise ToolError("event_id is required when search_type='single'")

            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id

            user_id = getattr(plexus_ctx, "user_id", None)
            if not user_id:
                raise ToolError("User ID not available in context")

            # Build tool parameters based on search type
            tool_params = {
                "search_type": search_type,
                "calendar_id": calendar_id,
                "max_results": max_results,
            }

            if search_type == "single":
                tool_params["event_id"] = event_id
            elif search_type == "search":
                tool_params["query"] = query
            elif search_type == "upcoming":
                tool_params["days"] = days
            elif search_type == "advanced":
                tool_params.update(
                    {
                        "time_min": time_min,
                        "time_max": time_max,
                        "query": query,
                    }
                )

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="get_events",
                tool_params=tool_params,
                no_access_response={
                    "events": [] if search_type != "single" else None,
                    "event": None if search_type == "single" else None,
                    "count": 0,
                    "found": False if search_type == "single" else None,
                    "search_type": search_type,
                    "calendar_id": calendar_id,
                    "status_message": "You don't have permission to read calendar events with this configuration.",
                },
                restricted_access_response={
                    "events": [] if search_type != "single" else None,
                    "event": None if search_type == "single" else None,
                    "count": 0,
                    "found": False if search_type == "single" else None,
                    "search_type": search_type,
                    "calendar_id": calendar_id,
                    "status_message": f"The tool request with details {{'search_type': '{search_type}'}} is sent to the user and they can approve it on the app.",
                },
                approval_message=f"Your request to get calendar events with search_type '{search_type}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)

            # Execute appropriate search based on type
            if search_type == "single":
                event = await calendar_api.get_event(event_id, calendar_id)
                if event:
                    return {
                        "event": event,
                        "found": True,
                        "search_type": search_type,
                        "event_id": event_id,
                        "status_message": "success",
                    }
                else:
                    return {
                        "event": None,
                        "found": False,
                        "search_type": search_type,
                        "event_id": event_id,
                        "message": "Event not found",
                        "status_message": "success",
                    }

            elif search_type == "search":
                events = await calendar_api.search_events(query, max_results)
                return {
                    "events": events,
                    "count": len(events),
                    "search_type": search_type,
                    "query": query,
                    "calendar_id": calendar_id,
                    "max_results": max_results,
                    "status_message": "success",
                }

            elif search_type == "upcoming":
                events = await calendar_api.get_upcoming_events(days)
                return {
                    "events": events,
                    "count": len(events),
                    "search_type": search_type,
                    "days": days,
                    "calendar_id": calendar_id,
                    "message": f"Upcoming events for the next {days} days",
                    "status_message": "success",
                }

            elif search_type == "advanced":
                result = await calendar_api.get_events_advanced(
                    calendar_id=calendar_id,
                    max_results=max_results,
                    time_min=time_min,
                    time_max=time_max,
                    query=query,
                    show_deleted=show_deleted,
                    single_events=single_events,
                    order_by=order_by,
                )
                return {
                    "events": result["events"],
                    "count": result["count"],
                    "search_type": search_type,
                    "calendar_id": calendar_id,
                    "max_results": max_results,
                    "time_min": time_min,
                    "time_max": time_max,
                    "query": query,
                    "next_page_token": result.get("next_page_token"),
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
    async def create_event(
        ctx: FastMCPBaseContext,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        attendees: Optional[List[str]] = None,
        location: str = "",
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        """Create a new calendar event.

        This function creates a new calendar event with the specified details.
        Requires appropriate permissions for event creation.

        Args:
            summary: Event title/summary
            start_time: Event start time (ISO format)
            end_time: Event end time (ISO format)
            description: Event description (optional)
            attendees: List of attendee email addresses (optional)
            location: Event location (optional)
            calendar_id: Calendar ID to create event in (default: "primary")
        """
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
                tool_name="create_event",
                tool_params={
                    "summary": summary,
                    "start_time": start_time,
                    "end_time": end_time,
                    "description": description,
                    "attendees": attendees,
                    "location": location,
                    "calendar_id": calendar_id,
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
                    "status_message": f"The tool request with details {{'summary': '{summary}'}} is sent to the user and they can approve it on the app.",
                },
                approval_message=f"Your request to create calendar event '{summary}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            event = await calendar_api.create_event(
                summary,
                start_time,
                end_time,
                description,
                attendees,
                location,
                calendar_id,
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
    async def update_event(
        ctx: FastMCPBaseContext,
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        """Update an existing calendar event or add attendees.

        This function provides comprehensive event update capabilities including
        modifying event details and managing attendee lists.

        Args:
            event_id: ID of the event to update
            summary: New event title/summary (optional)
            start_time: New start time (ISO format, optional)
            end_time: New end time (ISO format, optional)
            description: New description (optional)
            location: New location (optional)
            attendees: List of attendee emails to add (optional)
            calendar_id: Calendar ID containing the event (default: "primary")
        """
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
                tool_name="update_event",
                tool_params={
                    "event_id": event_id,
                    "summary": summary,
                    "start_time": start_time,
                    "end_time": end_time,
                    "description": description,
                    "location": location,
                    "attendees": attendees,
                    "calendar_id": calendar_id,
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
                    "status_message": f"The tool request with details {{'event_id': '{event_id}'}} is sent to the user and they can approve it on the app.",
                },
                approval_message=f"Your request to update calendar event {event_id} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)

            # Determine operation type based on parameters
            if attendees and not any(
                [summary, start_time, end_time, description, location]
            ):
                # Add attendees only
                event = await calendar_api.add_event_attendees(
                    event_id, attendees, calendar_id
                )
                return {
                    "event": event,
                    "status": "updated",
                    "message": f"Added {len(attendees)} attendees to event",
                    "added_attendees": attendees,
                    "status_message": "success",
                }
            else:
                # Full event update
                event = await calendar_api.update_event(
                    event_id,
                    summary,
                    start_time,
                    end_time,
                    description,
                    location,
                    calendar_id,
                )

                # Also add attendees if specified
                if attendees:
                    event = await calendar_api.add_event_attendees(
                        event_id, attendees, calendar_id
                    )

                added_attendees = attendees if attendees else []
            return {
                "event": event,
                "status": "updated",
                "message": "Calendar event updated successfully",
                "added_attendees": added_attendees,
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
    async def delete_event(
        ctx: FastMCPBaseContext, event_id: str, calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Delete a calendar event.

        This function permanently removes a calendar event from the specified calendar.
        Requires appropriate permissions for event deletion.

        Args:
            event_id: ID of the event to delete
            calendar_id: Calendar ID containing the event (default: "primary")
        """
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
                tool_name="delete_event",
                tool_params={"event_id": event_id, "calendar_id": calendar_id},
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
                    "status_message": f"The tool request with details {{'event_id': '{event_id}'}} is sent to the user and they can approve it on the app.",
                },
                approval_message=f"Your request to delete calendar event {event_id} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            success = await calendar_api.delete_event(event_id, calendar_id)

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
    async def list_calendars(ctx: FastMCPBaseContext) -> Dict[str, Any]:
        """List all calendars available to the authenticated user.

        This function retrieves a comprehensive list of all calendars that the user has access to,
        including their primary calendar and any shared calendars. Each calendar entry includes
        metadata such as access roles, colors, and visibility settings.

        """
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
                tool_name="list_calendars",
                tool_params={},
                no_access_response={"calendars": [], "count": 0},
                restricted_access_response={"calendars": [], "count": 0},
                approval_message="Your request to list calendars was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            calendars = await calendar_api.list_calendars()

            return {
                "calendars": calendars,
                "count": len(calendars),
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error listing calendars: {e}")
            raise ToolError(f"Error listing calendars: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def create_calendar(
        ctx: FastMCPBaseContext, name: str, description: str = "", timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """Create a new calendar for the authenticated user.

        This function creates a new calendar with the specified name, description, and timezone.
        The user will have owner access to the newly created calendar and can share it with others.

        Args:
            name: Name of the new calendar (required)
            description: Optional description for the calendar (default: empty string)
            timezone: Timezone for the calendar in IANA format (default: "UTC")
                      Examples: "America/New_York", "Europe/London", "Asia/Tokyo"
        """
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
                tool_name="create_calendar",
                tool_params={
                    "name": name,
                    "description": description,
                    "timezone": timezone,
                },
                no_access_response={"calendar": None, "status": "access_denied"},
                restricted_access_response={
                    "calendar": None,
                    "status": "approval_required",
                },
                approval_message=f"Your request to create calendar '{name}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            created_calendar = await calendar_api.create_calendar(
                name, description, timezone
            )

            return {
                "calendar": created_calendar,
                "status": "created",
                "message": f"Calendar '{name}' created successfully",
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error creating calendar: {e}")
            raise ToolError(f"Error creating calendar: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def quick_add_event_from_text(
        ctx: FastMCPBaseContext, text: str, calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Quick-add an event from natural language text using AI parsing.

        This function leverages Google's natural language processing capabilities to automatically
        parse event details from plain English text and create calendar events. It's particularly
        useful for creating events from voice-to-text transcriptions or casual descriptions.

        Args:
            text: Natural language description of the event. Examples:
                  - "Meeting with John tomorrow at 3pm for 1 hour"
                  - "Dentist appointment next Tuesday at 10am"
                  - "Team lunch on Friday at noon for 90 minutes"
                  - "Project deadline on March 15th"
            calendar_id: Calendar ID to add event to (default: "primary")

        Note:
            The AI parsing is quite sophisticated and can understand relative dates (tomorrow, next week),
            times (3pm, 10am), durations (1 hour, 90 minutes), and various event types.
        """
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
                tool_name="quick_add_event_from_text",
                tool_params={"text": text, "calendar_id": calendar_id},
                no_access_response={"event": None, "status": "access_denied"},
                restricted_access_response={
                    "event": None,
                    "status": "approval_required",
                },
                approval_message="Your request to quick-add event from text was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            event = await calendar_api.quick_add_event(text, calendar_id)

            return {
                "event": event,
                "status": "created",
                "message": f"Event created from text: '{text}'",
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error quick-adding event: {e}")
            raise ToolError(f"Error creating event from text: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def check_attendee_status(
        ctx: FastMCPBaseContext, event_id: str, calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Check the response status of attendees for a calendar event.

        This function retrieves detailed information about how invited attendees have responded
        to a calendar event invitation. It provides insights into who has accepted, declined,
        or not yet responded to the event.

        Args:
            event_id: ID of the event to check attendee status for
            calendar_id: Calendar ID containing the event (default: "primary")
        """
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
                tool_name="check_attendee_status",
                tool_params={"event_id": event_id, "calendar_id": calendar_id},
                no_access_response={"attendees": [], "status": "access_denied"},
                restricted_access_response={
                    "attendees": [],
                    "status": "approval_required",
                },
                approval_message=f"Your request to check attendee status for event {event_id} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            result = await calendar_api.get_attendee_status(event_id, calendar_id)

            return {
                "event_id": event_id,
                "event_summary": result["event_summary"],
                "attendees": result["attendees"],
                "attendee_count": result["attendee_count"],
                "status_counts": result["status_counts"],
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error checking attendee status: {e}")
            raise ToolError(f"Error checking attendee status: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def query_free_busy(
        ctx: FastMCPBaseContext, calendar_ids: List[str], time_min: str, time_max: str
    ) -> Dict[str, Any]:
        """Query free/busy availability information for multiple calendars.

        This function checks the availability status of multiple calendars over a specified time period.
        It's useful for finding suitable meeting times across different participants' schedules.
        The function returns busy time blocks for each calendar without revealing actual event details.

        Args:
            calendar_ids: List of calendar IDs to check availability for. Can include:
                         - Primary calendar: "primary"
                         - Specific calendar IDs
                         - Shared calendars the user has access to
            time_min: Start time for the query in ISO 8601 format (e.g., "2024-01-01T09:00:00Z")
            time_max: End time for the query in ISO 8601 format (e.g., "2024-01-01T17:00:00Z")

        Returns:
            Dict containing:
            - calendars: Dictionary mapping calendar IDs to their free/busy information:
              * Each calendar entry contains busy time periods as arrays of [start, end] time pairs
              * Example: {"primary": [["2024-01-01T10:00:00Z", "2024-01-01T11:00:00Z"]]}
            - query_time_min: The start time used for the query
            - query_time_max: The end time used for the query
            - calendar_count: Number of calendars queried
            - status_message: Operation status ("success", "access_denied", or approval message)

        Note:
            Free/busy information only shows when calendars are busy, not the actual event details.
            This respects privacy by not revealing event titles, attendees, or other sensitive information.
        """
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
                tool_name="query_free_busy",
                tool_params={
                    "calendar_ids": calendar_ids,
                    "time_min": time_min,
                    "time_max": time_max,
                },
                no_access_response={"calendars": {}, "status": "access_denied"},
                restricted_access_response={
                    "calendars": {},
                    "status": "approval_required",
                },
                approval_message="Your request to query free/busy information was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            calendars_freebusy = await calendar_api.query_freebusy(
                calendar_ids, time_min, time_max
            )

            return {
                "calendars": calendars_freebusy,
                "query_time_min": time_min,
                "query_time_max": time_max,
                "calendar_count": len(calendar_ids),
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error querying free/busy: {e}")
            raise ToolError(f"Error querying free/busy information: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def schedule_mutual(
        ctx: FastMCPBaseContext,
        calendar_ids: List[str],
        duration_minutes: int,
        search_days: int = 7,
        summary: str = "Meeting",
        description: str = "",
        working_hours_start: int = 9,
        working_hours_end: int = 17,
    ) -> Dict[str, Any]:
        """Find mutual free time slots and schedule meetings automatically.

        This function analyzes free/busy information across multiple calendars to identify
        the best available time slots for scheduling meetings with all participants.
        It automatically creates the meeting event in the first available suitable time slot.

        Args:
            calendar_ids: List of calendar IDs to check for mutual availability. Should include
                         all participants' calendars to ensure everyone is available.
            duration_minutes: Duration of the meeting in minutes (e.g., 30, 60, 90)
            search_days: Number of days to search forward from today (default: 7)
            summary: Title/summary for the meeting event (default: "Meeting")
            description: Description/details of the meeting (default: empty)
            working_hours_start: Start of working hours in 24-hour format (default: 9 for 9:00 AM)
            working_hours_end: End of working hours in 24-hour format (default: 17 for 5:00 PM)

        Note:
            The function respects working hours and will only suggest time slots during the
            specified working hours. It prioritizes earlier time slots when multiple options exist.
        """
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
                tool_name="schedule_mutual",
                tool_params={
                    "calendar_ids": calendar_ids,
                    "duration_minutes": duration_minutes,
                    "search_days": search_days,
                    "summary": summary,
                },
                no_access_response={"free_slots": [], "status": "access_denied"},
                restricted_access_response={
                    "free_slots": [],
                    "status": "approval_required",
                },
                approval_message="Your request to find mutual free time for scheduling was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            result = await calendar_api.schedule_mutual(
                calendar_ids,
                duration_minutes,
                search_days,
                summary,
                description,
                working_hours_start,
                working_hours_end,
            )

            return result
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error scheduling mutual meeting: {e}")
            raise ToolError(f"Error scheduling mutual meeting: {str(e)}")

    @staticmethod
    @PLEXUS_SERVER_INSTANCE.tool()
    async def analyze_busyness(
        ctx: FastMCPBaseContext, days: int = 7, calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Analyze calendar activity patterns and busyness levels.

        This function provides comprehensive insights into calendar usage patterns including
        event frequency, time allocation, and activity distribution. It's useful for understanding
        work-life balance, productivity patterns, and scheduling optimization.

        Args:
            days: Number of days to analyze, looking backward from today (default: 7)
            calendar_id: Calendar ID to analyze (default: "primary")

        Note:
            Analysis includes all-day events and calculates utilization based on standard
            working hours (9 AM - 5 PM). Weekends are included in the analysis but marked
            separately in the daily breakdown.
        """
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
                tool_name="analyze_busyness",
                tool_params={"days": days, "calendar_id": calendar_id},
                no_access_response={"analysis": {}, "status": "access_denied"},
                restricted_access_response={
                    "analysis": {},
                    "status": "approval_required",
                },
                approval_message="Your request to analyze calendar busyness was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="calendar",
            )

            if permission_result is not None:
                return permission_result

            calendar_api = CalendarAPI(entity_id, user_id)
            analysis = await calendar_api.analyze_busyness(days, calendar_id)

            return {
                "analysis": analysis,
                "calendar_id": calendar_id,
                "analysis_period_days": days,
                "status_message": "success",
            }
        except PlexusExternalAuthRequiredError:
            raise ToolError(
                "Calendar integration not authenticated. Please add Calendar integration first."
            )
        except Exception as e:
            logger.error(f"Error analyzing busyness: {e}")
            raise ToolError(f"Error analyzing calendar busyness: {str(e)}")
