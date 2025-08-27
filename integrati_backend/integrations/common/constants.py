"""Common tools integration constants and configuration."""

import logging

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

# Default permission levels for background agent config
# 1 = NO_ACCESS, 2 = RESTRICTED_ACCESS, 3 = FULL_ACCESS
COMMON_DEFAULT_BACKGROUND_PERMISSIONS = {
    "add_numbers": 3,  # Full access - safe math operations
    "subtract_numbers": 3,  # Full access - safe math operations
    "multiply_numbers": 3,  # Full access - safe math operations
    "divide_numbers": 3,  # Full access - safe math operations
    "calculate_power": 3,  # Full access - safe math operations
    "calculate_square_root": 3,  # Full access - safe math operations
    "calculate_percentage": 3,  # Full access - safe math operations
    "sum_list": 3,  # Full access - safe math operations
    "calculate_average": 3,  # Full access - safe math operations
}
