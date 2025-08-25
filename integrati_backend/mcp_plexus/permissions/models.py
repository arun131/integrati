"""Permission models for MCP Plexus tool access control."""

from enum import IntEnum
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime


class ToolPermissionLevel(IntEnum):
    """Tool permission levels for config-based access control."""

    NO_ACCESS = 1  # Tool completely hidden and blocked
    RESTRICTED_ACCESS = 2  # Tool visible but requires user approval
    FULL_ACCESS = 3  # Tool has full access without restrictions


class ToolApprovalRequest(BaseModel):
    """Model for tool approval requests in restricted access scenarios."""

    approval_id: str
    entity_id: str
    requesting_config_id: str
    approving_config_id: str = "base"
    tool_name: str
    tool_params: Dict[str, Any]
    tool_context: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, approved, denied, executed
    created_at: datetime
    responded_at: Optional[datetime] = None
    response_reason: Optional[str] = None
    executed_at: Optional[datetime] = None
    execution_result: Optional[str] = None


class ToolPermissionResponse(BaseModel):
    """Response from permission check indicating access level and actions."""

    allowed: bool
    permission_level: ToolPermissionLevel
    approval_id: Optional[str] = None
    message: str
    requires_user_approval: bool = False
