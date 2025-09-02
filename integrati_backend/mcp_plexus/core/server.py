# mcp_plexus/core/server.py
from typing import (
    TYPE_CHECKING,
    TypeVar,
    Callable,
    Any,
    Dict,
    Set,
    Optional,
    Union,
    List,
    overload,
)
import logging

from fastmcp import FastMCP
from mcp.types import Tool as MCPTool
from fastmcp.tools import Tool, FunctionTool
from fastmcp.resources import Resource, ResourceTemplate
from fastmcp.prompts import Prompt

if TYPE_CHECKING:
    from ..oauth.models import OAuthProviderSettings
    from ..oauth.storage_interfaces import AbstractExternalOAuthProviderConfigStore

logger = logging.getLogger(__name__)

# Global cache for external OAuth config store to avoid repeated imports
_ext_oauth_config_store_cache: Optional["AbstractExternalOAuthProviderConfigStore"] = (
    None
)


def _get_external_oauth_config_store_instance() -> (
    Optional["AbstractExternalOAuthProviderConfigStore"]
):
    """
    Lazy-load and cache the external OAuth provider config store instance.
    Returns None if the store is not available or import fails.
    """
    global _ext_oauth_config_store_cache
    if _ext_oauth_config_store_cache is None:
        try:
            from mcp_plexus.main import external_oauth_provider_config_store_instance

            _ext_oauth_config_store_cache = (
                external_oauth_provider_config_store_instance
            )
            logger.debug(
                "MCPPlexusServer: Successfully imported external_oauth_provider_config_store_instance"
            )
        except (ImportError, AttributeError):
            logger.error(
                "MCPPlexusServer: Failed to import or find external_oauth_provider_config_store_instance.",
                exc_info=True,
            )
            return None
    return _ext_oauth_config_store_cache


F = TypeVar("F", bound=Callable[..., Any])


