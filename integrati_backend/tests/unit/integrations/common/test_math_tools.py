"""Unit tests for basic math tools in integrations.common.tools.

We import the tool functions directly (they are normal Python callables)
and ensure correctness as pure functions—no FastMCP context required.
"""

import pytest

from integrations.common.tools import CommonTools


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (2, 3, 5),
        (-1, 1, 0),
        (0, 0, 0),
    ],
)
@pytest.mark.asyncio
async def test_add_numbers(a, b, expected):
    assert await CommonTools.add_numbers(a, b) == expected


@pytest.mark.parametrize("lst,expected", [([1, 2, 3], 6), ([], 0), ([5], 5)])
@pytest.mark.asyncio
async def test_sum_list(lst, expected):
    assert await CommonTools.sum_list(lst) == expected


@pytest.mark.asyncio
async def test_divide_numbers():
    assert await CommonTools.divide_numbers(10, 2) == 5
    with pytest.raises(ValueError):
        await CommonTools.divide_numbers(5, 0)


@pytest.mark.asyncio
async def test_calculate_square_root():
    assert await CommonTools.calculate_square_root(9) == 3
    with pytest.raises(ValueError):
        await CommonTools.calculate_square_root(-1)
