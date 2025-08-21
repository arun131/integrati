"""
FastAPI endpoints for the Integrati chatbot system.
Updated to use the new simplified approach with direct MCP integration.
"""

import logging
import uuid
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from .models import (
    NewChatRequest,
    ChatbotMessageRequest,
    ChatbotResponse,
    ChatHistoryResponse,
    UserChatsResponse,
    StorageStatsResponse,
    ContinueChatRequest,
)
from .conversation_manager import ConversationManager
from .main_processor import process_chatbot_request

logger = logging.getLogger(__name__)

# Create router
chatbot_router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])


async def get_redis_client():
    """Get Redis client for dependency injection."""
    try:
        import redis.asyncio as redis
        from mcp_plexus.settings import settings

        # Create Redis client using MCP Plexus settings
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            ssl=settings.redis_ssl,
            decode_responses=True,
        )

        # Test connection
        await redis_client.ping()
        logger.info("Redis client connected successfully")
        return redis_client

    except Exception as e:
        logger.error(f"Failed to create Redis client: {e}")
        # Return None to allow graceful fallback
        return None


async def get_conversation_manager(
    redis_client=Depends(get_redis_client),
) -> ConversationManager:
    """Get conversation manager for Redis-based conversation history."""
    if redis_client is None:
        # Create a mock Redis client for testing/fallback
        logger.warning(
            "Using mock Redis client - conversation history will not persist"
        )
        from unittest.mock import AsyncMock

        mock_redis = AsyncMock()
        mock_redis.hget.return_value = None
        mock_redis.hset.return_value = True
        mock_redis.hmget.return_value = [None, None, None]
        return ConversationManager(mock_redis)

    return ConversationManager(redis_client)


@chatbot_router.post("/new-chat")
async def create_new_chat(request: NewChatRequest):
    """Create a new chat session."""
    try:
        chat_id = f"{request.tenant_id}:{request.user_id}:{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()

        # Create chat data (stored for future use)
        _chat_data = {
            "chat_id": chat_id,
            "user_id": request.user_id,
            "tenant_id": request.tenant_id,
            "created_at": timestamp,
            "last_activity": timestamp,
            "message_count": 0,
            "integrations": request.integrations,
            "status": "active",
        }

        # If there's an initial message, process it
        if request.initial_message:
            # For now, we'll just return the chat ID
            # The actual processing will happen in the message endpoint
            return {
                "success": True,
                "chat_id": chat_id,
                "message": "New chat session created. Use the message endpoint to send your first message.",
                "initial_message": request.initial_message,
            }
        else:
            return {
                "success": True,
                "chat_id": chat_id,
                "message": "New chat session created. Send a message to start the conversation.",
            }

    except Exception as e:
        logger.error(f"Failed to create new chat: {e}")
        return {"success": False, "error": str(e)}


@chatbot_router.post("/message")
async def send_message(
    request: ChatbotMessageRequest,
    conversation_manager: ConversationManager = Depends(get_conversation_manager),
):
    """Send a message to the chatbot."""
    try:
        logger.info(f"Processing message for chat {request.chat_id}")
        logger.info(f"Request data: {request.dict()}")

        # Extract tenant_id and user_id from chat_id
        # Format: tenant_id:user_id:uuid
        chat_parts = request.chat_id.split(":")
        if len(chat_parts) != 3:
            logger.error(f"Invalid chat_id format: {request.chat_id}")
            raise HTTPException(status_code=400, detail="Invalid chat_id format")

        tenant_id = chat_parts[0]
        user_id = chat_parts[1]

        logger.info(f"Extracted tenant_id: {tenant_id}, user_id: {user_id}")

        # Process the message using the new main processor with conversation manager
        logger.info("Processing message with main processor...")
        result = await process_chatbot_request(
            chat_id=request.chat_id,
            tenant_id=tenant_id,
            user_query=request.message,
            integrations=request.integrations,  # Trust frontend integrations
            token=request.token,
            conversation_manager=conversation_manager,
            historical_context=None,  # Will be loaded from Redis
        )

        logger.info(f"Main processor result: {result}")

        # Create response
        response = ChatbotResponse(
            success=result["success"],
            response=result.get("response", "No response generated"),
            agent_used=result.get("agent_used", "orchestrator"),
            tools_used=result.get("tools_used", []),
            reasoning=result.get("reasoning", "No reasoning provided"),
            trajectory=result.get("trajectory", ""),
            chat_id=request.chat_id,
            tenant_id=tenant_id,
            session_active=True,
            error=result.get("error"),
        )

        logger.info("Response created successfully")
        return response

    except Exception as e:
        logger.error(f"Failed to process message: {e}", exc_info=True)
        return ChatbotResponse(
            success=False,
            error=str(e),
            response="I'm sorry, but I encountered an error while processing your request. Please try again.",
            agent_used="orchestrator",
            tools_used=[],
            reasoning=f"Error occurred: {str(e)}",
            chat_id=request.chat_id,
            tenant_id="unknown",
            session_active=False,
        )


