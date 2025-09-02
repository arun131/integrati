"""Calendar API wrapper for calendar operations."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .unified_auth import UnifiedCalendarAuth
from mcp_plexus.oauth.errors import PlexusExternalAuthRequiredError

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS (for advanced calendar operations)
# ============================================================================


def _parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string and ensure it's timezone-aware."""
    try:
        # Try parsing with timezone info
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        # Fallback to naive datetime, assume UTC
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt


def _find_free_slots(
    busy_periods: List[Dict[str, Any]],
    duration_minutes: int,
    start_time: datetime,
    end_time: datetime,
    working_hours_start: int = 9,
    working_hours_end: int = 17,
) -> List[Dict[str, Any]]:
    """Find free time slots between busy periods."""
    free_slots = []
    current_time = start_time

    # Sort busy periods by start time
    busy_periods.sort(key=lambda x: _parse_datetime(x["start"]))

    for busy in busy_periods:
        busy_start = _parse_datetime(busy["start"])
        busy_end = _parse_datetime(busy["end"])

        # Skip if busy period is outside our search window
        if busy_end <= current_time or busy_start >= end_time:
            continue

        # Find gap before this busy period
        gap_start = max(current_time, start_time)
        gap_end = min(busy_start, end_time)

        if gap_end > gap_start:
            # Check if gap is during working hours and long enough
            gap_duration = (gap_end - gap_start).total_seconds() / 60
            if gap_duration >= duration_minutes:
                # Check if slot is within working hours
                if (
                    gap_start.hour >= working_hours_start
                    and gap_end.hour <= working_hours_end
                ):
                    free_slots.append(
                        {
                            "start": gap_start.isoformat(),
                            "end": gap_end.isoformat(),
                            "duration_minutes": gap_duration,
                        }
                    )

        current_time = max(current_time, busy_end)

    # Check for final gap after last busy period
    final_gap_start = max(current_time, start_time)
    final_gap_end = end_time

    if final_gap_end > final_gap_start:
        gap_duration = (final_gap_end - final_gap_start).total_seconds() / 60
        if gap_duration >= duration_minutes:
            if (
                final_gap_start.hour >= working_hours_start
                and final_gap_end.hour <= working_hours_end
            ):
                free_slots.append(
                    {
                        "start": final_gap_start.isoformat(),
                        "end": final_gap_end.isoformat(),
                        "duration_minutes": gap_duration,
                    }
                )

    return free_slots


def _analyze_busyness(events: List[Dict[str, Any]], days: int = 7) -> Dict[str, Any]:
    """Analyze daily event counts and durations."""
    analysis = {
        "total_events": len(events),
        "total_duration_hours": 0,
        "daily_breakdown": {},
        "average_events_per_day": 0,
        "average_hours_per_day": 0,
        "busiest_day": None,
        "busiest_day_count": 0,
        "period_days": days,
    }

    daily_events = {}
    daily_duration = {}

    for event in events:
        try:
            start_time = _parse_datetime(event["start"]["dateTime"])
            end_time = _parse_datetime(event["end"]["dateTime"])

            # Skip all-day events
            if "date" in event["start"]:
                continue

            day_key = start_time.date().isoformat()
            duration_hours = (end_time - start_time).total_seconds() / 3600

            if day_key not in daily_events:
                daily_events[day_key] = 0
                daily_duration[day_key] = 0

            daily_events[day_key] += 1
            daily_duration[day_key] += duration_hours
            analysis["total_duration_hours"] += duration_hours

        except (KeyError, ValueError, TypeError):
            continue

    # Build daily breakdown
    for day in daily_events:
        analysis["daily_breakdown"][day] = {
            "event_count": daily_events[day],
            "duration_hours": round(daily_duration[day], 2),
        }

    # Calculate averages
    if daily_events:
        analysis["average_events_per_day"] = round(len(events) / len(daily_events), 2)
        analysis["average_hours_per_day"] = round(
            analysis["total_duration_hours"] / len(daily_events), 2
        )

        # Find busiest day
        busiest_day = max(daily_events, key=daily_events.get)
        analysis["busiest_day"] = busiest_day
        analysis["busiest_day_count"] = daily_events[busiest_day]

    return analysis


