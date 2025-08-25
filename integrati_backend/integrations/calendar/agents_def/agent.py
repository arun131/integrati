"""Calendar agent factory functions."""

import dspy
from .signature import CalendarAgentSignature, CalendarBackgroundAgentSignature
from typing import Literal


class CalendarAgent(dspy.Module):
    """Calendar agent"""

    def __init__(self, calendar_tools: list):
        self.calendar_tools = calendar_tools
        self.agent = dspy.ReAct(signature=CalendarAgentSignature, tools=calendar_tools)

    def forward(self, user_query: str, request_context: dict) -> str:
        """Forward the request to the Calendar agent."""
        return self.agent(user_query=user_query, request_context=request_context)

    async def aforward(self, user_query: str, request_context: dict) -> str:
        """Forward the request to the Calendar agent."""
        return await self.agent.acall(
            user_query=user_query, request_context=request_context
        )


class CalendarBackgroundAgent(dspy.Module):
    """Calendar background agent"""

    def __init__(self, calendar_tools: list):
        self.calendar_tools = calendar_tools
        self.agent = dspy.ReAct(
            signature=CalendarBackgroundAgentSignature, tools=calendar_tools
        )

    def forward(self, event_details: dict, user_context: dict) -> str:
        """Forward the request to the Calendar background agent."""
        return self.agent(event_details=event_details, user_context=user_context)

    async def aforward(self, event_details: dict, user_context: dict) -> str:
        """Forward the request to the Calendar background agent."""
        return await self.agent.acall(
            event_details=event_details, user_context=user_context
        )


def get_calendar_agent(
    calendar_tools: list, trigger: Literal["background", "chatbot"]
) -> CalendarAgent:
    """
    Create and return a Calendar agent with the provided tools.

    Args:
        calendar_tools: List of DSPy tools for Calendar operations
        trigger: The trigger for the Calendar agent. Can be "background" or "chatbot"
    Returns:
        dspy.ReAct: Configured Calendar agent
        or
        dspy.ReAct: Configured Calendar background agent
    """

    if trigger == "background":
        agent = CalendarBackgroundAgent(calendar_tools)
    else:
        agent = CalendarAgent(calendar_tools)

    return agent
