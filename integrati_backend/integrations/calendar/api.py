"""Calendar API wrapper for calendar operations."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .unified_auth import UnifiedCalendarAuth
from mcp_plexus.oauth.errors import PlexusExternalAuthRequiredError

logger = logging.getLogger(__name__)


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
                service.events().insert(calendarId="primary", body=event).execute()
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
    ) -> Dict[str, Any]:
        """Update an existing calendar event."""
        try:
            service = await self._get_service()

            # Get existing event
            event = (
                service.events().get(calendarId="primary", eventId=event_id).execute()
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
                .update(calendarId="primary", eventId=event_id, body=event)
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

    async def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        try:
            service = await self._get_service()
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            return True
        except HttpError as e:
            if e.resp.status == 401:
                raise PlexusExternalAuthRequiredError("Calendar authentication expired")
            raise Exception(f"Calendar API error: {e}")
        except Exception as e:
            logger.error(f"Error deleting calendar event: {e}")
            raise

    async def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific calendar event by ID."""
        try:
            service = await self._get_service()
            event = (
                service.events().get(calendarId="primary", eventId=event_id).execute()
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
