"""Analytics endpoints for frontend."""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from mcp_plexus.plexus_auth.dependencies import get_current_plexus_user
from analytics.logger import analytics_logger

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyticsSummaryResponse(BaseModel):
    """Response model for analytics summary."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    average_execution_time: float
    most_used_tools: list
    client_usage: dict
    time_period: dict


class UserAnalyticsResponse(BaseModel):
    """Response model for user analytics."""

    user_id: str
    entity_id: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_execution_time: float
    favorite_tools: list
    last_activity: Optional[str]
    integrations_used: list


@router.get("/analytics/summary")
async def get_analytics_summary(
    days: int = Query(
        default=30, ge=1, le=365, description="Number of days to analyze"
    ),
    current_user: Dict[str, Any] = Depends(get_current_plexus_user),
):
    """Get analytics summary for the current tenant."""
    try:
        entity_id = current_user["entity_id"]

        summary = await analytics_logger.get_analytics_summary(entity_id, days)

        return {
            "total_requests": summary.total_requests,
            "successful_requests": summary.successful_requests,
            "failed_requests": summary.failed_requests,
            "average_execution_time": summary.average_execution_time,
            "most_used_tools": summary.most_used_tools,
            "client_usage": summary.client_usage,
            "time_period": summary.time_period,
            "entity_id": entity_id,
            "days_analyzed": days,
        }
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/user")
async def get_user_analytics(
    days: int = Query(
        default=30, ge=1, le=365, description="Number of days to analyze"
    ),
    current_user: Dict[str, Any] = Depends(get_current_plexus_user),
):
    """Get analytics for the current user."""
    try:
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        user_analytics = await analytics_logger.get_user_analytics(
            entity_id, user_id, days
        )

        return {
            "user_id": user_analytics.user_id,
            "entity_id": user_analytics.entity_id,
            "total_requests": user_analytics.total_requests,
            "successful_requests": user_analytics.successful_requests,
            "failed_requests": user_analytics.failed_requests,
            "average_execution_time": user_analytics.average_execution_time,
            "favorite_tools": user_analytics.favorite_tools,
            "last_activity": user_analytics.last_activity.isoformat()
            if user_analytics.last_activity
            else None,
            "integrations_used": user_analytics.integrations_used,
            "days_analyzed": days,
        }
    except Exception as e:
        logger.error(f"Error getting user analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/tools")
async def get_tool_analytics(
    days: int = Query(
        default=30, ge=1, le=365, description="Number of days to analyze"
    ),
    current_user: Dict[str, Any] = Depends(get_current_plexus_user),
):
    """Get analytics for individual tools."""
    try:
        entity_id = current_user["entity_id"]

        # Get analytics summary which includes tool usage
        summary = await analytics_logger.get_analytics_summary(entity_id, days)

        return {
            "most_used_tools": summary.most_used_tools,
            "total_tools_used": len(summary.most_used_tools),
            "entity_id": entity_id,
            "days_analyzed": days,
        }
    except Exception as e:
        logger.error(f"Error getting tool analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/clients")
async def get_client_analytics(
    days: int = Query(
        default=30, ge=1, le=365, description="Number of days to analyze"
    ),
    current_user: Dict[str, Any] = Depends(get_current_plexus_user),
):
    """Get analytics for different client types."""
    try:
        entity_id = current_user["entity_id"]

        # Get analytics summary which includes client usage
        summary = await analytics_logger.get_analytics_summary(entity_id, days)

        return {
            "client_usage": summary.client_usage,
            "total_clients": len(summary.client_usage),
            "entity_id": entity_id,
            "days_analyzed": days,
        }
    except Exception as e:
        logger.error(f"Error getting client analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/integrations")
async def get_integration_analytics(
    days: int = Query(
        default=30, ge=1, le=365, description="Number of days to analyze"
    ),
    current_user: Dict[str, Any] = Depends(get_current_plexus_user),
):
    """Get analytics for integrations."""
    try:
        entity_id = current_user["entity_id"]
        user_id = current_user["persistent_user_id"]

        # Get user analytics which includes integrations used
        user_analytics = await analytics_logger.get_user_analytics(
            entity_id, user_id, days
        )

        return {
            "integrations_used": user_analytics.integrations_used,
            "total_integrations": len(user_analytics.integrations_used),
            "entity_id": entity_id,
            "user_id": user_id,
            "days_analyzed": days,
        }
    except Exception as e:
        logger.error(f"Error getting integration analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
