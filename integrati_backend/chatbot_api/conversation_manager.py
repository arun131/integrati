"""
Redis-based conversation history management for the Integrati chatbot system.
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation history storage and retrieval in Redis."""

    def __init__(self, redis_client: redis.Redis):
        """Initialize conversation manager with Redis client."""
        self.redis_client = redis_client

    async def get_conversation_history(self, chat_id: str) -> List[Dict]:
        """Retrieve conversation history for a given chat ID."""
        try:
            history_data = await self.redis_client.hget(
                f"conversation:{chat_id}", "history"
            )
            if history_data:
                return json.loads(history_data)
            return []
        except Exception as e:
            logger.error(f"Failed to get conversation history for {chat_id}: {e}")
            return []

    async def save_conversation_history(
        self, chat_id: str, history: List[Dict]
    ) -> bool:
        """Save complete conversation history for a chat ID."""
        try:
            await self.redis_client.hset(
                f"conversation:{chat_id}", "history", json.dumps(history)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save conversation history for {chat_id}: {e}")
            return False

    async def add_message_to_history(self, chat_id: str, message: Dict) -> bool:
        """Add a new message to conversation history."""
        try:
            history = await self.get_conversation_history(chat_id)

            new_message = {
                "trajectory": message.get("trajectory", ""),
                "reasoning": message.get("reasoning", ""),
                "tools_used": message.get("tools_used", []),
                "response": message.get("response", ""),
                "response_timestamp": message.get(
                    "response_timestamp", datetime.now().isoformat()
                ),
                "user_query": message.get("user_query", ""),
            }

            history.append(new_message)
            return await self.save_conversation_history(chat_id, history)
        except Exception as e:
            logger.error(f"Failed to add message to history for {chat_id}: {e}")
            return False

    async def update_conversation_metadata(
        self, chat_id: str, tenant_id: str, integrations: List[str]
    ) -> bool:
        """Update conversation metadata like tenant ID and integrations."""
        try:
            await self.redis_client.hset(
                f"conversation:{chat_id}",
                mapping={
                    "last_seen": datetime.now().isoformat(),
                    "tenant_id": tenant_id,
                    "integrations": json.dumps(integrations),
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update conversation metadata for {chat_id}: {e}")
            return False

    async def get_conversation_metadata(self, chat_id: str) -> Optional[Dict]:
        """Get conversation metadata including tenant ID and integrations."""
        try:
            metadata = await self.redis_client.hmget(
                f"conversation:{chat_id}", "tenant_id", "integrations", "last_seen"
            )
            if metadata[0]:  # tenant_id exists
                return {
                    "tenant_id": metadata[0],
                    "integrations": json.loads(metadata[1]) if metadata[1] else [],
                    "last_seen": metadata[2],
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get conversation metadata for {chat_id}: {e}")
            return None
