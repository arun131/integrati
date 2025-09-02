"""Common tools for MCP server including search operations."""

import logging
from typing import Dict, Any, Optional
from fastmcp import Context as FastMCPBaseContext
from fastmcp.exceptions import ToolError
from mcp_plexus.plexus_context import PlexusContext

from .api import GoogleSearchAPI
from ..utils import PermissionHelper

logger = logging.getLogger(__name__)

# Tool names for smart categorization
COMMON_TOOL_NAMES = [
    "web_search",
    "local_search",
]


def get_plexus_instance():
    """Get the PLEXUS_SERVER_INSTANCE lazily to avoid import issues."""
    from mcp_plexus.core.global_registry import PLEXUS_SERVER_INSTANCE

    return PLEXUS_SERVER_INSTANCE


class CommonTools:
    """Common search tools available to all users."""

    @staticmethod
    async def web_search(
        ctx: FastMCPBaseContext,
        query: str,
        num_results: int = 10,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform web search using Google Custom Search API.

        Args:
            query: The search query string
            num_results: Number of results to return (default: 10, max: 10)
            location: Optional location to refine search results

        Examples:
           web_search("restaurants", location="San Francisco, CA")
           web_search("machine learning conferences 2024", num_results=8, location="United States")
        """
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id
            user_id = getattr(plexus_ctx, "user_id", None)

            if not user_id:
                raise ToolError("User ID not available in context")

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="web_search",
                tool_params={
                    "query": query,
                    "num_results": num_results,
                    "location": location,
                },
                no_access_response={
                    "results": [],
                    "total_results": 0,
                    "status": "access_denied",
                    "status_message": "You don't have permission to use web search tools with this configuration.",
                },
                restricted_access_response={
                    "results": [],
                    "total_results": 0,
                    "status": "approval_required",
                    "status_message": f"Your request to search the web for '{query}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                },
                approval_message=f"Your request to search the web for '{query}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="common",
            )

            if permission_result is not None:
                return permission_result

            # Execute search
            search_api = GoogleSearchAPI()
            search_query = query + (" in " + location if location else "")
            results = await search_api.web_search(search_query, num_results, location)

            logger.info(
                f"Web search completed: {len(results)} results for query '{query}'"
            )
            return {
                "results": results,
                "total_results": len(results),
                "status": "success",
                "status_message": "success",
            }
        except Exception as e:
            logger.error(f"Error performing web search: {e}")
            raise ToolError(f"Error performing web search: {str(e)}")

    @staticmethod
    async def local_search(
        ctx: FastMCPBaseContext,
        query: str,
        location: Optional[str] = None,
        num_results: int = 5,
    ) -> Dict[str, Any]:
        """Search for local businesses and services using Google Places API.

        Args:
            query: Search query (e.g., "home services near me", "restaurants")
            location: Optional location override (e.g., "New York, NY")
            num_results: Number of results to return (default: 5)

        Examples:
           local_search("home services near me", location="New York, NY")
           local_search("restaurants", num_results=3)
        """
        try:
            plexus_ctx = PlexusContext(ctx.fastmcp)
            entity_id = plexus_ctx.entity_id
            user_id = getattr(plexus_ctx, "user_id", None)

            if not user_id:
                raise ToolError("User ID not available in context")

            # Check permissions using helper
            permission_result = await PermissionHelper.check_and_handle_permissions(
                entity_id=entity_id,
                user_id=user_id,
                tool_name="local_search",
                tool_params={
                    "query": query,
                    "location": location,
                    "num_results": num_results,
                },
                no_access_response={
                    "results": [],
                    "total_results": 0,
                    "status": "access_denied",
                    "status_message": "You don't have permission to use local search tools with this configuration.",
                },
                restricted_access_response={
                    "results": [],
                    "total_results": 0,
                    "status": "approval_required",
                    "status_message": f"Your request to search for local '{query}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                },
                approval_message=f"Your request to search for local '{query}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="common",
            )

            if permission_result is not None:
                return permission_result

            # Execute search
            search_api = GoogleSearchAPI()
            search_query = query + (" in " + location if location else "")
            results = await search_api.local_search(search_query, location, num_results)

            logger.info(
                f"Local search completed: {len(results)} results for query '{query}'"
            )
            return {
                "results": results,
                "total_results": len(results),
                "status": "success",
                "status_message": "success",
            }
        except Exception as e:
            logger.error(f"Error performing local search: {e}")
            raise ToolError(f"Error performing local search: {str(e)}")


# Register tools with the MCP server
def register_common_tools():
    """Register common tools with the MCP server."""
    plexus_instance = get_plexus_instance()
    if plexus_instance is None:
        logger.warning(
            "PLEXUS_SERVER_INSTANCE not available, skipping tool registration"
        )
        return

    # Register all tools
    tools = [
        CommonTools.web_search,
        CommonTools.local_search,
    ]

    for tool in tools:
        plexus_instance.tool()(tool)
        logger.info(f"Registered tool: {tool.__name__}")
