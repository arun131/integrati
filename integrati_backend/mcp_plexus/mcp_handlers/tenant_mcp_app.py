# mcp_plexus/mcp_handlers/tenant_mcp_app.py
from fastmcp import FastMCP
from fastmcp.resources import TextResource
import logging

from ..settings import settings
from ..plexus_context import PlexusContext
from ..core.server import MCPPlexusServer
import mcp_plexus.core.global_registry

# Configure logger for tenant MCP application
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if settings.debug_mode else logging.INFO)

# Global FastMCP instance for tenant-based MCP operations
shared_fastmcp_server_instance: FastMCP = None


def _plexus_context_factory(server_instance: FastMCP) -> PlexusContext:
    """Create a PlexusContext instance for MCP operations."""
    return PlexusContext(server_instance)


def _get_example_resource_content_str() -> str:
    """Get example resource content for testing."""
    return """
    # Example Resource

    This is an example resource that demonstrates how to use MCP resources.

    ## Features
    - Markdown support
    - Code highlighting
    - Lists and formatting

    ## Usage
    This resource can be accessed via MCP and provides example content.
    """


def _create_fastmcp_instance() -> FastMCP:
    """Create and configure the FastMCP instance."""
    # Create the FastMCP instance
    fastmcp_instance = FastMCP(
        name="Plexus Tenant MCP Server",
        version="0.2.1",
    )

    # Add example resource
    example_resource = TextResource(
        uri="file:///example.md",
        name="Example Resource",
        description="An example resource for testing",
        text=_get_example_resource_content_str(),
    )
    fastmcp_instance.add_resource(example_resource)

    logger.info("FastMCP instance created successfully")
    return fastmcp_instance


# Initialize the shared FastMCP instance
if shared_fastmcp_server_instance is None:
    shared_fastmcp_server_instance = _create_fastmcp_instance()
    logger.info("Shared FastMCP instance initialized")

# Initialize the global Plexus server facade if not already created
if mcp_plexus.core.global_registry.PLEXUS_SERVER_INSTANCE is None:
    _plexus_server_facade = MCPPlexusServer(server_settings=None)
    mcp_plexus.core.global_registry.PLEXUS_SERVER_INSTANCE = _plexus_server_facade
    logger.info("Global PLEXUS_SERVER_INSTANCE populated.")
else:
    logger.warning("Global PLEXUS_SERVER_INSTANCE was already populated.")

# Load all available tools from the integrations directory
logger.info("Loading tools from integrations directory")
try:
    # Import and register common tools
    from integrations.common.tools import register_common_tools

    register_common_tools()
    logger.info("Successfully registered common tools")
except Exception as e:
    logger.error(f"Failed to register common tools: {e}")

# Log registered tools for verification
if shared_fastmcp_server_instance and hasattr(
    shared_fastmcp_server_instance, "_tool_manager"
):
    tool_manager = shared_fastmcp_server_instance._tool_manager
    if tool_manager and hasattr(tool_manager, "get_tools"):
        try:
            # Handle both sync and async tool managers
            if hasattr(tool_manager.get_tools, "__await__"):
                # Async tool manager - we'll skip logging for now
                logger.info("Tool manager is async - tools loaded successfully")
            else:
                # Sync tool manager
                tool_names = list(tool_manager.get_tools().keys())
                logger.info(f"Tools registered on shared instance: {tool_names}")
        except Exception as e:
            logger.warning(f"Could not get tool names: {e}")
    else:
        logger.info("FastMCP 2.0 tool manager structure - tools loaded successfully")
