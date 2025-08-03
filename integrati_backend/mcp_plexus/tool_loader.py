"""Tool loading utilities for MCP Plexus."""

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def load_tools_from_directory(directory_path: str) -> List[str]:
    """
    DEPRECATED: Use load_tools_from_integrations instead.

    Load tools from a directory containing tool modules.
    """
    logger.warning(
        "load_tools_from_directory is deprecated. Use load_tools_from_integrations instead."
    )
    return load_tools_from_integrations()


async def load_tools_from_integrations() -> List[str]:
    """
    Load tools from the integrations directory.

    Scans the integrations directory for tools.py files and imports them.
    Returns a list of loaded integration names.
    """
    # Get the path to the integrations directory (relative to mcp_plexus)
    mcp_plexus_dir = Path(__file__).parent
    integrations_dir = mcp_plexus_dir.parent / "integrations"

    if not integrations_dir.exists():
        logger.warning(f"Integrations directory not found: {integrations_dir}")
        return []

    loaded_integrations = []

    # Scan for integration directories
    for integration_dir in integrations_dir.iterdir():
        if not integration_dir.is_dir():
            continue

        integration_name = integration_dir.name
        tools_file = integration_dir / "tools.py"

        if tools_file.exists():
            try:
                # Import the tools module
                module_name = f"integrations.{integration_name}.tools"
                logger.info(f"Loading tools from {module_name}")

                # Import the module
                __import__(module_name)

                # Try to register tools if there's a registration function
                try:
                    registration_module = __import__(
                        f"integrations.{integration_name}.tools",
                        fromlist=["register_common_tools"],
                    )
                    if hasattr(registration_module, "register_common_tools"):
                        registration_module.register_common_tools()
                        logger.info(f"Registered tools for {integration_name}")
                except Exception as e:
                    logger.warning(
                        f"Could not register tools for {integration_name}: {e}"
                    )

                loaded_integrations.append(integration_name)
                logger.info(f"Successfully loaded integration: {integration_name}")

            except Exception as e:
                logger.error(f"Failed to load integration {integration_name}: {e}")
                continue

    logger.info(
        f"Loaded {len(loaded_integrations)} integrations: {loaded_integrations}"
    )
    return loaded_integrations


async def register_dynamic_tools_for_tenant(entity_id: str, user_id: str) -> List[str]:
    """
    Register tools for a specific tenant based on their connected integrations.
    """
    try:
        from .dynamic_tool_registry import get_dynamic_tool_registry

        tool_registry = await get_dynamic_tool_registry()
        available_tools = await tool_registry.register_tools_for_tenant(
            entity_id, user_id
        )
        logger.info(
            f"Registered {len(available_tools)} dynamic tools for tenant {entity_id}"
        )
        return available_tools
    except Exception as e:
        logger.error(f"Error registering dynamic tools for tenant {entity_id}: {e}")
        return []


async def load_tools_for_user(user_id: str, entity_id: str) -> List[str]:
    """
    Load tools specific to a user.

    This function can be extended to load user-specific tools based on
    their permissions and enabled integrations.
    """
    # For now, load all available tools
    # In the future, this could filter based on user permissions
    return await load_tools_from_integrations()
