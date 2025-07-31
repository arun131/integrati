"""Common math tools for MCP server."""

import logging
from typing import List

logger = logging.getLogger(__name__)


def get_plexus_instance():
    """Get the PLEXUS_SERVER_INSTANCE lazily to avoid import issues."""
    from mcp_plexus.core.global_registry import PLEXUS_SERVER_INSTANCE

    return PLEXUS_SERVER_INSTANCE


class CommonTools:
    """Common math tools available to all users."""

    @staticmethod
    async def add_numbers(a: float, b: float) -> float:
        """Add two numbers."""
        try:
            result = a + b
            logger.info(f"Added {a} + {b} = {result}")
            return result
        except Exception as e:
            logger.error(f"Error adding numbers: {e}")
            raise

    @staticmethod
    async def subtract_numbers(a: float, b: float) -> float:
        """Subtract b from a."""
        try:
            result = a - b
            logger.info(f"Subtracted {a} - {b} = {result}")
            return result
        except Exception as e:
            logger.error(f"Error subtracting numbers: {e}")
            raise

    @staticmethod
    async def multiply_numbers(a: float, b: float) -> float:
        """Multiply two numbers."""
        try:
            result = a * b
            logger.info(f"Multiplied {a} * {b} = {result}")
            return result
        except Exception as e:
            logger.error(f"Error multiplying numbers: {e}")
            raise

    @staticmethod
    async def divide_numbers(a: float, b: float) -> float:
        """Divide a by b."""
        try:
            if b == 0:
                raise ValueError("Cannot divide by zero")
            result = a / b
            logger.info(f"Divided {a} / {b} = {result}")
            return result
        except Exception as e:
            logger.error(f"Error dividing numbers: {e}")
            raise

    @staticmethod
    async def calculate_power(base: float, exponent: float) -> float:
        """Calculate base raised to the power of exponent."""
        try:
            result = base**exponent
            logger.info(f"Calculated {base} ^ {exponent} = {result}")
            return result
        except Exception as e:
            logger.error(f"Error calculating power: {e}")
            raise

    @staticmethod
    async def calculate_square_root(number: float) -> float:
        """Calculate square root of a number."""
        try:
            if number < 0:
                raise ValueError("Cannot calculate square root of negative number")
            result = number**0.5
            logger.info(f"Calculated sqrt({number}) = {result}")
            return result
        except Exception as e:
            logger.error(f"Error calculating square root: {e}")
            raise

    @staticmethod
    async def calculate_percentage(value: float, total: float) -> float:
        """Calculate percentage of value relative to total."""
        try:
            if total == 0:
                raise ValueError("Total cannot be zero")
            result = (value / total) * 100
            logger.info(f"Calculated {value} as {result}% of {total}")
            return result
        except Exception as e:
            logger.error(f"Error calculating percentage: {e}")
            raise

    @staticmethod
    async def sum_list(numbers: List[float]) -> float:
        """Sum a list of numbers."""
        try:
            result = sum(numbers)
            logger.info(f"Summed {numbers} = {result}")
            return result
        except Exception as e:
            logger.error(f"Error summing list: {e}")
            raise

    @staticmethod
    async def calculate_average(numbers: List[float]) -> float:
        """Calculate average of a list of numbers."""
        try:
            if not numbers:
                raise ValueError("Cannot calculate average of empty list")
            result = sum(numbers) / len(numbers)
            logger.info(f"Calculated average of {numbers} = {result}")
            return result
        except Exception as e:
            logger.error(f"Error calculating average: {e}")
            raise


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
