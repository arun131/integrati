"""Analytics data models for tracking system activities."""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class MCPRequestLog(BaseModel):
    """Model for logging MCP tool requests."""

    entity_id: str = Field(description="Tenant entity ID")
    user_id: str = Field(description="User ID within the tenant")
    client_name: str = Field(description="Client name (claude, cursor, openai, etc.)")
    tool_name: str = Field(description="Name of the MCP tool called")
    parameters: Dict[str, Any] = Field(description="Tool parameters")
    response: Dict[str, Any] = Field(description="Tool response")
    execution_time: float = Field(description="Execution time in seconds")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Request timestamp"
    )
    success: bool = Field(description="Whether the request was successful")
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )
    session_id: Optional[str] = Field(default=None, description="MCP session ID")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AuthEventLog(BaseModel):
    """Model for logging authentication events."""

    entity_id: str = Field(description="Tenant entity ID")
    user_id: str = Field(description="User ID within the tenant")
    event_type: str = Field(
        description="Type of auth event (firebase_login, oauth_start, oauth_complete)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional event metadata"
    )
    success: bool = Field(
        default=True, description="Whether the auth event was successful"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class IntegrationEventLog(BaseModel):
    """Model for logging integration events."""

    entity_id: str = Field(description="Tenant entity ID")
    user_id: str = Field(description="User ID within the tenant")
    integration_name: str = Field(
        description="Name of the integration (gmail, calendar, etc.)"
    )
    event_type: str = Field(
        description="Type of integration event (add, remove, auth_start, auth_complete)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional event metadata"
    )
    success: bool = Field(
        default=True, description="Whether the integration event was successful"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AnalyticsSummary(BaseModel):
    """Model for analytics summary data."""

    total_requests: int = Field(description="Total number of MCP requests")
    successful_requests: int = Field(description="Number of successful requests")
    failed_requests: int = Field(description="Number of failed requests")
    average_execution_time: float = Field(
        description="Average execution time in seconds"
    )
    most_used_tools: List[Dict[str, Any]] = Field(
        description="Most frequently used tools"
    )
    client_usage: Dict[str, int] = Field(description="Usage by client type")
    time_period: Dict[str, datetime] = Field(description="Time period for the summary")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserAnalytics(BaseModel):
    """Model for user-specific analytics."""

    user_id: str = Field(description="User ID")
    entity_id: str = Field(description="Tenant entity ID")
    total_requests: int = Field(description="Total requests by this user")
    successful_requests: int = Field(description="Successful requests by this user")
    failed_requests: int = Field(description="Failed requests by this user")
    average_execution_time: float = Field(
        description="Average execution time for this user"
    )
    favorite_tools: List[str] = Field(description="Most used tools by this user")
    last_activity: Optional[datetime] = Field(description="Last activity timestamp")
    integrations_used: List[str] = Field(description="Integrations used by this user")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