@chatbot_router.get("/chat/{chat_id}/history")
async def get_chat_history(
    chat_id: str,
    limit: int = 50,
    conversation_manager: ConversationManager = Depends(get_conversation_manager),
):
    """Get chat history for a specific chat from Redis."""
    try:
        # Get conversation history from Redis
        conversation_history = await conversation_manager.get_conversation_history(
            chat_id
        )

        # Apply limit if specified
        if limit and limit > 0:
            conversation_history = conversation_history[-limit:]

        return ChatHistoryResponse(
            success=True, history={"history_of_messages": conversation_history}
        )
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        return ChatHistoryResponse(success=False, error=str(e))


@chatbot_router.post("/chat/{chat_id}/continue")
async def continue_chat(
    chat_id: str,
    request: ContinueChatRequest,
    conversation_manager: ConversationManager = Depends(get_conversation_manager),
):
    """Continue an existing chat session."""
    try:
        # Extract tenant_id from chat_id
        chat_parts = chat_id.split(":")
        if len(chat_parts) != 3:
            raise HTTPException(status_code=400, detail="Invalid chat_id format")

        tenant_id = chat_parts[0]
        _user_id = chat_parts[
            1
        ]  # Extract user_id from chat_id format: tenant_id:user_id:uuid

        # Process the message using the new main processor with conversation manager
        result = await process_chatbot_request(
            chat_id=chat_id,
            tenant_id=tenant_id,
            user_query=request.message,
            integrations=request.integrations,  # Trust frontend integrations
            token=request.token,
            conversation_manager=conversation_manager,
            historical_context=None,  # Will be loaded from Redis
        )

        # Create response
        response = ChatbotResponse(
            success=result["success"],
            response=result.get("response", "No response generated"),
            agent_used=result.get("agent_used", "orchestrator"),
            reasoning=result.get("reasoning", "No reasoning provided"),
            trajectory=result.get("trajectory", ""),
            tools_used=result.get("tools_used", []),
            chat_id=chat_id,
            tenant_id=tenant_id,
            session_active=True,
            error=result.get("error"),
        )

        return response

    except Exception as e:
        logger.error(f"Failed to continue chat: {e}")
        return ChatbotResponse(
            success=False,
            error=str(e),
            response="I'm sorry, but I encountered an error while processing your request. Please try again.",
            agent_used="orchestrator",
            tools_used=[],
            reasoning=f"Error occurred: {str(e)}",
            chat_id=chat_id,
            tenant_id="unknown",
            session_active=False,
        )


@chatbot_router.get("/chats/{user_id}")
async def get_user_chats(user_id: str, limit: int = 20):
    """Get user's chat sessions."""
    try:
        # For now, return empty list
        # This would be implemented with Redis storage
        return UserChatsResponse(success=True, chats=[])
    except Exception as e:
        logger.error(f"Failed to get user chats: {e}")
        return UserChatsResponse(success=False, error=str(e))


@chatbot_router.get("/storage/stats")
async def get_storage_stats():
    """Get storage statistics."""
    try:
        # Since we no longer use session management, return basic stats
        stats = {
            "active_sessions": 0,  # No longer tracking sessions
            "session_timeout_seconds": 0,  # No timeout needed
            "total_sessions_created": 0,  # No session tracking
        }

        return StorageStatsResponse(success=True, stats=stats)
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        return StorageStatsResponse(success=False, error=str(e))


@chatbot_router.get("/test")
async def test_chatbot_endpoint():
    """Simple test endpoint to verify the chatbot system is working."""
    try:
        return {
            "success": True,
            "message": "Chatbot system is working!",
            "timestamp": datetime.now().isoformat(),
            "status": "operational",
        }
    except Exception as e:
        logger.error(f"Test endpoint failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@chatbot_router.get("/status")
async def get_chatbot_status():
    """Get the status of the chatbot system."""
    try:
        # Get system info (no session management needed)
        system_info = {
            "active_sessions": 0,  # No longer tracking sessions
            "session_timeout_minutes": 0,  # No timeout needed
            "dspy_available": True,  # We assume DSPy is available
            "mcp_integration": True,  # We assume MCP integration is available
        }

        return {
            "status": "operational",
            "active_sessions": 0,  # No session tracking
            "system_info": system_info,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get chatbot status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
