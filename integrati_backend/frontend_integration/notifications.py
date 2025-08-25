"""Notifications endpoints for frontend."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel

from mcp_plexus.plexus_auth.dependencies import get_current_plexus_user_from_token
from analytics.database import AnalyticsDatabase

logger = logging.getLogger(__name__)

router = APIRouter()


class NotificationResponse(BaseModel):
    """Response model for a single notification."""

    notification_id: str
    notification_text: str
    integration_type: str
    agent_used: str
    priority: str
    timestamp: str
    is_read: bool
    event_details: Optional[Dict[str, Any]]
    tools_used: Optional[List[str]]
    reasoning: Optional[str]


class NotificationsListResponse(BaseModel):
    """Response model for notifications list."""

    notifications: List[NotificationResponse]
    total_count: int
    unread_count: int
    entity_id: str
    user_id: str


@router.get("/notifications")
async def get_notifications(
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of notifications to retrieve"
    ),
    include_read: bool = Query(default=False, description="Include read notifications"),
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
):
    """Get notifications for the current user."""
    try:
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        db = AnalyticsDatabase()

        # Get notifications
        notifications = await db.get_user_notifications(
            entity_id, user_id, limit, include_read
        )

        # Get unread count
        unread_count = await db.get_unread_notification_count(entity_id, user_id)

        # Convert to response format
        notification_responses = []
        for notification in notifications:
            notification_responses.append(
                NotificationResponse(
                    notification_id=notification.notification_id,
                    notification_text=notification.notification_text,
                    integration_type=notification.integration_type,
                    agent_used=notification.agent_used,
                    priority=notification.priority,
                    timestamp=notification.timestamp.isoformat(),
                    is_read=notification.is_read,
                    event_details=notification.event_details,
                    tools_used=notification.tools_used,
                    reasoning=notification.reasoning,
                )
            )

        return NotificationsListResponse(
            notifications=notification_responses,
            total_count=len(notification_responses),
            unread_count=unread_count,
            entity_id=entity_id,
            user_id=user_id,
        )
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/notifications/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: str = Path(..., description="Notification ID to mark as read"),
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
):
    """Mark a specific notification as read."""
    try:
        db = AnalyticsDatabase()

        success = await db.mark_notification_as_read(notification_id)

        if not success:
            raise HTTPException(
                status_code=404, detail="Notification not found or already read"
            )

        return {"success": True, "message": "Notification marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
):
    """Mark all notifications as read for the current user."""
    try:
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        db = AnalyticsDatabase()

        success = await db.mark_all_notifications_as_read(entity_id, user_id)

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to mark notifications as read"
            )

        return {"success": True, "message": "All notifications marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/notifications/count")
async def get_notification_count(
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
):
    """Get unread notification count for the current user."""
    try:
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        db = AnalyticsDatabase()

        unread_count = await db.get_unread_notification_count(entity_id, user_id)

        return {
            "unread_count": unread_count,
            "entity_id": entity_id,
            "user_id": user_id,
        }
    except Exception as e:
        logger.error(f"Error getting notification count: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