def _find_mutual_free_time(
    calendars_freebusy: Dict[str, List[Dict[str, Any]]],
    duration_minutes: int,
    search_days: int = 7,
    working_hours_start: int = 9,
    working_hours_end: int = 17,
) -> List[Dict[str, Any]]:
    """Find mutual free time across multiple calendars."""
    if not calendars_freebusy:
        return []

    # Get search window
    now = datetime.now(timezone.utc)
    start_time = now.replace(
        hour=working_hours_start, minute=0, second=0, microsecond=0
    )
    end_time = start_time + timedelta(days=search_days)

    # Collect all busy periods across calendars
    all_busy_periods = []
    for calendar_id, busy_periods in calendars_freebusy.items():
        for busy in busy_periods:
            all_busy_periods.append(
                {"start": busy["start"], "end": busy["end"], "calendar_id": calendar_id}
            )

    # Find free slots considering all calendars' busy periods
    return _find_free_slots(
        all_busy_periods,
        duration_minutes,
        start_time,
        end_time,
        working_hours_start,
        working_hours_end,
    )


class CalendarAPI:
    """Calendar API wrapper for calendar operations."""

    def __init__(self, entity_id: str, user_id: str):
        """Initialize Calendar API wrapper."""
        self.entity_id = entity_id
        self.user_id = user_id
        self.auth = UnifiedCalendarAuth(entity_id, user_id)
        self.service = None

    async def _get_service(self):
        """Get Calendar API service instance."""
        if self.service is None:
            credentials = await self.auth.get_valid_credentials()
            if not credentials:
                raise PlexusExternalAuthRequiredError(
                    authorization_url="https://accounts.google.com/o/oauth2/auth",
                    provider_name="calendar",
                    detail_message="Calendar integration not authenticated",
                )

            self.service = build("calendar", "v3", credentials=credentials)
        return self.service

    async def get_events(
        self,
        max_results: int = 10,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get calendar events."""
        try:
            service = await self._get_service()

            # Set default time range if not provided
            if not time_min:
                time_min = datetime.now(timezone.utc).isoformat()
            if not time_max:
                time_max = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            return [self._parse_event(event) for event in events]
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError(
                    authorization_url="https://accounts.google.com/o/oauth2/auth",
                    provider_name="calendar",
                    detail_message="Calendar authentication expired",
                )
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error getting calendar events: {e}")
            raise

    async def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        attendees: Optional[List[str]] = None,
        location: str = "",
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        """Create a new calendar event."""
        try:
            service = await self._get_service()

            event = {
                "summary": summary,
                "description": description,
                "start": {
                    "dateTime": start_time,
                    "timeZone": "UTC",
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": "UTC",
                },
                "location": location,
            }

            if attendees:
                event["attendees"] = [{"email": email} for email in attendees]

            created_event = (
                service.events().insert(calendarId=calendar_id, body=event).execute()
            )

            return self._parse_event(created_event)
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            raise

    async def update_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        """Update an existing calendar event."""
        try:
            service = await self._get_service()

            # Get existing event
            event = (
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            )

            # Update fields if provided
            if summary:
                event["summary"] = summary
            if description:
                event["description"] = description
            if start_time:
                event["start"]["dateTime"] = start_time
            if end_time:
                event["end"]["dateTime"] = end_time
            if location:
                event["location"] = location

            updated_event = (
                service.events()
                .update(calendarId=calendar_id, eventId=event_id, body=event)
                .execute()
            )

            return self._parse_event(updated_event)
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error updating calendar event: {e}")
            raise

    async def delete_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        """Delete a calendar event."""
        try:
            service = await self._get_service()
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return True
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error deleting calendar event: {e}")
            raise

    async def get_event(
        self, event_id: str, calendar_id: str = "primary"
    ) -> Optional[Dict[str, Any]]:
        """Get a specific calendar event by ID."""
        try:
            service = await self._get_service()
            event = (
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            )
            return self._parse_event(event)
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            elif e.resp.status == 404:
                return None
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error getting calendar event: {e}")
            raise

    async def search_events(
        self, query: str, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search calendar events by query."""
        try:
            service = await self._get_service()

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    q=query,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            return [self._parse_event(event) for event in events]
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error searching calendar events: {e}")
            raise

    async def get_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming events for the next N days."""
        try:
            service = await self._get_service()

            now = datetime.now(timezone.utc)
            time_min = now.isoformat()
            time_max = (now + timedelta(days=days)).isoformat()

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            return [self._parse_event(event) for event in events]
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            raise

    # ============================================================================
    # ADVANCED CALENDAR OPERATIONS
    # ============================================================================

    async def list_calendars(self) -> List[Dict[str, Any]]:
        """List all calendars available to the user."""
        try:
            service = await self._get_service()
            calendar_list = service.calendarList().list().execute()
            calendars = calendar_list.get("items", [])
            return calendars
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error listing calendars: {e}")
            raise

    async def create_calendar(
        self, name: str, description: str = "", timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """Create a new calendar."""
        try:
            service = await self._get_service()

            calendar_body = {
                "summary": name,
                "description": description,
                "timeZone": timezone,
            }

            created_calendar = service.calendars().insert(body=calendar_body).execute()
            return created_calendar
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error creating calendar: {e}")
            raise

    async def get_events_advanced(
        self,
        calendar_id: str = "primary",
        max_results: int = 10,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        query: Optional[str] = None,
        show_deleted: bool = False,
        single_events: bool = True,
        order_by: str = "startTime",
    ) -> Dict[str, Any]:
        """Get calendar events with advanced filtering options."""
        try:
            service = await self._get_service()

            # Build request with advanced parameters
            request_params = {
                "calendarId": calendar_id,
                "maxResults": max_results,
                "singleEvents": single_events,
                "orderBy": order_by,
                "showDeleted": show_deleted,
            }

            # Add optional parameters
            if time_min:
                request_params["timeMin"] = time_min
            if time_max:
                request_params["timeMax"] = time_max
            if query:
                request_params["q"] = query

            events_result = service.events().list(**request_params).execute()
            events = events_result.get("items", [])

            return {
                "events": [self._parse_event(event) for event in events],
                "count": len(events),
                "next_page_token": events_result.get("nextPageToken"),
            }
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error getting calendar events advanced: {e}")
            raise

    async def quick_add_event(
        self, text: str, calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Quick-add an event from natural language text."""
        try:
            service = await self._get_service()

            # Use Google's quickAdd API which parses natural language
            quick_add_result = (
                service.events().quickAdd(calendarId=calendar_id, text=text).execute()
            )

            return self._parse_event(quick_add_result)
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error quick-adding event: {e}")
            raise

    async def query_freebusy(
        self, calendar_ids: List[str], time_min: str, time_max: str
    ) -> Dict[str, Any]:
        """Query free/busy information for multiple calendars."""
        try:
            service = await self._get_service()

            # Query free/busy for all specified calendars
            freebusy_request = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": cal_id} for cal_id in calendar_ids],
            }

            freebusy_result = service.freebusy().query(body=freebusy_request).execute()

            # Process and format the results
            calendars_freebusy = {}
            for cal_id in calendar_ids:
                cal_freebusy = freebusy_result.get("calendars", {}).get(cal_id, {})
                calendars_freebusy[cal_id] = {
                    "busy": cal_freebusy.get("busy", []),
                    "errors": cal_freebusy.get("errors", []),
                }

            return calendars_freebusy
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error querying free/busy: {e}")
            raise

    async def add_event_attendees(
        self, event_id: str, attendees: List[str], calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Add attendees to an existing calendar event."""
        try:
            service = await self._get_service()

            # Get the current event
            event = (
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            )

            # Add new attendees to existing ones
            current_attendees = event.get("attendees", [])
            attendee_dicts = [{"email": email} for email in attendees]
            updated_attendees = current_attendees + attendee_dicts

            # Update the event
            event["attendees"] = updated_attendees
            updated_event = (
                service.events()
                .update(calendarId=calendar_id, eventId=event_id, body=event)
                .execute()
            )

            return self._parse_event(updated_event)
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error adding attendees to event: {e}")
            raise

    async def get_attendee_status(
        self, event_id: str, calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Check the response status of attendees for a calendar event."""
        try:
            service = await self._get_service()

            # Get the event with attendee information
            event = (
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            )

            attendees = event.get("attendees", [])
            attendee_status = []

            for attendee in attendees:
                status_info = {
                    "email": attendee.get("email", ""),
                    "displayName": attendee.get("displayName", ""),
                    "responseStatus": attendee.get("responseStatus", "unknown"),
                    "optional": attendee.get("optional", False),
                }
                attendee_status.append(status_info)

            # Count responses
            status_counts = {}
            for attendee in attendee_status:
                status = attendee["responseStatus"]
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                "event_summary": event.get("summary", ""),
                "attendees": attendee_status,
                "attendee_count": len(attendee_status),
                "status_counts": status_counts,
            }
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error checking attendee status: {e}")
            raise

    async def analyze_busyness(
        self, days: int = 7, calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Analyze daily event counts and durations for busyness insights."""
        try:
            service = await self._get_service()

            # Get events for the analysis period
            now = datetime.now(timezone.utc)
            time_min = (now - timedelta(days=days)).isoformat()
            time_max = now.isoformat()

            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            # Analyze the events using helper function
            analysis = _analyze_busyness(events, days)

            return analysis
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error analyzing busyness: {e}")
            raise

    async def schedule_mutual(
        self,
        calendar_ids: List[str],
        duration_minutes: int,
        search_days: int = 7,
        summary: str = "Meeting",
        description: str = "",
        working_hours_start: int = 9,
        working_hours_end: int = 17,
    ) -> Dict[str, Any]:
        """Find mutual free slots and schedule meetings automatically."""
        try:
            service = await self._get_service()

            # Get search time window
            now = datetime.now(timezone.utc)
            start_time = now.replace(
                hour=working_hours_start, minute=0, second=0, microsecond=0
            )
            end_time = start_time + timedelta(days=search_days)

            # Query free/busy for all calendars
            freebusy_request = {
                "timeMin": start_time.isoformat(),
                "timeMax": end_time.isoformat(),
                "items": [{"id": cal_id} for cal_id in calendar_ids],
            }

            freebusy_result = service.freebusy().query(body=freebusy_request).execute()

            # Extract busy periods for each calendar
            calendars_freebusy = {}
            for cal_id in calendar_ids:
                cal_freebusy = freebusy_result.get("calendars", {}).get(cal_id, {})
                calendars_freebusy[cal_id] = cal_freebusy.get("busy", [])

            # Find mutual free time slots
            free_slots = _find_mutual_free_time(
                calendars_freebusy,
                duration_minutes,
                search_days,
                working_hours_start,
                working_hours_end,
            )

            # Take the first available slot and create the event
            if free_slots:
                best_slot = free_slots[0]

                # Create event in primary calendar
                event_body = {
                    "summary": summary,
                    "description": description,
                    "start": {
                        "dateTime": best_slot["start"],
                        "timeZone": "UTC",
                    },
                    "end": {
                        "dateTime": best_slot["end"],
                        "timeZone": "UTC",
                    },
                }

                created_event = (
                    service.events()
                    .insert(calendarId="primary", body=event_body)
                    .execute()
                )

                return {
                    "free_slots": free_slots[:5],  # Return top 5 suggestions
                    "scheduled_event": self._parse_event(created_event),
                    "status": "scheduled",
                    "message": f"Meeting '{summary}' scheduled at {best_slot['start']}",
                    "duration_minutes": duration_minutes,
                    "participants": len(calendar_ids),
                }
            else:
                return {
                    "free_slots": [],
                    "scheduled_event": None,
                    "status": "no_availability",
                    "message": f"No mutual free slots found in the next {search_days} days for {duration_minutes} minute meeting",
                    "duration_minutes": duration_minutes,
                    "participants": len(calendar_ids),
                }
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error scheduling mutual meeting: {e}")
            raise

    def _parse_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse calendar event into a structured format."""
        start = event.get("start", {})
        end = event.get("end", {})

        return {
            "id": event.get("id"),
            "summary": event.get("summary", ""),
            "description": event.get("description", ""),
            "location": event.get("location", ""),
            "start_time": start.get("dateTime") or start.get("date"),
            "end_time": end.get("dateTime") or end.get("date"),
            "timezone": start.get("timeZone", "UTC"),
            "attendees": [
                attendee.get("email") for attendee in event.get("attendees", [])
            ],
            "organizer": event.get("organizer", {}).get("email", ""),
            "status": event.get("status", ""),
            "created": event.get("created"),
            "updated": event.get("updated"),
            "html_link": event.get("htmlLink", ""),
        }
