"""Dynamic tool registry for MCP Plexus."""

import logging
from typing import Dict, Any, List, Optional, Callable
from mcp_plexus.core.global_registry import PLEXUS_SERVER_INSTANCE
from mcp_plexus.oauth.unified_token_service import get_unified_oauth_token_service

logger = logging.getLogger(__name__)


class DynamicToolRegistry:
    """Registry for dynamically registering tools based on tenant integration status."""
    
    def __init__(self):
        """Initialize the dynamic tool registry."""
        self.registered_tools = {}
        self.integration_tools = {
            "gmail": [
                "search_gmail_messages",
                "get_last_received_email", 
                "send_gmail_message",
                "get_gmail_message",
                "get_unread_email_count",
                "search_gmail_by_sender",
                "search_gmail_by_subject"
            ],
            "calendar": [
                "get_calendar_events",
                "create_calendar_event",
                "update_calendar_event", 
                "delete_calendar_event",
                "get_calendar_event",
                "search_calendar_events",
                "get_upcoming_events"
            ]
        }
        self.common_tools = [
            "add_numbers",
            "subtract_numbers", 
            "multiply_numbers",
            "divide_numbers",
            "calculate_power",
            "calculate_square_root",
            "calculate_percentage",
            "sum_list",
            "calculate_average"
        ]
    
    async def get_tenant_integrations(self, entity_id: str, user_id: str) -> List[str]:
        """Get list of connected integrations for a tenant."""
        try:
            unified_service = await get_unified_oauth_token_service()
            connected_integrations = []
            
            for integration_name in ["gmail", "calendar"]:
                token_data = await unified_service.get_oauth_tokens(
                    entity_id, user_id, integration_name, prefer_tenant_level=True
                )
                if token_data:
                    connected_integrations.append(integration_name)
            
            logger.info(f"Tenant {entity_id} has connected integrations: {connected_integrations}")
            return connected_integrations
        except Exception as e:
            logger.error(f"Error getting tenant integrations: {e}")
            return []
    
    def get_available_tools(self, entity_id: str, user_id: str, connected_integrations: List[str]) -> List[str]:
        """Get list of available tools for a tenant based on their connected integrations."""
        available_tools = self.common_tools.copy()
        
        for integration in connected_integrations:
            if integration in self.integration_tools:
                available_tools.extend(self.integration_tools[integration])
        
        logger.info(f"Available tools for tenant {entity_id}: {available_tools}")
        return available_tools
    
    async def register_tools_for_tenant(self, entity_id: str, user_id: str) -> List[str]:
        """Register tools for a specific tenant based on their integrations."""
        try:
            # Get connected integrations
            connected_integrations = await self.get_tenant_integrations(entity_id, user_id)
            
            # Get available tools
            available_tools = self.get_available_tools(entity_id, user_id, connected_integrations)
            
            # Store the mapping for this tenant
            tenant_key = f"{entity_id}:{user_id}"
            self.registered_tools[tenant_key] = {
                "integrations": connected_integrations,
                "tools": available_tools
            }
            
            logger.info(f"Registered {len(available_tools)} tools for tenant {entity_id}")
            return available_tools
            
        except Exception as e:
            logger.error(f"Error registering tools for tenant {entity_id}: {e}")
            return self.common_tools
    
    def get_tenant_tools(self, entity_id: str, user_id: str) -> List[str]:
        """Get registered tools for a tenant."""
        tenant_key = f"{entity_id}:{user_id}"
        if tenant_key in self.registered_tools:
            return self.registered_tools[tenant_key]["tools"]
        return self.common_tools
    
    def is_tool_available(self, entity_id: str, user_id: str, tool_name: str) -> bool:
        """Check if a specific tool is available for a tenant."""
        tenant_tools = self.get_tenant_tools(entity_id, user_id)
        return tool_name in tenant_tools


# Global instance
dynamic_tool_registry = DynamicToolRegistry()


async def get_dynamic_tool_registry() -> DynamicToolRegistry:
    """Get the global dynamic tool registry instance."""
    return dynamic_tool_registry


def register_tool_with_tenant_check(tool_name: str):
    """Decorator to register a tool with tenant availability check."""
    def decorator(func: Callable) -> Callable:
        # Register the tool with the MCP server
        if PLEXUS_SERVER_INSTANCE:
            PLEXUS_SERVER_INSTANCE.tool()(func)
            logger.info(f"Registered tool: {tool_name}")
        
        return func
    return decorator 