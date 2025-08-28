"""
Pydantic models for the Integrati chatbot API.
Updated to match the new simplified requirements.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChatMessage(BaseModel):
    """Individual chat message model."""

    message_id: Optional[str] = None
    chat_id: str
    user_query: str
    response: str
    reasoning: str
    tools_used: List[str]
    timestamp: datetime
    message_type: str = "user"  # user, system, agent


class ChatSession(BaseModel):
    """Chat session model."""

    chat_id: str
    user_id: str
    tenant_id: str
    created_at: datetime
    last_activity: datetime
    message_count: int
    integrations: List[str]
    status: str = "active"


class NewChatRequest(BaseModel):
    """Request to create a new chat session."""

    user_id: str = Field(..., description="User identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    initial_message: Optional[str] = Field(None, description="Optional initial message")
    integrations: List[str] = Field(default=[], description="Available integrations")


class ContinueChatRequest(BaseModel):
    """Request to continue an existing chat."""

    message: str = Field(..., description="User message to continue chat")
    integrations: List[str] = Field(default=[], description="Available integrations")
    token: str = Field(..., description="Authentication token")


class ChatbotMessageRequest(BaseModel):
    """Request to send a message to the chatbot."""

    chat_id: str = Field(..., description="Chat session identifier")
    message: str = Field(..., description="User message")
    integrations: List[str] = Field(default=[], description="Available integrations")
    token: str = Field(..., description="Authentication token")


class ChatbotResponse(BaseModel):
    """Response from the chatbot."""

    success: bool
    response: Optional[str] = None
    agent_used: Optional[str] = None
    tools_used: Optional[List[str]] = None
    reasoning: Optional[str] = None
    trajectory: Optional[str] = None
    chat_id: str
    tenant_id: str
    session_active: Optional[bool] = None
    error: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    """Response containing chat history."""

    success: bool
    history: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class UserChatsResponse(BaseModel):
    """Response containing user's chat sessions."""

    success: bool
    chats: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class StorageStatsResponse(BaseModel):
    """Response containing storage statistics."""

    success: bool
    stats: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ChatbotStatus(BaseModel):
    """Status model for the chatbot system."""

    status: str = Field(..., description="Overall system status")
    agents: Dict[str, Any] = Field(..., description="Status of individual agents")
    available_integrations: List[str] = Field(
        default=[], description="Available integrations"
    )
    system_info: Dict[str, Any] = Field(default={}, description="System information")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the status was checked"
    )


class MCPToolInfo(BaseModel):
    """Model for MCP tool information."""

    name: str = Field(..., description="Name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    input_schema: Dict[str, Any] = Field(
        default={}, description="Input schema for the tool"
    )
    tool_set: str = Field(..., description="Which tool set this tool belongs to")
    is_available: bool = Field(
        ..., description="Whether the tool is available to the user"
    )


class UserContext(BaseModel):
    """Model for user context information."""

    tenant_id: str = Field(..., description="The tenant identifier")
    user_id: str = Field(..., description="The user identifier")
    integrations: List[str] = Field(
        default=[], description="User's available integrations"
    )
    permissions: Dict[str, bool] = Field(default={}, description="User's permissions")
    mcp_tools: List[MCPToolInfo] = Field(default=[], description="Available MCP tools")
    conversation_history: Optional[List[Dict[str, Any]]] = None
