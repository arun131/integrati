"""OAuth provider for handling OAuth flows."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlencode

from .storage import get_user_external_token_store
from integrations.gmail.auth import GmailAuth
from integrations.calendar.auth import CalendarAuth

logger = logging.getLogger(__name__)


class OAuthProvider:
    """Generic OAuth provider for handling OAuth flows."""
    
    def __init__(self, integration_name: str):
        """Initialize OAuth provider for a specific integration."""
        self.integration_name = integration_name
        
        # Map integration names to their auth classes
        self.auth_classes = {
            "gmail": GmailAuth,
            "calendar": CalendarAuth
        }
        
        if integration_name not in self.auth_classes:
            raise ValueError(f"Unsupported integration: {integration_name}")
    
    async def get_authorization_url(self, state: str) -> str:
        """Get OAuth authorization URL."""
        # Use the specific auth class for this integration
        auth_class = self.auth_classes[self.integration_name]
        
        # Create a temporary auth instance to get the URL
        # We'll use placeholder entity_id and user_id for now
        temp_auth = auth_class("temp_entity", "temp_user")
        return await temp_auth.get_authorization_url(state)
    
    async def handle_callback(self, code: str, state: str, entity_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Handle OAuth callback and exchange code for tokens."""
        try:
            # Parse state to extract information
            state_parts = state.split(":")
            if len(state_parts) != 3:
                raise ValueError("Invalid state parameter")
            
            expected_entity_id, expected_user_id, integration_name = state_parts
            
            if expected_entity_id != entity_id or expected_user_id != user_id or integration_name != self.integration_name:
                raise ValueError("State parameter mismatch")
            
            # Use the appropriate auth class
            auth_class = self.auth_classes[self.integration_name]
            auth = auth_class(entity_id, user_id)
            
            # Exchange code for tokens
            tokens = await auth.exchange_code_for_tokens(code)
            
            if tokens:
                logger.info(f"Successfully obtained tokens for {self.integration_name} integration")
                return tokens
            else:
                logger.error(f"Failed to obtain tokens for {self.integration_name} integration")
                return None
                
        except Exception as e:
            logger.error(f"Error handling OAuth callback for {self.integration_name}: {e}")
            return None