class MCPPlexusServer:
    """
    Main server class that wraps FastMCP functionality with additional features
    like tenant-based tool scoping and OAuth provider management.
    """

    def __init__(self, server_settings: Optional[Any] = None):
        """
        Initialize the MCPPlexusServer with a shared FastMCP instance.

        Args:
            server_settings: Optional server configuration settings
        """
        from ..mcp_handlers.tenant_mcp_app import shared_fastmcp_server_instance
        from ..permissions.service import PermissionService

        self._fastmcp_instance: FastMCP = shared_fastmcp_server_instance
        self.plexus_settings = server_settings

        # Track which tools are restricted to specific tenants
        self._tool_tenant_scoping: Dict[str, List[str]] = {}
        # Track which tools belong to which tool sets
        self._tool_set_assignments: Dict[str, List[str]] = {}
        # Track which integration tool modules have been loaded to avoid duplicate imports
        self._loaded_connectors: Set[str] = set()
        self._tool_set_assignments: Dict[str, List[str]] = {}

        # Define common tools that are always available
        try:
            from integrations.common.constants import COMMON_TOOL_NAMES

            self.common_tools = COMMON_TOOL_NAMES
        except ImportError:
            # Fallback if import fails
            self.common_tools = ["web_search", "local_search"]

        # Initialize permission service for config-based tool access control
        self.permission_service = PermissionService()

        logger.info(
            f"MCPPlexusServer initialized using shared FastMCP instance: {getattr(self._fastmcp_instance, 'name', 'None')}"
        )

    def get_fastmcp_instance(self, entity_id: Optional[str] = None) -> FastMCP:
        """
        Get the FastMCP instance, with fallback recovery if instance is None.

        Args:
            entity_id: Optional entity identifier (currently unused but kept for API compatibility)

        Returns:
            The FastMCP instance

        Raises:
            RuntimeError: If FastMCP instance cannot be obtained
        """
        if not self._fastmcp_instance:
            logger.error("CRITICAL: MCPPlexusServer._fastmcp_instance is None!")
            from ..mcp_handlers.tenant_mcp_app import shared_fastmcp_server_instance

            self._fastmcp_instance = shared_fastmcp_server_instance
            if not self._fastmcp_instance:
                raise RuntimeError(
                    "MCPPlexusServer._fastmcp_instance is None and could not be re-fetched."
                )
        return self._fastmcp_instance

    @overload
    def tool(self, func: F) -> F: ...

    @overload
    def tool(
        self,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        annotations: Optional[Dict[str, Any]] = None,
        tool_sets: Optional[List[str]] = None,
        allowed_tenant_ids: Optional[List[str]] = None,
        exclude_args: Optional[List[str]] = None,
    ) -> Callable[[F], F]: ...

    def tool(
        self,
        func: Optional[F] = None,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        annotations: Optional[Dict[str, Any]] = None,
        tool_sets: Optional[List[str]] = None,
        allowed_tenant_ids: Optional[List[str]] = None,
        exclude_args: Optional[List[str]] = None,
    ) -> Union[Callable[[F], F], F]:
        """
        Decorator to register a function as an MCP tool with tenant scoping and tool set support.

        Args:
            func: The function to register as a tool
            name: Optional custom name for the tool
            description: Optional description of the tool
            tags: Optional set of tags for the tool
            annotations: Optional annotations for the tool
            tool_sets: Optional list of tool sets this tool belongs to
            allowed_tenant_ids: Optional list of tenant IDs that can access this tool
            exclude_args: Optional list of function arguments to exclude from the tool schema

        Returns:
            The decorated function or decorator
        """

        def decorator(fn: F) -> FunctionTool:
            effective_name = name or getattr(fn, "__name__", "unknown_tool")
            logger.info(
                f"MCPPlexusServer.tool registering '{effective_name}'. ToolSets: {tool_sets}, Tenants: {allowed_tenant_ids}"
            )

            # Build final tags including tool set tags
            final_tags = set(tags) if tags else set()
            if tool_sets:
                for ts_name in tool_sets:
                    final_tags.add(f"tool_set:{ts_name.strip().replace(' ', '_')}")

            # Combine exclude_args from decorator parameter and function attribute
            final_exclude_args = list(exclude_args) if exclude_args else []
            decorator_excluded = getattr(fn, "_plexus_exclude_args", [])
            final_exclude_args.extend(decorator_excluded)

            # Set up tenant scoping for this tool
            if allowed_tenant_ids is not None:
                self._tool_tenant_scoping[effective_name] = [
                    tid.strip() for tid in allowed_tenant_ids if tid.strip()
                ]
            elif effective_name not in self._tool_tenant_scoping:
                self._tool_tenant_scoping[effective_name] = []

            # Track tool set assignments
            if tool_sets:
                self._tool_set_assignments[effective_name] = [
                    ts.strip() for ts in tool_sets if ts.strip()
                ]

            # Create and register the tool with FastMCP
            tool_obj = Tool.from_function(
                fn=fn,
                name=name,
                description=description,
                tags=final_tags,
                annotations=annotations,
                exclude_args=final_exclude_args if final_exclude_args else None,
            )
            self.get_fastmcp_instance().add_tool(tool_obj)
            logger.info(
                f"MCPPlexusServer.tool: Registered tool '{tool_obj.name}' with FastMCP. Excluded args: {final_exclude_args}"
            )
            return tool_obj

        if callable(func):
            return decorator(func)
        else:
            return decorator

    def resource(
        self,
        uri: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        mime_type: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> Callable[[F], Union[Resource, ResourceTemplate]]:
        """
        Decorator to register a function as an MCP resource.

        Args:
            uri: The URI pattern for the resource
            name: Optional custom name for the resource
            description: Optional description of the resource
            mime_type: Optional MIME type for the resource
            tags: Optional set of tags for the resource

        Returns:
            The decorator function
        """

        def decorator(fn: F) -> Union[Resource, ResourceTemplate]:
            logger.info(f"MCPPlexusServer.resource registering URI: {uri}")
            return self.get_fastmcp_instance().resource(
                uri=uri,
                name=name,
                description=description,
                mime_type=mime_type,
                tags=tags,
            )(fn)

        return decorator

    @overload
    def prompt(self, func: F) -> F: ...

    @overload
    def prompt(
        self,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> Callable[[F], F]: ...

    def prompt(
        self,
        func: Optional[F] = None,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> Union[Callable[[F], F], F]:
        """
        Decorator to register a function as an MCP prompt.

        Args:
            func: The function to register as a prompt
            name: Optional custom name for the prompt
            description: Optional description of the prompt
            tags: Optional set of tags for the prompt

        Returns:
            The decorated function or decorator
        """

        def decorator(fn: F) -> Prompt:
            prompt_obj = Prompt.from_function(
                fn=fn, name=name, description=description, tags=tags
            )
            self.get_fastmcp_instance().add_prompt(prompt_obj)
            logger.info(
                f"MCPPlexusServer.prompt: Registered prompt '{prompt_obj.name}' with FastMCP"
            )
            return prompt_obj

        if callable(func):
            return decorator(func)
        else:
            return decorator

    async def get_mcp_tools_list_for_tenant(
        self,
        entity_id: str,
        tool_set_filter: Optional[str] = None,
        mcp_session_id: Optional[str] = None,
    ) -> List[MCPTool]:
        """
        Get the list of MCP tools available to a specific tenant, with optional tool set filtering.

        Args:
            entity_id: The tenant/entity ID requesting tools
            tool_set_filter: Optional tool set name to filter by
            mcp_session_id: Optional MCP session ID (currently unused)

        Returns:
            List of MCP tools visible to the tenant
        """
        if not self._fastmcp_instance or not hasattr(
            self._fastmcp_instance, "get_tools"
        ):
            logger.error(
                "MCPPlexusServer.get_mcp_tools_list_for_tenant: Invalid FastMCP instance"
            )
            return []

        source_tools_dict = await self._fastmcp_instance.get_tools()
        logger.debug(
            f"get_mcp_tools_list_for_tenant (E:{entity_id}, SetFilter:{tool_set_filter}): Found {len(source_tools_dict)} raw tools from FastMCP"
        )

        # Use DynamicToolRegistry to get tools available for this tenant based on integrations
        from ..dynamic_tool_registry import get_dynamic_tool_registry
        from ..main import plexus_session_manager_instance

        dynamic_registry = await get_dynamic_tool_registry()

        # Get the user ID from multiple sources (session, auth context, etc.)
        user_id = None

        # First, try to get from session
        if mcp_session_id and plexus_session_manager_instance:
            try:
                session_data, _ = await plexus_session_manager_instance.get_session(
                    entity_id, mcp_session_id
                )
                user_id = session_data.persistent_user_id if session_data else None
                if user_id:
                    logger.debug(f"Got user_id from session: {user_id}")
            except Exception as e:
                logger.debug(f"Could not get user ID from session: {e}")

        # If session didn't work, try to get from auth context
        # The PlexusMCPEndpoint should have set derived_persistent_user_id in the scope
        if not user_id:
            try:
                # This is a bit of a hack - we're trying to access the request context
                # The derived_persistent_user_id should be available in the FastMCP context
                from fastmcp.server.dependencies import get_http_request

                # Try to get the current request context
                request = get_http_request()
                if request and hasattr(request, "state"):
                    user_id = getattr(request.state, "derived_persistent_user_id", None)
                    if user_id:
                        logger.debug(f"Got user_id from request context: {user_id}")
            except Exception as e:
                logger.debug(f"Could not get user ID from request context: {e}")

        # If we still don't have user_id, try a simpler approach
        # For most cases, the user is authenticated as "base"
        if not user_id:
            # Default to "base" user since that's what we see in logs
            user_id = "base"
            logger.debug(f"Using default user_id: {user_id}")

        # Register and get available tools for this tenant
        if user_id:
            try:
                available_tool_names = await dynamic_registry.register_tools_for_tenant(
                    entity_id, user_id
                )
                logger.debug(
                    f"Dynamic tool loading successful for user {user_id}: {len(available_tool_names)} tools"
                )

                # Dynamically register integration tools that are needed but not yet registered
                await self._register_missing_integration_tools(
                    available_tool_names, source_tools_dict.keys()
                )

                # Re-fetch the tools dict after dynamic registration
                source_tools_dict = await self._fastmcp_instance.get_tools()

            except Exception as e:
                logger.error(f"Error in dynamic tool loading for user {user_id}: {e}")
                # Fallback to common tools on error
                available_tool_names = dynamic_registry.common_tools.copy()
        else:
            # Fallback to common tools only if no user context
            available_tool_names = dynamic_registry.common_tools.copy()
            logger.warning(
                f"No user context for tenant {entity_id}, showing only common tools"
            )

        logger.debug(
            f"Dynamic tool loading for tenant {entity_id}: Available tools: {available_tool_names}"
        )

        visible_tools: List[MCPTool] = []
        for tool_name, fmcp_tool_obj in source_tools_dict.items():
            # Only include tools that are available for this tenant per DynamicToolRegistry
            if tool_name not in available_tool_names:
                continue

            # Check tenant access permissions (for additional scoping beyond integrations)
            is_globally_visible = not self._tool_tenant_scoping.get(tool_name, [])
            if (
                not is_globally_visible
                and entity_id not in self._tool_tenant_scoping.get(tool_name, [])
            ):
                continue

            # Apply tool set filter if specified
            if tool_set_filter:
                expected_tag = f"tool_set:{tool_set_filter.strip().replace(' ', '_')}"
                if expected_tag not in (fmcp_tool_obj.tags or set()):
                    continue

            mcp_tool = fmcp_tool_obj.to_mcp_tool(name=tool_name)
            visible_tools.append(mcp_tool)

        logger.info(
            f"get_mcp_tools_list_for_tenant (E:{entity_id}, SetFilter:{tool_set_filter}): Returning {len(visible_tools)} tools"
        )
        return visible_tools

    async def can_tenant_call_tool(self, entity_id: str, tool_name: str) -> bool:
        """
        Check if a tenant has permission to call a specific tool.

        Args:
            entity_id: The tenant/entity ID
            tool_name: The name of the tool to check

        Returns:
            True if the tenant can call the tool, False otherwise
        """
        # Check if tool exists
        if (
            not self._fastmcp_instance
            or not hasattr(self._fastmcp_instance, "_tool_manager")
            or not self._fastmcp_instance._tool_manager.has_tool(tool_name)
        ):
            logger.warning(
                f"can_tenant_call_tool: Tool '{tool_name}' not registered. Denying call for E:{entity_id}"
            )
            return False

        # Check tenant permissions
        allowed_tenants_for_tool = self._tool_tenant_scoping.get(tool_name)
        if allowed_tenants_for_tool is None or not allowed_tenants_for_tool:
            # Tool is globally accessible
            return True

        return entity_id in allowed_tenants_for_tool

    async def get_mcp_tools_list_for_config(
        self,
        entity_id: str,
        config_id: str = "base",
        tool_set_filter: Optional[str] = None,
        mcp_session_id: Optional[str] = None,
    ) -> List[MCPTool]:
        """Get tools filtered by config permissions."""

        # Get all available tools first
        all_tools = await self.get_mcp_tools_list_for_tenant(
            entity_id, tool_set_filter, mcp_session_id
        )

        # If base config, return all tools
        if config_id == "base":
            return all_tools

        # Filter tools based on config permissions
        filtered_tools = []
        for tool in all_tools:
            permission_check = await self.permission_service.check_tool_permission(
                entity_id, config_id, tool.name
            )

            # Only show tools with RESTRICTED_ACCESS or FULL_ACCESS
            if permission_check.permission_level != 1:  # Not NO_ACCESS
                filtered_tools.append(tool)

        logger.info(
            f"get_mcp_tools_list_for_config (E:{entity_id}, C:{config_id}): Filtered {len(all_tools)} -> {len(filtered_tools)} tools"
        )
        return filtered_tools

    async def can_tenant_call_tool_with_config(
        self,
        entity_id: str,
        config_id: str,
        tool_name: str,
        tool_params: Dict[str, Any] = None,
    ):
        """Check if config can call tool and handle permissions."""

        # First check basic tenant permissions
        if not await self.can_tenant_call_tool(entity_id, tool_name):
            from ..permissions.models import ToolPermissionResponse, ToolPermissionLevel

            return ToolPermissionResponse(
                allowed=False,
                permission_level=ToolPermissionLevel.NO_ACCESS,
                message="Tenant does not have access to this tool",
            )

        # Check config-specific permissions
        return await self.permission_service.check_tool_permission(
            entity_id, config_id, tool_name, tool_params
        )

    async def _get_tenant_oauth_status(self, entity_id: str) -> Dict[str, bool]:
        """
        Get OAuth integration status for a tenant.

        Args:
            entity_id: The tenant/entity ID

        Returns:
            Dictionary mapping integration names to their connection status
        """
        try:
            from mcp_plexus.oauth.unified_token_service import (
                get_unified_oauth_token_service,
            )

            unified_service = await get_unified_oauth_token_service()

            oauth_status = {}
            for integration_name in ["gmail", "calendar"]:
                # Check for tenant-level tokens (prefer tenant-level)
                token_data = await unified_service.get_oauth_tokens(
                    entity_id, None, integration_name
                )
                oauth_status[integration_name] = bool(
                    token_data and token_data.get("access_token")
                )
                logger.info(
                    f"OAuth status for {entity_id}/{integration_name}: {oauth_status[integration_name]}"
                )

            return oauth_status
        except Exception as e:
            logger.error(f"Error getting OAuth status for tenant {entity_id}: {e}")
            return {"gmail": False, "calendar": False}

    async def _can_tenant_use_tool(
        self, entity_id: str, tool_name: str, oauth_status: Dict[str, bool]
    ) -> bool:
        """
        Check if a tenant can use a specific tool based on OAuth integration status.

        Args:
            entity_id: The tenant/entity ID
            tool_name: The name of the tool to check
            oauth_status: Dictionary of OAuth integration statuses

        Returns:
            True if the tenant can use the tool, False otherwise
        """
        # Build OAuth requirements from constants - no hardcoding!
        tool_oauth_requirements = {}

        try:
            from integrations.gmail.constants import GMAIL_TOOL_NAMES
            from integrations.calendar.constants import CALENDAR_TOOL_NAMES

            # Map all Gmail tools to require gmail OAuth
            for tool_name_gmail in GMAIL_TOOL_NAMES:
                tool_oauth_requirements[tool_name_gmail] = "gmail"

            # Map all Calendar tools to require calendar OAuth
            for tool_name_calendar in CALENDAR_TOOL_NAMES:
                tool_oauth_requirements[tool_name_calendar] = "calendar"

            logger.debug(
                f"Built OAuth requirements for {len(tool_oauth_requirements)} tools from constants"
            )

        except ImportError:
            # Fallback if constants are not available
            logger.warning(
                "Could not import tool constants, using minimal OAuth requirements"
            )
            tool_oauth_requirements = {
                "send_gmail_message": "gmail",
                "get_calendar_events": "calendar",
            }

        # Check if this tool requires OAuth
        required_integration = tool_oauth_requirements.get(tool_name)
        if required_integration:
            # Tool requires OAuth integration
            return oauth_status.get(required_integration, False)
        else:
            # Tool doesn't require OAuth (e.g., common tools)
            return True

    async def register_external_oauth_provider(
        self, entity_id: str, provider_settings: "OAuthProviderSettings"
    ) -> None:
        """
        Register an external OAuth provider configuration for a tenant.

        Args:
            entity_id: The tenant/entity ID
            provider_settings: The OAuth provider configuration

        Raises:
            RuntimeError: If the OAuth config store is unavailable
        """
        store = _get_external_oauth_config_store_instance()
        if not store:
            raise RuntimeError("External OAuth Provider Config Store unavailable")

        await store.save_provider_config(
            entity_id=entity_id, provider_config=provider_settings
        )
        logger.info(
            f"Registered provider '{provider_settings.provider_name}' for E:'{entity_id}'"
        )

    async def get_external_oauth_provider(
        self, entity_id: str, provider_name: str
    ) -> Optional["OAuthProviderSettings"]:
        """
        Retrieve an external OAuth provider configuration for a tenant.

        Args:
            entity_id: The tenant/entity ID
            provider_name: The name of the OAuth provider

        Returns:
            The OAuth provider settings if found, None otherwise
        """
        store = _get_external_oauth_config_store_instance()
        if not store:
            return None

        return await store.load_provider_config(
            entity_id=entity_id, provider_name=provider_name
        )

    async def delete_external_oauth_provider(
        self, entity_id: str, provider_name: str
    ) -> None:
        """
        Delete an external OAuth provider configuration for a tenant.

        Args:
            entity_id: The tenant/entity ID
            provider_name: The name of the OAuth provider to delete

        Raises:
            RuntimeError: If the OAuth config store is unavailable
        """
        store = _get_external_oauth_config_store_instance()
        if not store:
            raise RuntimeError("External OAuth Provider Config Store unavailable")

        await store.delete_provider_config(
            entity_id=entity_id, provider_name=provider_name
        )
        logger.info(f"Deleted provider '{provider_name}' for E:'{entity_id}'")

    async def get_all_external_oauth_providers_for_entity(
        self, entity_id: str
    ) -> List["OAuthProviderSettings"]:
        """
        Get all external OAuth provider configurations for a tenant.

        Args:
            entity_id: The tenant/entity ID

        Returns:
            List of OAuth provider settings for the tenant
        """
        store = _get_external_oauth_config_store_instance()
        if not store:
            return []

        return await store.load_all_provider_configs_for_entity(entity_id=entity_id)

    async def _register_missing_integration_tools(
        self, available_tool_names: List[str], currently_registered_tools: List[str]
    ) -> None:
        """
        Dynamically register integration tools that are needed but not yet registered with FastMCP.

        Args:
            available_tool_names: List of tool names that should be available
            currently_registered_tools: List of tool names currently registered with FastMCP
        """
        # Find which tools are missing from FastMCP registration
        missing_tools = []
        for tool_name in available_tool_names:
            if (
                tool_name not in currently_registered_tools
                and tool_name not in self.common_tools
            ):
                missing_tools.append(tool_name)

        if not missing_tools:
            return

        logger.info(
            f"Need to dynamically register {len(missing_tools)} integration tools: {missing_tools}"
        )

        # Import integration tool constants
        try:
            from integrations.gmail.constants import GMAIL_TOOL_NAMES
            from integrations.calendar.constants import CALENDAR_TOOL_NAMES

            # Group missing tools by integration using constants
            integration_tools_map = {
                "gmail": GMAIL_TOOL_NAMES,
                "calendar": CALENDAR_TOOL_NAMES,
            }
        except ImportError:
            # Fallback with minimal tools if constants import fails
            logger.error("Failed to import tool constants - using minimal fallback")
            integration_tools_map = {
                "gmail": ["send_gmail_message", "get_gmail_message"],
                "calendar": ["get_calendar_events", "create_calendar_event"],
            }

        # Register missing tools by importing their modules
        for integration_name, tool_names in integration_tools_map.items():
            tools_to_register = [t for t in tool_names if t in missing_tools]
            if tools_to_register:
                try:
                    # Import the integration tools module
                    module_name = f"integrations.{integration_name}.tools"
                    logger.info(
                        f"Importing {module_name} to register tools: {tools_to_register}"
                    )

                    # Import the module - the @PLEXUS_SERVER_INSTANCE.tool() decorators should register the tools automatically
                    __import__(module_name)

                    logger.info(
                        f"Successfully imported {integration_name} tools - decorators should register automatically"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to register tools for {integration_name}: {e}"
                    )

    def add_resource(self, resource_obj: Resource, key: Optional[str] = None) -> None:
        """
        Add a resource object directly to the FastMCP instance.

        Args:
            resource_obj: The resource object to add
            key: Optional key for the resource

        Raises:
            RuntimeError: If FastMCP instance is not available
        """
        logger.info(
            f"MCPPlexusServer.add_resource: URI: {resource_obj.uri}, Key: {key}"
        )
        if not self._fastmcp_instance:
            raise RuntimeError("FastMCP instance not available for add_resource")

        self._fastmcp_instance.add_resource(resource_obj, key=key)
