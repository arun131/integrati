"""Common math tools for MCP server."""

import logging
from typing import List, Dict, Any
from fastmcp import Context as FastMCPBaseContext
from fastmcp.exceptions import ToolError
from mcp_plexus.plexus_context import PlexusContext

from ..utils import PermissionHelper

logger = logging.getLogger(__name__)

# Tool names for smart categorization
COMMON_TOOL_NAMES = [
    "add_numbers",
    "subtract_numbers",
    "multiply_numbers",
    "divide_numbers",
    "calculate_power",
    "calculate_square_root",
    "calculate_percentage",
    "sum_list",
    "calculate_average",
]


def get_plexus_instance():
    """Get the PLEXUS_SERVER_INSTANCE lazily to avoid import issues."""
    from mcp_plexus.core.global_registry import PLEXUS_SERVER_INSTANCE

    return PLEXUS_SERVER_INSTANCE


class CommonTools:
    """Common math tools available to all users."""

    @staticmethod
    async def add_numbers(
        ctx: FastMCPBaseContext, a: float, b: float
    ) -> Dict[str, Any]:
        """Add two numbers."""
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
                tool_name="add_numbers",
                tool_params={"a": a, "b": b},
                no_access_response={
                    "result": 0,
                    "operation": f"{a} + {b}",
                    "status_message": "You don't have permission to use math tools with this configuration.",
                },
                restricted_access_response={
                    "result": 0,
                    "operation": f"{a} + {b}",
                },
                approval_message=f"Your request to add {a} + {b} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="common",
            )

            if permission_result is not None:
                return permission_result

            result = a + b
            logger.info(f"Added {a} + {b} = {result}")
            return {
                "result": result,
                "operation": f"{a} + {b}",
                "status_message": "success",
            }
        except Exception as e:
            logger.error(f"Error adding numbers: {e}")
            raise ToolError(f"Error adding numbers: {str(e)}")

    @staticmethod
    async def subtract_numbers(
        ctx: FastMCPBaseContext, a: float, b: float
    ) -> Dict[str, Any]:
        """Subtract b from a."""
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
                tool_name="subtract_numbers",
                tool_params={"a": a, "b": b},
                no_access_response={
                    "result": 0,
                    "operation": f"{a} - {b}",
                    "status_message": "You don't have permission to use math tools with this configuration.",
                },
                restricted_access_response={
                    "result": 0,
                    "operation": f"{a} - {b}",
                },
                approval_message=f"Your request to subtract {a} - {b} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="common",
            )

            if permission_result is not None:
                return permission_result

            result = a - b
            logger.info(f"Subtracted {a} - {b} = {result}")
            return {
                "result": result,
                "operation": f"{a} - {b}",
                "status_message": "success",
            }
        except Exception as e:
            logger.error(f"Error subtracting numbers: {e}")
            raise ToolError(f"Error subtracting numbers: {str(e)}")

    @staticmethod
    async def multiply_numbers(
        ctx: FastMCPBaseContext, a: float, b: float
    ) -> Dict[str, Any]:
        """Multiply two numbers."""
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
                tool_name="multiply_numbers",
                tool_params={"a": a, "b": b},
                no_access_response={
                    "result": 0,
                    "operation": f"{a} * {b}",
                    "status_message": "You don't have permission to use math tools with this configuration.",
                },
                restricted_access_response={
                    "result": 0,
                    "operation": f"{a} * {b}",
                },
                approval_message=f"Your request to multiply {a} * {b} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="common",
            )

            if permission_result is not None:
                return permission_result

            result = a * b
            logger.info(f"Multiplied {a} * {b} = {result}")
            return {
                "result": result,
                "operation": f"{a} * {b}",
                "status_message": "success",
            }
        except Exception as e:
            logger.error(f"Error multiplying numbers: {e}")
            raise ToolError(f"Error multiplying numbers: {str(e)}")

    @staticmethod
    async def divide_numbers(
        ctx: FastMCPBaseContext, a: float, b: float
    ) -> Dict[str, Any]:
        """Divide a by b."""
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
                tool_name="divide_numbers",
                tool_params={"a": a, "b": b},
                no_access_response={
                    "result": 0,
                    "operation": f"{a} / {b}",
                    "status_message": "You don't have permission to use math tools with this configuration.",
                },
                restricted_access_response={
                    "result": 0,
                    "operation": f"{a} / {b}",
                },
                approval_message=f"Your request to divide {a} / {b} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="common",
            )

            if permission_result is not None:
                return permission_result

            if b == 0:
                raise ToolError("Cannot divide by zero")
            result = a / b
            logger.info(f"Divided {a} / {b} = {result}")
            return {
                "result": result,
                "operation": f"{a} / {b}",
                "status_message": "success",
            }
        except Exception as e:
            logger.error(f"Error dividing numbers: {e}")
            raise ToolError(f"Error dividing numbers: {str(e)}")

    @staticmethod
    async def calculate_power(
        ctx: FastMCPBaseContext, base: float, exponent: float
    ) -> Dict[str, Any]:
        """Calculate base raised to the power of exponent."""
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
                tool_name="calculate_power",
                tool_params={"base": base, "exponent": exponent},
                no_access_response={
                    "result": 0,
                    "operation": f"{base} ^ {exponent}",
                    "status_message": "You don't have permission to use math tools with this configuration.",
                },
                restricted_access_response={
                    "result": 0,
                    "operation": f"{base} ^ {exponent}",
                },
                approval_message=f"Your request to calculate {base} ^ {exponent} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="common",
            )

            if permission_result is not None:
                return permission_result

            result = base**exponent
            logger.info(f"Calculated {base} ^ {exponent} = {result}")
            return {
                "result": result,
                "operation": f"{base} ^ {exponent}",
                "status_message": "success",
            }
        except Exception as e:
            logger.error(f"Error calculating power: {e}")
            raise ToolError(f"Error calculating power: {str(e)}")

    @staticmethod
    async def calculate_square_root(
        ctx: FastMCPBaseContext, number: float
    ) -> Dict[str, Any]:
        """Calculate square root of a number."""
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
                tool_name="calculate_square_root",
                tool_params={"number": number},
                no_access_response={
                    "result": 0,
                    "operation": f"sqrt({number})",
                    "status_message": "You don't have permission to use math tools with this configuration.",
                },
                restricted_access_response={
                    "result": 0,
                    "operation": f"sqrt({number})",
                },
                approval_message=f"Your request to calculate sqrt({number}) was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="common",
            )

            if permission_result is not None:
                return permission_result

            if number < 0:
                raise ToolError("Cannot calculate square root of negative number")
            result = number**0.5
            logger.info(f"Calculated sqrt({number}) = {result}")
            return {
                "result": result,
                "operation": f"sqrt({number})",
                "status_message": "success",
            }
        except Exception as e:
            logger.error(f"Error calculating square root: {e}")
            raise ToolError(f"Error calculating square root: {str(e)}")

    @staticmethod
    async def calculate_percentage(
        ctx: FastMCPBaseContext, value: float, total: float
    ) -> Dict[str, Any]:
        """Calculate percentage of value relative to total."""
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
                tool_name="calculate_percentage",
                tool_params={"value": value, "total": total},
                no_access_response={
                    "result": 0,
                    "operation": f"{value} as % of {total}",
                    "status_message": "You don't have permission to use math tools with this configuration.",
                },
                restricted_access_response={
                    "result": 0,
                    "operation": f"{value} as % of {total}",
                },
                approval_message=f"Your request to calculate {value} as percentage of {total} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="common",
            )

            if permission_result is not None:
                return permission_result

            if total == 0:
                raise ToolError("Total cannot be zero")
            result = (value / total) * 100
            logger.info(f"Calculated {value} as {result}% of {total}")
            return {
                "result": result,
                "operation": f"{value} as {result}% of {total}",
                "status_message": "success",
            }
        except Exception as e:
            logger.error(f"Error calculating percentage: {e}")
            raise ToolError(f"Error calculating percentage: {str(e)}")

    @staticmethod
    async def sum_list(ctx: FastMCPBaseContext, numbers: List[float]) -> Dict[str, Any]:
        """Sum a list of numbers."""
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
                tool_name="sum_list",
                tool_params={"numbers": numbers},
                no_access_response={
                    "result": 0,
                    "operation": f"sum({numbers})",
                    "status_message": "You don't have permission to use math tools with this configuration.",
                },
                restricted_access_response={
                    "result": 0,
                    "operation": f"sum({numbers})",
                },
                approval_message=f"Your request to sum the list {numbers} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="common",
            )

            if permission_result is not None:
                return permission_result

            result = sum(numbers)
            logger.info(f"Summed {numbers} = {result}")
            return {
                "result": result,
                "operation": f"sum({numbers})",
                "status_message": "success",
            }
        except Exception as e:
            logger.error(f"Error summing list: {e}")
            raise ToolError(f"Error summing list: {str(e)}")

    @staticmethod
    async def calculate_average(
        ctx: FastMCPBaseContext, numbers: List[float]
    ) -> Dict[str, Any]:
        """Calculate average of a list of numbers."""
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
                tool_name="calculate_average",
                tool_params={"numbers": numbers},
                no_access_response={
                    "result": 0,
                    "operation": f"avg({numbers})",
                    "status_message": "You don't have permission to use math tools with this configuration.",
                },
                restricted_access_response={
                    "result": 0,
                    "operation": f"avg({numbers})",
                },
                approval_message=f"Your request to calculate average of {numbers} was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
                integration_type="common",
            )

            if permission_result is not None:
                return permission_result

            if not numbers:
                raise ToolError("Cannot calculate average of empty list")
            result = sum(numbers) / len(numbers)
            logger.info(f"Calculated average of {numbers} = {result}")
            return {
                "result": result,
                "operation": f"avg({numbers})",
                "status_message": "success",
            }
        except Exception as e:
            logger.error(f"Error calculating average: {e}")
            raise ToolError(f"Error calculating average: {str(e)}")


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
        CommonTools.add_numbers,
        CommonTools.subtract_numbers,
        CommonTools.multiply_numbers,
        CommonTools.divide_numbers,
        CommonTools.calculate_power,
        CommonTools.calculate_square_root,
        CommonTools.calculate_percentage,
        CommonTools.sum_list,
        CommonTools.calculate_average,
    ]

    for tool in tools:
        plexus_instance.tool()(tool)
        logger.info(f"Registered tool: {tool.__name__}")
